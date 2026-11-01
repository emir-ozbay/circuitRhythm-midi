"""Synthetic SPSC USB RX ring, with provenance-aware private marker inspection."""
import struct
import midi_usb_ledger_prototype as ledger
import midi_usb_inquiry_prototype as prior
from midi_usb_inquiry_test_support import UsbInquiryFixture
from thumb_asm import b_w


class UsbLedgerFixture:
    enqueue = UsbInquiryFixture.enqueue

    def __init__(self, h, overlay=True):
        self.h = h
        self.code, self.labels = ledger.arm_code()
        h.u.mem_write(ledger.CODE_BASE, self.code)
        h.u.mem_write(ledger.STATE_BASE-4, b'RBEG')
        h.u.mem_write(ledger.STATE_BASE+ledger.STATE_SIZE, b'REND')
        h.u.mem_write(ledger.STATE_BASE, bytes(ledger.STATE_SIZE))
        fifo = h.ingress.usb_fifo
        read = int.from_bytes(h.u.mem_read(fifo+8, 2), 'little')
        for off, value in ((0, ledger.MAGIC), (ledger.PORT, h.ingress.usb_port),
                           (ledger.PARSER, h.ingress.parser), (ledger.ROUTER, h.output.router),
                           (ledger.DESC+4, ledger.STATE_BASE+ledger.BUFFER),
                           (ledger.FIFO, fifo), (ledger.EXPECTED_READ, read)):
            h.word(ledger.STATE_BASE+off, value)
        assert h.u.mem_read(prior.CIN_TABLE, 16) == prior.CIN_LENGTHS
        assert h.u.mem_read(prior.REPLY_ADDR, len(prior.REPLY)) == prior.REPLY
        if overlay:
            address = prior.NATIVE_POLL
            assert h.u.mem_read(address, 4) == prior.POLL_PROLOGUE
            assert 0x08010200 <= address < address+4 <= 0x08080000
            assert all(address+4 <= o['address'] or o['address']+len(o['replacement']) <= address
                       for o in h.recovery.overlays)
            patch = b_w(address, self.labels['ul_poll'])
            h.recovery.overlays.append(dict(address=address, original=prior.POLL_PROLOGUE, replacement=patch))
            h.u.mem_write(address, patch)

    def poll(self):
        return self.h.call(prior.NATIVE_POLL)

    def ring(self):
        data, capacity, write, read, item = struct.unpack('<I4H', self.h.u.mem_read(self.h.ingress.usb_fifo, 12))
        return dict(data=data, capacity=capacity, write=write, read=read, item=item,
                    queued=(write-read) % capacity)

    def records(self):
        ring = self.ring()
        def byte(offset):
            return self.h.u.mem_read(ring['data']+(ring['read']+offset) % ring['capacity'], 1)[0]
        result, offset = [], 0
        while offset+2 <= ring['queued']:
            size = byte(offset) | byte(offset+1) << 8
            if offset+2+size > ring['queued']:
                break
            payload = bytes(byte(offset+2+n) for n in range(size))
            result.append(dict(offset=offset, size=size, payload=payload))
            offset += size+2
        return result

    def status(self):
        h = self.h
        values = {name: h.read(ledger.STATE_BASE+off) for name, off in (
            ('pending', ledger.PENDING), ('scanned', ledger.SCANNED),
            ('expected_read', ledger.EXPECTED_READ), ('busy', ledger.BUSY), ('fault', ledger.FAULT))}
        values['queued'] = self.ring()['queued']
        values['owed'] = sum(r['payload'][::4].count(ledger.OWED)
                             for r in self.records() if r['offset']+r['size']+2 <= values['scanned'])
        return values

    def settle(self, rounds=256):
        for n in range(rounds):
            self.h.q.poll(); self.poll()
            s = self.status()
            if not s['pending'] and not s['queued'] and not self.h.q.status()['active'] and not any(
                    self.h.recovery.pending(p) for p in range(3)):
                return n+1
        raise AssertionError('RX ledger did not settle')

    def check(self):
        h = self.h
        h.assertEqual(h.u.mem_read(ledger.STATE_BASE-4, 4), b'RBEG')
        h.assertEqual(h.u.mem_read(ledger.STATE_BASE+ledger.STATE_SIZE, 4), b'REND')
        s = self.status()
        h.assertEqual(s['busy'], 0)
        h.assertLessEqual(s['pending'], ledger.MAX_PENDING)
        h.assertLessEqual(s['scanned'], s['queued'])
        h.assertEqual(s['expected_read'], self.ring()['read'])
        h.q.check_canaries()
