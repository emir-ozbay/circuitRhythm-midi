"""Regression evidence for the second audit; real stock store-read ABI."""
import unittest
import test_phase1_safety as base


class ReauditABI(unittest.TestCase):
    # Read/Close component tests explicitly bypass containment in emulator RAM.
    # They cannot establish that production Load is functional.

    setUpClass = classmethod(base.SafetyTests.setUpClass.__func__)
    setUp = base.SafetyTests.setUp
    word = base.SafetyTests.word
    read = base.SafetyTests.read
    store = base.SafetyTests.store
    call = base.SafetyTests.call

    def test_containment_preserves_entire_live_project_before_any_read(self):
        from probe_project_alias import probe
        result = probe(self.image, self.labels)
        self.assertTrue(result['entire_raw_buffer_preserved'])
        self.assertEqual(result['file_read_api_calls'], 0)
        self.assertEqual(result['pattern_note_after_failed_load'], 60)
        self.assertEqual(result['transition_after_error'], 0)
        self.assertEqual(result['project_tainted'], 0)

    def test_counterfactual_without_containment_still_corrupts_live_pattern(self):
        from probe_project_alias import probe
        result = probe(self.image, self.labels, bypass_containment=True)
        self.assertTrue(result['live_pattern_corrupted_without_apply'])
        self.assertFalse(result['entire_raw_buffer_preserved'])
        self.assertEqual(result['file_read_api_calls'], 1)
        self.assertEqual(result['pattern_note_after_failed_load'], 34)

    def test_containment_cleans_phase_and_preserves_mode_dirty_and_owner(self):
        from storage_queue_test_support import StorageQueueFixture
        for mode in (0, 1):
            for heap_valid in (False, True):
                for owned in (False, True):
                    with self.subTest(mode=mode, heap_valid=heap_valid, owned=owned):
                        self.setUp()
                        q = StorageQueueFixture(self)
                        f = q.begin_project_load(mode)
                        self.assertEqual(q.read_api_calls, 0)
                        self.assertEqual(q.work(), 0)
                        self.assertFalse(q.deliver())
                        state = base.seq.SEQ_STATE_ADDR
                        self.u.mem_write(state + base.seq.OFF_TRANS_STATE, b'\x02')
                        self.u.mem_write(state + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                        self.u.mem_write(state + base.seq.OFF_PROJECT_TAINTED, b'\x01')
                        self.word(state + base.seq.OFF_SAVE_OWNER, f.p)
                        self.word(state + base.seq.OFF_PROJ_CTRL_PTR, f.p if owned else f.p + 4)
                        if not heap_valid:
                            self.word(base.seq.HEAP_CUR_PTR, state + 4)
                        before = bytes(self.u.mem_read(state, 256))
                        self.call(0x08037BD6, f.p)
                        after = bytes(self.u.mem_read(state, 256))
                        expected = bytearray(before)
                        if heap_valid and owned:
                            expected[base.seq.OFF_TRANS_STATE] = 0
                        self.assertEqual(after, expected)
                        phase = self.call(base.seq.STOCK_READ_STORE_WORD, f.phase, 1)
                        self.assertEqual(self.u.mem_read(phase, 1), b'\x00')
                        self.assertEqual(q.work(), 0)
                        self.assertFalse(q.deliver())

    def test_failed_load_blocks_dispatch_and_direct_save(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        f = q.begin_project_load(bypass_containment=True)
        q.work(read_result=5)
        q.deliver()
        q.work()
        q.deliver()
        state = base.seq.SEQ_STATE_ADDR
        self.assertEqual(self.u.mem_read(state + base.seq.OFF_PROJECT_TAINTED, 1), b'\x01')
        save_node = f.p + 0x180
        self.word(f.p + 0x3C, save_node)
        self.word(save_node, f.p)
        before = bytes(self.u.mem_read(f.p, 0x100))
        self.assertEqual(self.call(base.seq.STOCK_ACTION_DISPATCH, save_node, 0, 0, 0), 1)
        self.assertEqual(self.call(0x08037ED0, f.p, 0, 0), 1)
        self.assertEqual(bytes(self.u.mem_read(f.p, 0x100)), before)
        self.assertEqual(self.read(state + base.seq.OFF_SAVE_OWNER), 0)
        self.assertEqual(q.work(), 0)
        self.assertEqual(self.u.mem_read(state + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')

    def test_save_entry_fails_closed_without_valid_state(self):
        self.word(base.seq.HEAP_CUR_PTR, base.seq.SEQ_STATE_ADDR + 4)
        before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256))
        self.assertEqual(self.call(0x08037ED0, 0x20006000, 0, 0), 1)
        self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 256)), before)

    def test_completed_apply_clears_failed_load_quarantine(self):
        from phase1_test_support import ProjectTransitionFixture
        f = ProjectTransitionFixture(self)
        self.word(f.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
        self.call(0x0803D8B8, f.ctrl, 18)
        self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_TAINTED, b'\x01')
        f.finish()  # explicit successful-apply boundary, not a physical read
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_TAINTED, 1), b'\x00')

    def test_real_constructors_bind_recorders_to_project_storage(self):
        from project_alias_test_support import ProjectAliasFixture, STORE_LEN, TRACK_STRIDE, PATTERN_OFFSET
        f = ProjectAliasFixture(self)
        self.assertEqual(self.read(f.p + 0x14), f.raw)
        self.assertEqual(self.read(f.span), TRACK_STRIDE)
        self.assertEqual(self.read(f.span + 4), 8)
        self.assertEqual(len(set(f.recorders)), 8)
        for track, patterns in enumerate(f.patterns):
            self.assertEqual(patterns, f.raw + PATTERN_OFFSET + track * TRACK_STRIDE)
            self.assertGreaterEqual(patterns, f.raw)
            self.assertLessEqual(patterns + TRACK_STRIDE, f.raw + STORE_LEN)
        self.assertEqual(self.read(f.raw + STORE_LEN), f.raw)

    def test_load_close_context_and_heap_failure_write_no_state(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        q.begin_project_load(bypass_containment=True)
        q.work()
        q.deliver()
        state = base.seq.SEQ_STATE_ADDR
        before = bytes(self.u.mem_read(state, 0x64))
        self.word(0x20040004, 0xDEADBEEF)
        self.call(self.labels['c_load_close_result'], 0, 0, 6)
        self.assertEqual(bytes(self.u.mem_read(state, 0x64)), before)
        self.word(base.seq.HEAP_CUR_PTR, state + 4)
        self.word(0x20040004, state)
        self.call(self.labels['c_load_close_result'], 0, 0, 6)
        self.assertEqual(bytes(self.u.mem_read(state, 0x64)), before)

    def test_partial_project_read_does_not_apply_failed_buffer(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        commits = []
        self.u.mem_write(base.seq.STOCK_LOAD_SUCCESS, bytes.fromhex('7047'))
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: commits.append(a), begin=base.seq.STOCK_LOAD_SUCCESS, end=base.seq.STOCK_LOAD_SUCCESS)
        f = q.begin_project_load(bypass_containment=True)
        self.u.mem_write(q.blob, b'\x11' * 64)
        q.read_payload = b'\xa5' * 16
        self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
        q.work(read_result=4)
        q.deliver()
        q.work()
        q.deliver()
        self.assertEqual(self.u.mem_read(q.blob, 64), b'\xa5' * 16 + b'\x11' * 48)
        self.assertEqual(commits, [])
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), b'\x00\x00')
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')

    def test_generic_read_callback_keeps_stock_path_and_abi(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        q.submit_load()
        q.work(read_result=5)
        self.assertTrue(q.deliver())
        self.assertEqual(len(q.calls), 1)
        registers, header = q.calls[0]
        self.assertEqual(registers[0], q.callback)
        self.assertEqual(registers[2], self.read(q.callback))
        self.assertEqual(registers[3], 0)
        self.assertEqual(header[:8], bytes([2, 0, 0, 0, 7, 0, 0, 0]))
        self.assertEqual(self.read(q.bridge), 0)
        self.assertEqual(q.work(), 0)  # no extra Close introduced for generic clients
        self.assertFalse(q.deliver())

    def test_load_close_rejects_wrong_target_and_duplicate(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        self.u.mem_write(base.seq.STOCK_LOAD_SUCCESS, bytes.fromhex('7047'))
        q.begin_project_load(bypass_containment=True)
        q.work()
        q.deliver()
        state = base.seq.SEQ_STATE_ADDR
        self.word(state + base.seq.OFF_LOAD_CLOSE_STATUS + 4, 33)
        before = bytes(self.u.mem_read(state, 0x64))
        q.work()
        q.deliver()
        self.assertEqual(bytes(self.u.mem_read(state, 0x64)), before)
        self.word(state + base.seq.OFF_LOAD_CLOSE_STATUS + 4, 32)
        self.word(0x20040004, state)
        self.call(self.labels['c_load_close_result'], 0, 0, 0)
        self.assertEqual(self.read(state + base.seq.OFF_LOAD_CLOSE_CALLBACK), 0)
        before = bytes(self.u.mem_read(state, 0x64))
        self.word(0x20040004, state)
        self.call(self.labels['c_load_close_result'], 0, 0, 0)
        self.assertEqual(bytes(self.u.mem_read(state, 0x64)), before)

    def test_load_read_and_close_errors_do_not_reach_project_commit(self):
        from storage_queue_test_support import StorageQueueFixture
        for mode in (0, 1):
            for read_result, close_result in ((0, 0), (0, 6), (2, 0), (2, 6), (4, 0), (4, 6), (5, 0), (5, 6)):
                with self.subTest(mode=mode, read_result=read_result, close_result=close_result):
                    self.setUp()
                    q = StorageQueueFixture(self)
                    # Success is observed at the apply boundary. Failure cleanup
                    # runs completely; this test does not fabricate a project file.
                    commits = []
                    self.u.mem_write(base.seq.STOCK_LOAD_SUCCESS, bytes.fromhex('7047'))
                    self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: commits.append(u.reg_read(base.UC_ARM_REG_R0)), begin=base.seq.STOCK_LOAD_SUCCESS, end=base.seq.STOCK_LOAD_SUCCESS)
                    f = q.begin_project_load(mode, bypass_containment=True)
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                    q.work(read_result=read_result)
                    self.assertTrue(q.deliver())
                    self.assertEqual(commits, [])
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), bytes([mode, 2]))
                    q.work(close_result=close_result)
                    self.assertTrue(q.deliver())
                    failure = read_result != 0 or close_result != 0
                    self.assertEqual(commits, [] if failure else [f.p])
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SEQ_ENABLED, 1), bytes([mode]))
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
                    self.call(base.seq.STOCK_READ_STORE_WORD, q.meta, 11)
                    self.assertEqual(self.u.mem_read(self.u.reg_read(base.UC_ARM_REG_R0), 1), bytes([mode * 32]))
                    if failure:
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_TRANS_STATE, 1), b'\x00')
                        self.call(base.seq.STOCK_READ_STORE_WORD, self.read(f.p + 0x4C), 0)
                        self.assertEqual(self.read(self.u.reg_read(base.UC_ARM_REG_R0)), 8)

    def test_edit_while_close_pending_survives_success_and_duplicate(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        q.begin_project_save()
        q.work()
        self.assertTrue(q.deliver())
        self.assertNotEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_CLOSE_CALLBACK), 0)
        listener, store = 0x20005000, 0x20005500
        self.word(listener + 0x1C, store)
        self.call(0x08048208, listener, store, 1, end=0x0804820C)
        q.work()
        self.assertTrue(q.deliver())
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
        self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_CLOSE_CALLBACK), 0)
        before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x54))
        self.word(0x20040004, base.seq.SEQ_STATE_ADDR)
        self.call(self.labels['c_save_close_result'], 0, 0, 0)
        self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x54)), before)

    def test_close_result_rejects_bad_context_and_invalid_heap(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        q.begin_project_save()
        q.work()
        q.deliver()
        state = base.seq.SEQ_STATE_ADDR
        before = bytes(self.u.mem_read(state, 0x54))
        self.word(0x20040004, 0xDEADBEEF)
        self.call(self.labels['c_save_close_result'], 0, 0, 6)
        self.assertEqual(bytes(self.u.mem_read(state, 0x54)), before)
        self.word(base.seq.HEAP_CUR_PTR, state + 4)
        self.word(0x20040004, state)
        self.call(self.labels['c_save_close_result'], 0, 0, 6)
        self.assertEqual(bytes(self.u.mem_read(state, 0x54)), before)

    def test_stock_storage_queue_defers_save_ack_and_rejects_overlap(self):
        from storage_queue_test_support import StorageQueueFixture
        from phase1_test_support import ProjectTransitionFixture
        for result, close_result in ((0, 0), (0, 6), (2, 0), (2, 6), (3, 0), (3, 6), (5, 0), (5, 6)):
            with self.subTest(result=result, close_result=close_result):
                self.setUp()
                f = ProjectTransitionFixture(self)
                q = StorageQueueFixture(self)
                callbacks = []
                self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: callbacks.append(a), begin=0x080381D6, end=0x080381D6)
                q.callback = f.p + 0x10
                self.word(q.callback, 0x20029000)
                self.word(0x20029000, 0x080381D7)
                meta = self.store(bytes(128))
                self.word(f.p + 0x44, meta)
                self.word(f.p + 0x4C, self.store(bytes(4)))
                self.word(f.p + 0xFC, self.store(bytes(4)))
                self.word(f.p + 0x14, 0x20029500)
                self.word(f.p + 0x6C, 0x20029600)
                save_node = f.p + 0x180
                self.word(f.p + 0x3C, save_node)
                self.word(save_node, f.p)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                self.call(0x08037ED0, f.p, 7, 0, end=0x08037F42)
                q.submit_save()
                # Actual stock action dispatcher rejects the second Save before
                # and after the worker has queued (but not delivered) its result.
                self.assertEqual(self.call(base.seq.STOCK_ACTION_DISPATCH, save_node, 7, 0, 0), 1)
                self.assertEqual(q.work(result), 1)
                self.assertEqual(self.call(base.seq.STOCK_ACTION_DISPATCH, save_node, 7, 0, 0), 1)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
                self.assertTrue(q.deliver())
                self.assertFalse(q.deliver())
                self.assertEqual(callbacks, [])
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
                self.assertEqual(self.call(base.seq.STOCK_ACTION_DISPATCH, save_node, 7, 0, 0), 1)
                q.work(close_result=close_result)
                self.assertEqual(callbacks, [])
                self.assertTrue(q.deliver())
                self.assertFalse(q.deliver())
                self.assertEqual(callbacks, [0x080381D6])
                self.assertEqual(self.read(q.header), 2)  # original file key preserved
                self.assertEqual(self.read(q.bridge + 4), 0)
                self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_OWNER), 0)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), bytes([result != 0 or close_result != 0]))
                self.call(base.seq.STOCK_READ_STORE_WORD, self.read(f.p + 0x4C), 0)
                self.assertEqual(self.read(self.u.reg_read(base.UC_ARM_REG_R0)) & 2, 0)

    def test_storage_result_bridge_preserves_nonproject_callback(self):
        from storage_queue_test_support import StorageQueueFixture
        q = StorageQueueFixture(self)
        q.submit_save()
        q.work(5)
        self.assertTrue(q.deliver())
        self.assertEqual(len(q.calls), 1)
        registers, header = q.calls[0]
        self.assertEqual(registers[0], q.callback)
        self.assertEqual(registers[2], 0)
        self.assertEqual(header[:8], bytes([2, 0, 0, 0, 7, 0, 0, 0]))
        self.assertEqual(self.read(q.bridge + 4), 0)

    def test_projects_reentry_does_not_replace_active_transition_context(self):
        from phase1_test_support import ProjectTransitionFixture
        f = ProjectTransitionFixture(self)
        self.word(f.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
        self.call(0x0803D8B8, f.ctrl, 18)
        foreign_view, foreign_node = 0x20005000, 0x20005500
        self.word(foreign_view + 0x0C, foreign_node)
        self.word(foreign_node, 0x20006004)
        self.u.reg_write(base.UC_ARM_REG_R4, foreign_view)
        self.call(self.labels['c_proj_enter_page'])
        self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJ_CTRL_PTR), f.p)
        self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJ_VIEW_PTR), f.view)

    def test_rejected_foreign_dispatch_cannot_replace_transition_owner(self):
        from phase1_test_support import ProjectTransitionFixture
        first = ProjectTransitionFixture(self)
        second = ProjectTransitionFixture(self, ctrl=0x20005000, view=0x20005500, p=0x20006000)
        self.word(first.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
        self.call(0x0803D8B8, first.ctrl, 18)
        self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJ_CTRL_PTR), first.p)
        self.assertEqual(self.call(base.seq.STOCK_ACTION_DISPATCH, second.p + 0x100, 32, 0, 0), 1)
        self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJ_CTRL_PTR), first.p)
        first.finish()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), b'\x01\x00')

    def test_save_error_ownership_and_interrupt_mask(self):
        p, other = 0x20006000, 0x20006200
        for foreign in (False, True):
            for status in (0, 1, 3, 4):
                for primask in (0, 1):
                    with self.subTest(foreign=foreign, status=status, primask=primask):
                        self.setUp()
                        callback_owner = other if foreign else p
                        phase = self.store(bytes([5, 7, 0, 0, 9, 0, 0, 0]))
                        ready = self.store(bytes([11, 0, 0, 0]))
                        self.word(callback_owner + 0x48, phase)
                        self.word(callback_owner + 0x4C, ready)
                        self.word(callback_owner + 0x6C, 0x20006400)
                        self.word(0x20006500, status)
                        self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                        self.call(0x08037ED0, p, 7, 0, end=0x08037ED4)
                        before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x44))
                        self.u.reg_write(base.UC_ARM_REG_PRIMASK, primask)
                        self.call(0x080381D6, callback_owner + 0x10, 0x20006500)
                        expected = bytearray(before)
                        if status == 3 and not foreign:
                            expected[base.seq.OFF_SAVE_OWNER:base.seq.OFF_SAVE_OWNER+4] = bytes(4)
                        self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x44)), bytes(expected))
                        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)
                        self.call(base.seq.STOCK_READ_STORE_WORD, ready, 0)
                        self.assertEqual(self.read(self.u.reg_read(base.UC_ARM_REG_R0)), 9 if status == 3 and not foreign else 11)
                        self.call(base.seq.STOCK_READ_STORE_WORD, phase, 1)
                        self.assertEqual(self.u.mem_read(self.u.reg_read(base.UC_ARM_REG_R0), 1), bytes([0 if status == 3 else 9]))

    def test_save_success_callback_forwards_to_stock_boundary(self):
        p = 0x20006000
        self.word(0x20006500, 2)
        self.call(0x080381D6, p + 0x10, 0x20006500, end=0x08038078)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_R0), p)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_R1), 2)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_SP), 0x20040000)

    def test_save_error_invalidates_snapshot_before_late_ack(self):
        p = 0x20006000
        phase = self.store(bytes([5, 7, 0, 0, 2, 0, 0, 0]))
        meta = self.store(bytes(64))
        self.word(p + 0x48, phase)
        self.word(p + 0x6C, 0x20006400)
        self.word(0x20006500, 3)
        self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
        self.call(0x08037ED0, p, 7, 0, end=0x08037ED4)
        self.call(0x080381D6, p + 0x10, 0x20006500)
        self.assertEqual(self.read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_OWNER), 0)
        self.u.reg_write(base.UC_ARM_REG_R5, p)
        self.u.reg_write(base.UC_ARM_REG_R6, 7)
        self.call(self.labels['c_proj_save_complete'], meta)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')

    def test_wrong_slot_load_completion_preserves_transition_and_dirty(self):
        from phase1_test_support import ProjectTransitionFixture
        for slot in (0, 31, 33, 64, 255):
            with self.subTest(slot=slot):
                self.setUp()
                f = ProjectTransitionFixture(self)
                self.word(f.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
                self.call(0x0803D8B8, f.ctrl, 18)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                self.word(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_OWNER, f.p)
                before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x44))
                self.u.reg_write(base.UC_ARM_REG_R4, f.p)
                self.u.reg_write(base.UC_ARM_REG_R5, slot)
                self.call(self.labels['c_proj_load_complete'], f.meta)
                self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x44)), before)

    def test_load_error_only_cancels_its_own_transition(self):
        from phase1_test_support import ProjectTransitionFixture
        for foreign in (False, True):
            for status in (0, 1, 3, 4):
                with self.subTest(foreign=foreign, status=status):
                    self.setUp()
                    f = ProjectTransitionFixture(self)
                    self.word(f.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
                    self.call(0x0803D8B8, f.ctrl, 18)
                    p = 0x20006000 if foreign else f.p
                    phase = self.store(bytes([0, 0, 0, 0, 9, 0, 0, 0]))
                    self.word(p + 0x48, phase)
                    self.word(p + 0x6C, 0x20006400)  # empty observer list
                    self.word(0x20006500, status)
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                    before = bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x44))
                    self.call(self.labels['c_proj_load_cb'], p + 0x0C, 0x20006500)
                    expected = bytearray(before)
                    if status == 3 and not foreign:
                        expected[base.seq.OFF_TRANS_STATE] = 0
                        expected[base.seq.OFF_SAVE_EDITED] = 1
                    self.assertEqual(bytes(self.u.mem_read(base.seq.SEQ_STATE_ADDR, 0x44)), bytes(expected))
                    self.call(base.seq.STOCK_READ_STORE_WORD, phase, 1)
                    addr = self.u.reg_read(base.UC_ARM_REG_R0)
                    self.assertEqual(self.u.mem_read(addr, 1), bytes([0 if status == 3 else 9]))

    def test_record_start_rejected_inflight_and_restores_interrupt_mask(self):
        from midi_record_test_support import MidiRecordFixture
        for state in (0, 1, 2):
            for primask in (0, 1):
                with self.subTest(state=state, primask=primask):
                    self.setUp()
                    f = MidiRecordFixture(self, 0)
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + 5, bytes([state]))
                    self.u.reg_write(base.UC_ARM_REG_PRIMASK, primask)
                    f.send(0x90)
                    self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)
                    self.assertEqual(self.u.mem_read(f.recorder + 0x60, 2), bytes([60, 96]) if state == 0 else bytes(2))
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), bytes([state == 0]))
                    self.word(f.clock + 0x40, 24)
                    f.send(0x80, velocity=0)
                    self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)

    def test_pending_scan_all_tracks_and_invalid_pointers(self):
        state = base.seq.SEQ_STATE_ADDR
        for track in range(8):
            recorder = 0x20005000 + track * 0x300
            self.word(state + base.seq.OFF_RECORDERS + track * 4, recorder)
        self.call(self.labels['c_records_pending'], state)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_R1), 0)
        for track in range(8):
            recorder = 0x20005000 + track * 0x300
            for offset in (0x60, 0x68, 0x290):
                self.word(recorder + offset, 1)
                self.call(self.labels['c_records_pending'], state)
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_R1), 1)
                self.word(recorder + offset, 0)
        for ptr in (1, 0x20000001, base.seq.SEQ_STATE_ADDR, 0xFFFFFFFF):
            self.word(state + base.seq.OFF_RECORDERS, ptr)
            self.call(self.labels['c_records_pending'], state)
            self.assertEqual(self.u.reg_read(base.UC_ARM_REG_R1), 1)

    def test_pending_midi_record_blocks_mode_switch_and_save_ack(self):
        from midi_record_test_support import MidiRecordFixture
        from phase1_test_support import ProjectTransitionFixture
        f = MidiRecordFixture(self, 7)
        t = ProjectTransitionFixture(self, ctrl=0x20031000, view=0x20031500, p=0x20030000)
        self.word(t.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
        f.send(0x90)
        self.call(0x0803D8B8, t.ctrl, 18)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 5, 1), b'\x00')
        self.call(0x08037ED0, t.p, 0, 0, end=0x08037ED4)
        self.u.reg_write(base.UC_ARM_REG_R5, t.p)
        self.u.reg_write(base.UC_ARM_REG_R6, 0)
        self.call(self.labels['c_proj_save_complete'], t.meta)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
        self.word(f.clock + 0x40, 24)
        f.send(0x80, velocity=0)
        f.finish()
        self.call(0x08037ED0, t.p, 0, 0, end=0x08037ED4)
        self.u.reg_write(base.UC_ARM_REG_R5, t.p)
        self.u.reg_write(base.UC_ARM_REG_R6, 0)
        self.call(self.labels['c_proj_save_complete'], t.meta)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_midi_extreme_notes_preserve_recorder_boundary(self):
        from midi_record_test_support import MidiRecordFixture
        for note in (0, 127):
            with self.subTest(note=note):
                self.setUp()
                f = MidiRecordFixture(self, 7)
                self.u.mem_write(f.recorder + 0x294, b'\xa5' * 16)
                f.send(0x90, note=note)
                self.word(f.clock + 0x40, 24)
                f.send(0x80, note=note, velocity=0)
                f.finish()
                off = 7 * 0xA28 + 31 * 8
                data = bytes(self.u.mem_read(f.patterns, 8 * 0xA28))
                self.assertEqual(data[off], note + 12)
                self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                self.assertEqual(self.u.mem_read(f.recorder + 0x294, 16), b'\xa5' * 16)

    def test_stock_note_ownership_keeps_other_source_until_release(self):
        filt, callback, vt = 0x20004000, 0x20004100, 0x20004200
        on, off = 0x0800E900, 0x0800E904
        self.word(callback, vt)
        self.word(vt, on | 1); self.word(vt + 4, off | 1)
        self.u.mem_write(on, bytes.fromhex('704700007047'))
        events = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: events.append(a), begin=on, end=off)
        self.call(0x08054F10, filt, callback)
        self.call(0x08054F30, filt, 60, 96, 0)
        self.call(0x08054F30, filt, 60, 96, 0)  # duplicate from same source
        self.assertEqual(events, [on])
        self.call(0x08054F30, filt, 60, 96, 1)  # other source retriggers
        self.assertEqual(events, [on, off, on])
        self.call(0x08054FA8, filt, 60, 0)
        self.assertEqual(events, [on, off, on])
        self.call(0x08054FA8, filt, 60, 1)
        self.assertEqual(events, [on, off, on, off])
        self.call(0x08054FA8, filt, 60, 1)
        self.assertEqual(events, [on, off, on, off])
        self.assertEqual(bytes(self.u.mem_read(filt + 4, 40)), bytes(40))

    def test_midi_decoder_through_ownership_filters_to_pattern(self):
        from midi_record_test_support import MidiRecordFixture
        for track in range(8):
            for seq_enabled in (0, 1):
                for off_status in (0x80, 0x90):
                    with self.subTest(track=track, seq_enabled=seq_enabled, off_status=off_status):
                        self.setUp()
                        f = MidiRecordFixture(self, track)
                        self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([seq_enabled]))
                        f.send(0x90)
                        self.assertEqual(self.u.mem_read(f.recorder + 0x60, 2), bytes([60, 96]))
                        self.word(f.clock + 0x40, 24)
                        f.send(off_status, velocity=0)
                        f.finish()
                        data = bytes(self.u.mem_read(f.patterns, 8 * 0xA28))
                        off = 7 * 0xA28 + 31 * 8
                        self.assertEqual(data[off], 60)
                        self.assertGreater(data[off + 1], 0)
                        self.assertEqual(data[off + 3], 96)
                        self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                        for filt in f.filters:
                            self.assertEqual(bytes(self.u.mem_read(filt + 4, 40)), bytes(40))
                        self.assertEqual(bytes(self.u.mem_read(f.receiver + 0x74, 160)), bytes(160))
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
                        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, 1), b'\x01')

    def test_midi_channel_and_note_translation_to_router_boundary(self):
        # Real decoder -> receiver -> note adapter -> track adapter. Only the
        # terminal router recipient is observed, not replaced with a recorder.
        decoder, receiver, adapter, offset_adapter = 0x20004000, 0x20004100, 0x20004300, 0x20004320
        router, vt, message = 0x20004400, 0x20004420, 0x20004700
        on, off = 0x0800E900, 0x0800E904
        self.word(decoder, receiver)
        self.u.mem_write(decoder + 4, bytes(reversed(range(8))))
        self.u.mem_write(decoder + 0x1C, b'\x01')
        self.word(receiver, 0x080665E4)
        self.word(receiver + 0x24, adapter)
        self.word(adapter, 0x080694D0)
        self.word(adapter + 4, offset_adapter)
        self.word(offset_adapter, 0x08069510)
        self.word(offset_adapter + 4, router)
        self.u.mem_write(offset_adapter + 8, b'\x10')
        self.word(router, vt)
        self.word(vt, on | 1)
        self.word(vt + 4, off | 1)
        self.u.mem_write(on, bytes.fromhex('704700007047'))
        events = []
        self.u.hook_add(base.UC_HOOK_CODE,
            lambda u,a,z,d: events.append((a, tuple(u.reg_read(r) for r in base.REGS))),
            begin=on, end=off)
        for track in range(8):
            for zero_off in (False, True):
                channel = 7 - track
                self.u.mem_write(message, bytes([0x90 | channel, 48, 96]))
                self.call(0x0805AF94, decoder, message)
                self.assertEqual(events[-1], (on, (router, 60, 96, 16 + track)))
                self.u.mem_write(message, bytes([(0x90 if zero_off else 0x80) | channel, 48, 0]))
                self.call(0x0805AF94, decoder, message)
                self.assertEqual(events[-1], (off, (router, 60, 16 + track, 0)))
                self.assertEqual(bytes(self.u.mem_read(receiver + 0x74, 8 * 20)), bytes(8 * 20))
        count = len(events)
        self.u.mem_write(message, bytes([0x98, 48, 96]))  # no matching channel
        self.call(0x0805AF94, decoder, message)
        self.assertEqual(len(events), count)
        self.u.mem_write(decoder + 0x1C, b'\x00')
        self.u.mem_write(message, bytes([0x97, 48, 96]))
        self.call(0x0805AF94, decoder, message)
        self.assertEqual(len(events), count)

    def test_record_group_routes_tracks_and_checks_all_three_gates(self):
        import struct
        group, recorder, patterns = 0x20004500, 0x20007000, 0x20010000
        for track in range(8):
            for flags in ((1, 1, 0), (0, 1, 0), (1, 0, 0), (1, 1, 1)):
                with self.subTest(track=track, flags=flags):
                    self.setUp()
                    self.word(group, 0x08068CE4)
                    self.word(group + 8, self.store(struct.pack('<3I', *flags)))
                    self.word(group + 0x0C + track * 4, recorder)
                    self.word(recorder, 0x08067864)
                    self.word(recorder + 0x50, patterns)
                    self.word(recorder + 0x14, self.store(bytes([1, 0, 0, 0])))
                    self.word(recorder + 0x20, self.store(bytes(4)))
                    self.word(recorder + 0x5C, self.store(bytes(8)))
                    self.word(recorder + 0x0C, self.store(struct.pack('<3I', 7, 31, 0)))
                    self.word(recorder + 0x10, self.store(struct.pack('<2I', 7, 31)))
                    clock = self.store(bytes(4))
                    self.word(recorder + 0x1C, clock)
                    self.call(0x08036A80, group, 60, 96, 16 + track)
                    enabled = flags == (1, 1, 0)
                    self.assertEqual(self.u.mem_read(recorder + 0x60, 2), bytes([60, 96]) if enabled else bytes(2))
                    self.word(clock + 0x40, 24)
                    self.call(0x08036AC4, group, 60, 16 + track)
                    self.word(0x20040000, 0)
                    self.call(0x08048D2A, recorder, 7, 31, 24)
                    data = bytes(self.u.mem_read(patterns, 8 * 0xA28))
                    if enabled:
                        off = 7 * 0xA28 + 31 * 8
                        self.assertEqual(data[off], 60)
                        self.assertEqual(data[off + 3], 96)
                        self.assertGreater(data[off + 1], 0)
                        self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                    else:
                        self.assertEqual(data, bytes(len(data)))
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), bytes([enabled]))

    def test_recorder_callbacks_through_pending_to_pattern(self):
        # Real recorder vtable and Note On/Off/flush code. This starts at the
        # recorder interface, not at UART/USB ingress or the MIDI dispatcher.
        import struct
        recorder, patterns = 0x20004000, 0x20010000
        self.word(recorder, 0x08067864)
        self.word(recorder + 0x50, patterns)
        self.word(recorder + 0x14, self.store(bytes([1, 0, 0, 0])))
        self.word(recorder + 0x20, self.store(bytes(4)))
        self.word(recorder + 0x5C, self.store(bytes(8)))
        for pattern in (0, 7):
            for step in (0, 31):
                with self.subTest(pattern=pattern, step=step):
                    self.u.mem_write(patterns, bytes(8 * 0xA28))
                    self.u.mem_write(recorder + 0x60, bytes(0x240))
                    self.word(recorder + 0x0C, self.store(struct.pack('<3I', pattern, step, 0)))
                    self.word(recorder + 0x10, self.store(struct.pack('<2I', pattern, step)))
                    clock = self.store(bytes(4))
                    self.word(recorder + 0x1C, clock)
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, b'\x00')
                    self.call(0x080492A8, recorder, 60, 96)
                    self.assertEqual(self.u.mem_read(recorder + 0x60, 2), bytes([60, 96]))
                    self.assertEqual(bytes(self.u.mem_read(patterns, 8 * 0xA28)), bytes(8 * 0xA28))
                    self.word(clock + 0x40, 24)
                    self.call(0x0804933E, recorder, 60)
                    self.assertEqual(bytes(self.u.mem_read(patterns, 8 * 0xA28)), bytes(8 * 0xA28))
                    self.word(0x20040000, 0)  # flush fifth argument: timing offset
                    self.call(0x08048D2A, recorder, pattern, step, 24)
                    data = bytes(self.u.mem_read(patterns, 8 * 0xA28))
                    off = pattern * 0xA28 + step * 8
                    self.assertEqual(data[off], 60)
                    self.assertEqual(data[off + 3], 96)
                    self.assertGreater(data[off + 1], 0)
                    self.assertEqual(data[:off] + data[off + 8:], bytes(len(data) - 8))
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, 1), b'\x01')
                    self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                    self.call(0x0804933E, recorder, 60)
                    self.call(0x08048D2A, recorder, pattern, step, 24)
                    self.assertEqual(bytes(self.u.mem_read(patterns, len(data))), data)
                    self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_direct_record_to_nonselected_pattern_marks_dirty(self):
        player, patterns = 0x20004000, 0x20010000
        self.word(player + 0x50, patterns)
        for pattern in (0, 7):
            self.word(player + 0x14, self.store(bytes([1 if pattern == 0 else 0, 0, 0, 0])))
            for step in (0, 31):
                self.u.mem_write(patterns, bytes(8 * 0xA28))
                pending = 1 | (step << 1) | (pattern << 6) | (96 << 9) | (3 << 27)
                self.word(player + 0x64 + 60*4, pending)
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, b'\x00')
                result = self.call(0x08048E70, player, 60, 24)
                self.assertEqual(result, 0)  # nonselected pattern, no store notify needed
                data = bytes(self.u.mem_read(patterns, 8 * 0xA28))
                off = pattern*0xA28 + step*8
                self.assertEqual(data[off], 60)
                self.assertGreater(data[off+1], 0)
                self.assertEqual(data[off+2:off+5], bytes([8, 96, 7]))
                self.assertEqual(data[:off] + data[off+8:], bytes(len(data)-8))
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_SAVE_EDITED, 1), b'\x01')
                # Consumed pending record: another call must not write/mark dirty.
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                self.call(0x08048E70, player, 60, 24)
                self.assertEqual(bytes(self.u.mem_read(patterns, len(data))), data)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_direct_delay_to_nonselected_pattern_marks_dirty(self):
        player, patterns = 0x20004000, 0x20010000
        self.word(player + 0x50, patterns)
        self.word(player + 0x14, self.store(bytes(4)))
        self.call(0x0804909C, player, 7, 31, 42)
        data = bytes(self.u.mem_read(patterns, 8*0xA28))
        off = 7*0xA28 + 31*8 + 5
        self.assertEqual(data[off], 42)
        self.assertEqual(data[:off] + data[off+1:], bytes(len(data)-1))
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')

    def test_record_selected_pattern_updates_stores_and_preserves_canaries(self):
        from verify_phase1_candidate import EmulatorHarness
        h = EmulatorHarness(self.image, self.labels)
        env = h.setup_step_view_environment(active_pattern=7)
        recorder = 0x20004500
        h.word(recorder + 0x50, env['patterns'])
        h.word(recorder + 0x14, h.readword(0x20001000 + 0x28))
        h.word(recorder + 0x54, env['st1'])
        h.word(recorder + 0x58, env['st2'])
        h.word(recorder + 0x64 + 60*4, 1 | (31<<1) | (7<<6) | (96<<9) | (3<<27))
        before = bytes(h.u.mem_read(env['patterns'], 8*0xA28))
        self.assertEqual(h.call(0x08048E70, recorder, 60, 24), 1)
        h.call(base.seq.STOCK_NOTIFY_STORE, env['st1'])
        h.call(base.seq.STOCK_NOTIFY_STORE, env['st2'])
        after = bytes(h.u.mem_read(env['patterns'], 8*0xA28))
        off = 7*0xA28 + 31*8
        self.assertEqual(after[off], 60)
        self.assertEqual(after[off+3], 96)
        self.assertEqual(after[:off] + after[off+8:], before[:off] + before[off+8:])
        self.assertEqual(h.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')

    def test_parameter_commit_without_pad_marks_dirty_and_blocks_switch(self):
        from verify_phase1_candidate import EmulatorHarness
        from phase1_test_support import ProjectTransitionFixture
        for setter, store_name, offset, value in (
            (0x080549B0, 'st1', 3, 99), (0x080549D8, 'st1', 2, 5),
            (0x08054A04, 'st1', 4, 3), (0x08054A30, 'st1', 5, 80),
            (0x08054A5C, 'st2', 0, 72), (0x08054A84, 'st2', 1, 12),
            (0x08054AB0, 'st2', 6, 1),
        ):
            for step in (0, 31):
                with self.subTest(setter=hex(setter), step=step):
                    h = EmulatorHarness(self.image, self.labels)
                    env = h.setup_step_view_environment(active_pattern=7)
                    f = ProjectTransitionFixture(h)
                    h.word(f.ctrl + 0x0C, h.store(bytes([1, 0, 0, 0])))
                    h.call(setter, env[store_name], step, value)
                    h.call(base.seq.STOCK_NOTIFY_STORE, env[store_name])
                    self.assertEqual(h.u.mem_read(env['patterns'] + 7*0xA28 + 8*step + offset, 1), bytes([value]))
                    self.assertEqual(h.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
                    h.call(0x0803D8B8, f.ctrl, 18)
                    self.assertEqual(h.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), bytes(2))

    def test_nonmutation_commit_notification_preserves_dirty_and_abi(self):
        listener, store = 0x20004000, 0x20006000
        # Unknown source takes the stock no-op return, without dereferencing stores.
        self.call(0x08048208, listener, store, 0)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x00')

    def test_knob_input_marks_dirty_and_transition_blocks_delivery(self):
        ctrl, view, vt = 0x20004000, 0x20005000, 0x20006000
        self.word(ctrl + 0x8C, self.store(bytes(4)))
        self.word(ctrl + 0x78, view); self.word(view, vt)
        callback = 0x0800E900
        self.word(vt + 0x10, callback | 1)
        self.u.mem_write(callback, bytes.fromhex('7047'))
        events = []
        self.u.hook_add(base.UC_HOOK_CODE, lambda u,a,z,d: events.append(tuple(u.reg_read(r) for r in base.REGS[:3])), begin=callback, end=callback)
        for knob in range(8):
            for delta in (0, 1, 0xFFFFFFFF):
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x00')
                self.call(0x0803DDE0, ctrl, knob, delta)
                self.assertEqual(events[-1], (view, knob, delta))
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), bytes([int(delta != 0)]))
        count = len(events)
        for state in (1, 2):
            self.u.mem_write(base.seq.SEQ_STATE_ADDR + 5, bytes([state]))
            self.call(0x0803DDE0, ctrl, 0, 1)
            self.assertEqual(len(events), count)

    def test_save_completion_retains_edits_after_snapshot(self):
        # Execute real save entry until the serialization continuation, then
        # inject the completion boundary. This is a race contract, not SD I/O.
        p, slot = 0x20004000, 7
        meta = self.store(bytes(64))
        for edited in (False, True):
            for primask in (0, 1):
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                self.call(0x08037ED0, p, slot, 0, end=0x08037ED4)
                if edited:
                    listener, store = 0x20006000, 0x20006100
                    self.word(listener + 0x1C, store)
                    self.call(0x08048208, listener, store, 1, end=0x0804820C)
                self.u.reg_write(base.UC_ARM_REG_R5, p)
                self.u.reg_write(base.UC_ARM_REG_R6, slot)
                self.u.reg_write(base.UC_ARM_REG_PRIMASK, primask)
                self.call(self.labels['c_proj_save_complete'], meta)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), bytes([edited]))
                self.assertEqual(self.u.reg_read(base.UC_ARM_REG_PRIMASK), primask)
                # A late duplicate completion must not acknowledge later edits.
                self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
                self.call(self.labels['c_proj_save_complete'], meta)
                self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')

    def test_save_gate_preserves_bank_across_stock_read(self):
        for bank in (0, 1):
            view = 0x20004000
            meta = bytearray(48); meta[44] = bank * 32
            self.word(view + 0x18, self.store(bytes(meta)))
            ready = self.store(bytes([8, 0, 0, 0]))
            self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, bytes([bank]))
            self.u.reg_write(base.UC_ARM_REG_R4, view)
            result = self.call(self.labels['c_save_btn_gate'], ready, 0)
            self.assertEqual(result, ready + 0x40)

    def test_clear_guard_preserves_bank_across_stock_read(self):
        p, action = 0x20004000, 0x20006000
        self.word(p + 0x1C, action)
        meta = bytearray(48); meta[44] = 32
        self.word(p + 0x44, self.store(bytes(meta)))
        phase = self.store(bytes(8))
        self.u.mem_write(base.seq.SEQ_STATE_ADDR + 4, b'\x01')
        self.u.reg_write(base.UC_ARM_REG_R4, action)
        self.u.reg_write(base.UC_ARM_REG_R5, p)
        self.assertEqual(self.call(self.labels['c_proj_dispatch_guard'], phase, 1), phase + 0x44)

    def test_timer_forwards_all_five_arguments(self):
        self.word(0x200014F0, 0x20005000)
        self.word(0x20040000, 0x20007000)
        self.call(self.labels['c_proj_timer_or_direct'], 5, 0, 1, 0x08038075,
                  end=base.seq.STOCK_TIMER_SCHEDULE)
        self.assertEqual(self.u.reg_read(base.UC_ARM_REG_R1), 0)
        self.assertEqual(self.read(self.u.reg_read(base.UC_ARM_REG_SP)), 0x20007000)

    def test_allocator_rejects_integer_wrap(self):
        for size in (0xFFFFFFFC, 0xFFFFFFFF):
            cur = self.read(base.seq.HEAP_CUR_PTR)
            self.assertEqual(self.call(base.seq.STOCK_ALLOCATOR_ADDR, size), 0xFFFFFFFF)
            self.assertEqual(self.read(base.seq.HEAP_CUR_PTR), cur)

    def test_missing_project_context_never_commits_mode(self):
        from phase1_test_support import ProjectTransitionFixture
        for missing in (None, 0x0C, 0x20, 0x24, 0x28):
            self.setUp()
            f = ProjectTransitionFixture(self)
            self.word(f.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
            if missing is None:
                self.word(f.ctrl + 0x50, 0)
            else:
                self.word(f.view + missing, 0)
            self.call(0x0803D8B8, f.ctrl, 18)
            self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), bytes(2))
            self.assertEqual(self.u.mem_read(0x20006D90, 16), bytes(16))

    def test_real_dispatch_waits_for_matching_completion(self):
        from phase1_test_support import ProjectTransitionFixture
        f = ProjectTransitionFixture(self)
        self.word(f.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
        self.call(0x0803D8B8, f.ctrl, 18)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), b'\x00\x02')
        self.u.reg_write(base.UC_ARM_REG_R4, f.p + 0x100)
        self.u.reg_write(base.UC_ARM_REG_R5, 32)
        self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, b'\x01')
        self.call(self.labels['c_proj_load_complete'], f.meta)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), b'\x00\x02')
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + base.seq.OFF_PROJECT_DIRTY, 1), b'\x01')
        f.finish()
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), b'\x01\x00')

    def test_invalid_slot_rejects_without_dispatch(self):
        from phase1_test_support import ProjectTransitionFixture
        f = ProjectTransitionFixture(self)
        self.word(f.ctrl + 0x0C, self.store(bytes([1, 0, 0, 0])))
        self.u.mem_write(base.seq.SEQ_STATE_ADDR + base.seq.OFF_LAST_SEQ_PROJ, b'\xff')
        self.call(0x0803D8B8, f.ctrl, 18)
        self.assertEqual(self.u.mem_read(base.seq.SEQ_STATE_ADDR + 4, 2), bytes(2))


if __name__ == '__main__':
    unittest.main()

