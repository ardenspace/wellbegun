import json
import tempfile
import unittest

from test_support import checking, create_project, read_all, record_success, runtime, start, state, tx, write_plan


def fail(root, record='producer', fid='F1', cid='worker'):
    return tx(root, {'op': 'set', 'record': record, 'status': 'fixing', 'context_id': cid, 'findings': [{'id': fid, 'clause': 'works', 'reproduction': 'python3 check.py reproduces contract failure'}]})


class RoundLimitTests(unittest.TestCase):
    def project(self, **limits):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return create_project(temp.name, round_limits=limits or None)

    def raises(self, code, func, *args, **kwargs):
        with self.assertRaises(runtime.Error) as caught:
            func(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_two_round_limit_stops_after_second_reject(self):
        root = self.project(producer=2)
        self.assertEqual({'round': 0, 'limit': 2, 'allowance': 2}, state(root)['scopes']['scope-producer'])
        start(root)
        checking(root); fail(root)
        self.assertEqual('fixing', state(root)['records']['producer']['status'])
        checking(root); fail(root)
        rec = state(root)['records']['producer']
        self.assertEqual(('stopped', 'round_cap', 2), (rec['status'], rec['stop_reason'], rec['round']))
        self.raises('invalid_transition', record_success, root)

    def test_missing_round_limit_keeps_three(self):
        root = self.project()
        self.assertEqual({'round': 0, 'limit': 3, 'allowance': 3}, state(root)['scopes']['scope-producer'])
        start(root)
        for _ in range(2):
            checking(root); fail(root)
        self.assertEqual('fixing', state(root)['records']['producer']['status'])
        checking(root); fail(root)
        self.assertEqual(('stopped', 'round_cap'), (state(root)['records']['producer']['status'], state(root)['records']['producer']['stop_reason']))

    def test_invalid_round_limit_rejected(self):
        root = self.project()
        records, _ = runtime.plan(root)
        for bad in [1, 4, '2', True, None, 2.0]:
            records['producer']['round_limit'] = bad
            write_plan(root, list(records.values()))
            self.raises('invalid_plan', runtime.plan, root)

    def test_replan_does_not_change_existing_scope_limit(self):
        root = self.project()
        records, _ = runtime.plan(root)
        records['producer']['round_limit'] = 2
        write_plan(root, list(records.values()))
        tx(root, {'op': 'reconcile', 'reason': 'tighten round limit'})
        self.assertEqual({'round': 0, 'limit': 3, 'allowance': 3}, state(root)['scopes']['scope-producer'])

    def test_replan_raising_round_limit_keeps_existing_scope_limit(self):
        root = self.project(producer=2)
        records, _ = runtime.plan(root)
        records['producer']['round_limit'] = 3
        write_plan(root, list(records.values()))
        tx(root, {'op': 'reconcile', 'reason': 'loosen round limit'})
        self.assertEqual({'round': 0, 'limit': 2, 'allowance': 2}, state(root)['scopes']['scope-producer'])
        start(root)
        checking(root); fail(root)
        checking(root); fail(root)
        rec = state(root)['records']['producer']
        self.assertEqual(('stopped', 'round_cap', 2), (rec['status'], rec['stop_reason'], rec['round']))

    def test_new_scope_from_replan_uses_round_limit(self):
        root = self.project()
        records, _ = runtime.plan(root)
        extra = dict(records['producer'], id='extra', scope_id='scope-extra', round_limit=2)
        write_plan(root, list(records.values()) + [extra])
        tx(root, {'op': 'reconcile', 'reason': 'add extra step', 'approved_new_scopes': ['scope-extra'], 'approval': 'User approved the extra step'})
        self.assertEqual({'round': 0, 'limit': 2, 'allowance': 2}, state(root)['scopes']['scope-extra'])

    def test_reopened_scope_extends_by_its_allowance(self):
        root = self.project(producer=2)
        start(root); checking(root); record_success(root)
        (root.parent / 'src.py').write_text('value = 2\n')
        tx(root, {'op': 'reconcile', 'reason': 'new intentional foundation revision'})
        self.assertEqual(3, state(root)['scopes']['scope-producer']['limit'])

    def test_state_without_allowance_reads_as_three(self):
        root = self.project()
        start(root); checking(root); record_success(root)
        data = state(root)
        del data['scopes']['scope-producer']['allowance']
        (root / 'state.json').write_text(json.dumps(data))
        (root.parent / 'src.py').write_text('value = 2\n')
        tx(root, {'op': 'reconcile', 'reason': 'new intentional foundation revision'})
        self.assertEqual(4, state(root)['scopes']['scope-producer']['limit'])

    def test_invalid_allowance_in_state_rejected(self):
        root = self.project()
        data = state(root)
        data['scopes']['scope-producer']['allowance'] = 5
        (root / 'state.json').write_text(json.dumps(data))
        self.raises('invalid_state', runtime.context, root)

    def test_approve_rounds_extends_two_round_scope(self):
        root = self.project(producer=2)
        start(root)
        for _ in range(2):
            checking(root); fail(root)
        tx(root, {'op': 'approve-rounds', 'scope_id': 'scope-producer', 'additional': 1, 'approval': 'User approved one additional round'})
        read_all(root)
        tx(root, {'op': 'set', 'record': 'producer', 'status': 'fixing'})
        checking(root)
        self.assertEqual(3, state(root)['records']['producer']['round'])
        self.assertEqual('checking', state(root)['records']['producer']['status'])

    def test_replacement_verifier_stops_at_two_round_cap(self):
        root = self.project(producer=2)
        records, _ = runtime.plan(root)
        records['producer']['grade'] = 'fresh'
        write_plan(root, list(records.values()))
        tx(root, {'op': 'reconcile', 'reason': 'fresh boundary'})
        self.assertEqual(2, state(root)['scopes']['scope-producer']['limit'])
        start(root)
        read_all(root, context_id='v1', audience='verifier')
        tx(root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'verifier_context_id': 'v1'})
        for num in range(2, 4):
            tx(root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'verifier context lost'})
            cid = 'v' + str(num)
            read_all(root, context_id=cid, audience='verifier')
            tx(root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'context_id': cid, 'verifier_context_id': cid})
        rec = state(root)['records']['producer']
        self.assertEqual(('stopped', 2, 'round_cap'), (rec['status'], rec['round'], rec['stop_reason']))


if __name__ == '__main__':
    unittest.main()
