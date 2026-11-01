"""Unicorn only: replace native USB poll with a retained-cursor experiment."""
import midi_usb_inquiry_prototype as rx
from thumb_asm import b_w


class UsbInquiryFixture:
    def __init__(self, h, overlay=True, ordered=False):
        self.h = h
        self.ordered = ordered
        self.code, self.labels = rx.arm_code(ordered=ordered)
        h.u.mem_write(rx.CODE_BASE, self.code)
        h.u.mem_write(rx.STATE_BASE-4, b'RBEG')
        h.u.mem_write(rx.STATE_BASE+rx.STATE_SIZE, b'REND')
        h.u.mem_write(rx.STATE_BASE, bytes(rx.STATE_SIZE))
        for offset, value in ((0, rx.ORDERED_MAGIC if ordered else rx.MAGIC), (rx.PORT, h.ingress.usb_port),
                              (rx.PARSER, h.ingress.parser), (rx.ROUTER, h.output.router),
                              (rx.DESC+4, rx.STATE_BASE+rx.BUFFER)):
            h.word(rx.STATE_BASE+offset, value)
        assert bytes(h.u.mem_read(rx.REPLY_ADDR, len(rx.REPLY))) == rx.REPLY
        assert bytes(h.u.mem_read(rx.CIN_TABLE, 16)) == rx.CIN_LENGTHS
        if overlay:
            address, original = rx.NATIVE_POLL, rx.POLL_PROLOGUE
            assert bytes(h.u.mem_read(address, 4)) == original
            assert 0x08010200 <= address < address+4 <= 0x08080000
            assert all(address+4 <= o['address'] or o['address']+len(o['replacement']) <= address
                       for o in h.recovery.overlays)
            replacement = b_w(address, self.labels['ui_poll'])
            h.recovery.overlays.append(dict(address=address, original=original, replacement=replacement))
            h.u.mem_write(address, replacement)

    def enqueue(self, packets):
        h = self.h
        assert 0 < len(packets) <= 64 and len(packets) % 4 == 0
        h.u.mem_write(h.ingress.enqueue_data, bytes(packets))
        h.ingress.descriptor(h.ingress.enqueue_desc, h.ingress.enqueue_data, len(packets))
        assert h.call(0x08025AEC, h.ingress.usb_fifo, h.ingress.enqueue_desc) == 1

    def poll(self):
        return self.h.call(rx.NATIVE_POLL)

    def status(self):
        return {name: self.h.read(rx.STATE_BASE+off)
                for name, off in [('busy', rx.BUSY), ('pending', rx.PENDING), ('length', rx.DESC),
                                  ('packet', rx.PACKET), ('sub', rx.SUB), ('fault', rx.FAULT)]}

    def settle(self, rounds=128):
        for n in range(rounds):
            self.h.q.poll()
            self.poll()
            if (not self.status()['pending'] and not self.status()['length']
                    and not self.h.q.status()['active']
                    and not self.h.call(0x0802A37E, self.h.ingress.usb_fifo)
                    and not any(self.h.recovery.pending(p) for p in range(3))):
                return n+1
        raise AssertionError('USB inquiry did not settle')

    def check(self):
        self.h.assertEqual(self.h.u.mem_read(rx.STATE_BASE-4, 4), b'RBEG')
        self.h.assertEqual(self.h.u.mem_read(rx.STATE_BASE+rx.STATE_SIZE, 4), b'REND')
        self.h.assertEqual(self.status()['busy'], 0)
        self.h.q.check_canaries()
