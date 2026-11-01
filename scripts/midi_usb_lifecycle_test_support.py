"""Synthetic registered-object lifecycle; installs asserted emulator gates only."""
import midi_usb_lifecycle_prototype as life
import midi_usb_ledger_prototype as ledger
import midi_usb_inquiry_prototype as rx
from thumb_asm import b_w


class UsbLifecycleFixture:
    def __init__(self, h):
        self.h = h
        self.code, self.labels = life.arm_code()
        h.u.mem_write(life.CODE_BASE, self.code)
        h.u.mem_write(life.STATE_BASE-4, b'CBEG')
        h.u.mem_write(life.STATE_BASE+life.STATE_SIZE, b'CEND')
        h.u.mem_write(life.STATE_BASE, bytes(life.STATE_SIZE))
        controller = h.native.usb_controller if h.native else 0x20007800
        h.word(h.ingress.usb_port+16, controller)
        h.u.mem_write(controller+0x274, b'\x03')
        ring = h.rx.ring()
        for off, val in ((0, life.MAGIC), (life.PHASE, life.ACTIVE), (life.FIFO, h.ingress.usb_fifo),
                         (life.DATA, ring['data']), (life.CAPACITY, ring['capacity']),
                         (life.PARSER, h.ingress.parser), (life.PORT, h.ingress.usb_port),
                         (life.CONTROLLER, controller), (life.EPOCH, 1),
                         (life.TX_ENDPOINT, h.native.usb_endpoint if h.native else 0)):
            h.word(life.STATE_BASE+off, val)
        previous = next(o for o in h.recovery.overlays if o['address'] == rx.NATIVE_POLL)
        assert h.u.mem_read(rx.NATIVE_POLL, 4) == previous['replacement']
        patch = b_w(rx.NATIVE_POLL, self.labels['cl_poll'])
        previous['replacement'] = patch
        h.u.mem_write(rx.NATIVE_POLL, patch)
        for address, (_, _, original) in life.GATES.items():
            assert h.u.mem_read(address, len(original)) == original
            assert 0x08010200 <= address < address+len(original) <= 0x08080000
            assert all(address+len(original) <= o['address'] or o['address']+len(o['replacement']) <= address
                       for o in h.recovery.overlays)
            replacement = b_w(address, self.labels[f'cl_gate_{address:08x}'])+b'\x00\xBF'*(len(original)//2-2)
            h.recovery.overlays.append(dict(address=address, original=original, replacement=replacement))
            h.u.mem_write(address, replacement)
        # Constructor/queue primitives already executed during fixture setup.
        # uc.mem_write alone does not invalidate every previously translated TB.
        h.u.ctl_remove_cache(0x08010000, 0x08080000)

    def reset(self):
        return self.h.call(self.labels['cl_reset'])

    def resume(self):
        return self.h.call(self.labels['cl_resume'])

    def offer(self, packets):
        h = self.h
        h.u.mem_write(h.ingress.enqueue_data, packets)
        h.ingress.descriptor(h.ingress.enqueue_desc, h.ingress.enqueue_data, len(packets))
        return h.call(0x08025AEC, h.ingress.usb_fifo, h.ingress.enqueue_desc)

    def configured(self, value):
        ctrl = self.h.read(life.STATE_BASE+life.CONTROLLER)
        self.h.u.mem_write(ctrl+0x274, bytes([value]))

    def status(self):
        return {name: self.h.read(life.STATE_BASE+off) for name, off in (
            ('phase', life.PHASE), ('busy', life.BUSY), ('errors', life.ERRORS),
            ('epoch', life.EPOCH), ('publishing', life.PUBLISHING))}

    def check(self):
        h = self.h
        h.assertEqual(h.u.mem_read(life.STATE_BASE-4, 4), b'CBEG')
        h.assertEqual(h.u.mem_read(life.STATE_BASE+life.STATE_SIZE, 4), b'CEND')
        h.assertEqual(self.status()['busy'], 0)
        h.assertEqual(self.status()['publishing'], 0)
        h.rx.check()
