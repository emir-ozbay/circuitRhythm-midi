"""Explicit queue API in Unicorn. Caller capture is a separate experiment."""
import midi_sysex_retry_prototype as retry
import midi_recovery_prototype as recovery
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2


class SysexRetryFixture:
    def __init__(self, h, notifications=False, reservations=False):
        self.h = h
        self.notifications = notifications
        self.reservations = reservations
        self.state_size = retry.REQUEST_STATE_SIZE if reservations else retry.NOTIFICATION_STATE_SIZE if notifications else retry.STATE_SIZE
        self.code, self.labels = retry.arm_code(notifications=notifications, reservations=reservations)
        assert recovery.CODE_BASE+len(h.recovery.code) <= retry.CODE_BASE
        h.u.mem_write(retry.CODE_BASE, self.code)
        h.u.mem_write(retry.STATE_BASE-4, b'QBEG')
        h.u.mem_write(retry.STATE_BASE+self.state_size, b'QEND')
        h.u.mem_write(retry.STATE_BASE, bytes(self.state_size))
        h.word(retry.STATE_BASE, retry.MAGIC)
        h.word(retry.STATE_BASE+retry.ROUTER, h.output.router)
        self.captured = []

    def install_producer_guards(self):
        from thumb_asm import b_w
        h = self.h
        for address, expected in retry.CALLER_GATES.items():
            assert bytes(h.u.mem_read(address, 4)) == expected
            assert 0x08010200 <= address < address+4 <= 0x08080000
            assert all(address+4 <= old['address'] or old['address']+len(old['replacement']) <= address
                       for old in h.recovery.overlays)
            replacement = b_w(address, self.labels[f'sr_gate_{address:08x}'])
            h.recovery.overlays.append(dict(address=address, original=expected, replacement=replacement))
            h.u.mem_write(address, replacement)

    def install_request_guards(self):
        from thumb_asm import b_w
        assert self.reservations
        h = self.h
        for address, (expected, _, _) in retry.REQUEST_GATES.items():
            assert bytes(h.u.mem_read(address, 4)) == expected
            assert 0x08010200 <= address < address+4 <= 0x08080000
            assert all(address+4 <= old['address'] or old['address']+len(old['replacement']) <= address
                       for old in h.recovery.overlays)
            replacement = b_w(address, self.labels[f'sr_request_gate_{address:08x}'])
            h.recovery.overlays.append(dict(address=address, original=expected, replacement=replacement))
            h.u.mem_write(address, replacement)

    def submit(self, descriptor, mask=7):
        return self.h.call(self.labels['sr_submit'], self.h.output.router, mask, descriptor)

    def service(self):
        return self.h.call(self.labels['sr_service'], self.h.output.router)

    def status(self):
        return {name: self.h.u.mem_read(retry.STATE_BASE+offset, 1)[0]
                for name, offset in [('active', retry.ACTIVE), ('waiting', retry.WAITING),
                                     ('accepted', retry.ACCEPTED), ('failed', retry.FAILED),
                                     ('errors', retry.ERRORS), ('busy', retry.BUSY)]}

    def poll(self):
        self.h.recovery.poll()
        return self.service()

    def settle(self, rounds=64):
        for n in range(rounds):
            self.poll()
            if not self.status()['active'] and not any(self.h.recovery.pending(p) for p in range(3)):
                return n+1
        raise AssertionError('owned SysEx transaction did not settle')

    def check_canaries(self):
        self.h.assertEqual(self.h.u.mem_read(retry.STATE_BASE-4, 4), b'QBEG')
        self.h.assertEqual(self.h.u.mem_read(retry.STATE_BASE+self.state_size, 4), b'QEND')
        self.h.recovery.check_canaries()

    def capture_native_callers(self, forced_result=None):
        """Capture real generated descriptors. forced_result only probes returns.

        Normal capture routes to the explicit queue API, deliberately omitting
        the native success notification. It is not a compatibility acceptance.
        """
        from thumb_asm import b_w
        h = self.h
        old = next(o for o in h.recovery.overlays if o['address'] == recovery.NATIVE_ROUTER)
        assert bytes(h.u.mem_read(recovery.NATIVE_ROUTER, 4)) == old['replacement']
        if forced_result is None:
            replacement = b_w(recovery.NATIVE_ROUTER, self.labels['sr_submit'])
        else:
            assert forced_result in (0, 1)
            replacement = bytes([forced_result, 0x20, 0x70, 0x47])
        old['replacement'] = replacement
        h.u.mem_write(recovery.NATIVE_ROUTER, replacement)
        def capture(u, pc, size, data):
            router, mask, desc = (u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            pointer, length = h.read(desc), h.read(desc+4)
            assert 2 <= length <= 360
            self.captured.append({'router': router, 'mask': mask, 'descriptor': desc,
                                  'pointer': pointer, 'payload': bytes(u.mem_read(pointer, length))})
        h.u.hook_add(UC_HOOK_CODE, capture, begin=recovery.NATIVE_ROUTER, end=recovery.NATIVE_ROUTER)


# Entry -> direct router callsite, source lifetime, result propagation.
# Validated by pinned disassembly and real caller execution below.
CALLERS = [
    (0x08026F0C, 0x08026F32, 'flash', 'discard'),
    (0x0802CBB8, 0x0802CBF0, 'static', 'forward'),
    (0x0802CD60, 0x0802CDA2, 'static', 'discard'),
    (0x0802CDF8, 0x0802CE64, 'stack', 'forward'),
    (0x0802CEE4, 0x0802CF38, 'stack', 'forward'),
    (0x0802D0B0, 0x0802D0F0, 'static', 'discard'),
    (0x0802D0F8, 0x0802D12C, 'static', 'forward'),
    (0x0802D134, 0x0802D1CC, 'static', 'forward'),
    (0x0802DE84, 0x0802DE8C, 'borrowed', 'forward'),
    (0x0802ED88, 0x0802EDA2, 'borrowed', 'forward'),
    (0x08042160, 0x080421B0, 'static', 'forward'),
    (0x0804691A, 0x08046954, 'borrowed+global_callback', 'forward'),
]


def caller_args(h, entry):
    """Synthetic arguments only; no request handlers/storage/flash writes run."""
    desc = h.sysex_descriptor()
    data = 0x20006100
    h.u.mem_write(data, b'\x01\x02\x03\x04')
    if entry == 0x08026F0C:
        h.u.mem_write(desc+16, bytes(h.u.mem_read(0x080270D0, 6)))
        return 0, desc, 0x55, 0x66
    if entry in (0x0802CBB8, 0x0802CD60):
        return 0x40, data, 2
    if entry == 0x0802CDF8:
        h.u.mem_write(desc+16, b'\xF0\x00\x20\x29\x00\x7E\x03\xF7')
        return (desc,)  # branch3 avoids palette mutation branch2
    if entry == 0x0802CEE4:
        return 0, 1, 0x456
    if entry in (0x0802D0B0, 0x0802D0F8):
        return (0x123456,)  # response formatter only, no flash-update handler
    if entry == 0x0802D134:
        # Native version response reads synthetic boot header and real app
        # identity. Selector43A94 is a boundary, not a full boot test.
        h.u.mem_write(0x08043A94, bytes.fromhex('00207047'))
        h.recovery.before_code = bytes(h.u.mem_read(0x08010000, len(h.image)))
        return ()
    if entry == 0x0802DE84:
        return 0, desc
    if entry == 0x0802ED88:
        h.u.mem_write(0x20006F58, b'\x01')
        return 0, desc
    if entry == 0x08042160:
        h.word(0x20006110, 1)
        return 0x20006110, 0x5E, data, 2
    if entry == 0x0804691A:
        return 1, desc, 0x0800EB21, 0x12345678
    raise ValueError(hex(entry))
