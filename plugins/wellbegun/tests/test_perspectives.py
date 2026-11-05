import copy
import tempfile
import unittest
from unittest.mock import patch

from test_support import checking, create_project, read_all, record_success, runtime, start, state, success_payload, tx, write_plan


def verdict(cid):
    return {'status': 'ACCEPT', 'independent': True, 'context_id': cid}


class PerspectiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = create_project(self.temp.name, whole_run=True)
        self.base = runtime.plan(self.root)[0]

    def raises(self, code, func, *args, **kwargs):
        with self.assertRaises(runtime.Error) as caught:
            func(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def plan_with(self, **changes):
        records = copy.deepcopy(self.base)
        for key, fields in changes.items():
            records[key].update(fields)
        write_plan(self.root, list(records.values()))

    def finish_steps(self):
        start(self.root); checking(self.root); record_success(self.root)
        start(self.root, 'gate', 'independent', 'verifier'); record_success(self.root, 'gate', 'independent', True)
        start(self.root, 'consumer'); checking(self.root, 'consumer'); record_success(self.root, 'consumer')

    def enter(self, verifiers, context_id=None, **extra):
        for cid in verifiers.values():
            read_all(self.root, 'whole-run', cid, 'verifier')
        payload = {'op': 'set', 'record': 'whole-run', 'status': 'checking', 'verifier_context_ids': verifiers, **extra}
        if state(self.root)['records']['whole-run']['status'] == 'queued':
            payload.update(context_id=context_id or next(iter(verifiers.values())), actor=None, workspace=str(self.root.parent.resolve()), target=['src.py'])
        else:
            payload['context_id'] = context_id or 'fixer'
        return tx(self.root, payload)

    def result(self, status, verdicts, **extra):
        payload = success_payload('whole-run', 'conductor')
        payload.update(status=status, verdicts=verdicts, **extra)
        return tx(self.root, payload)

    def reject_abuse_round(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.result('fixing', {'goal': verdict('v1'), 'money': verdict('v3')},
                    findings=[{'id': 'abuse-1', 'clause': 'works', 'reproduction': 'idle socket keeps a seat'}])
        read_all(self.root, 'whole-run', 'fixer', 'implementer')

    def test_perspectives_validation(self):
        for bad in [['goal', 'goal'], ['speed'], []]:
            with self.subTest(perspectives=bad):
                self.plan_with(gate={'perspectives': bad})
                self.raises('invalid_plan', runtime.plan, self.root)
        self.plan_with(gate={'perspectives': None})
        self.raises('invalid_plan', runtime.plan, self.root)
        self.plan_with(gate={'perspectives': ['goal', 'abuse']}, producer={'perspectives': ['goal']})
        self.raises('invalid_plan', runtime.plan, self.root)
        self.plan_with(gate={'perspectives': ['goal', 'abuse']})
        self.assertEqual(['goal', 'abuse'], runtime.plan(self.root)[0]['gate']['perspectives'])
        self.plan_with(**{'whole-run': {'kind': 'phase', 'grade': 'basic'}})
        runtime.plan(self.root)
        self.plan_with(**{'whole-run': {'kind': 'whole-run'}, 'gate': {'grade': 'basic'}})
        self.raises('invalid_plan', runtime.plan, self.root)

    def test_perspectives_of_defaults(self):
        records, _ = runtime.plan(self.root)
        self.assertEqual(['goal', 'abuse', 'money'], runtime.perspectives_of(records['whole-run']))
        self.assertEqual([], runtime.perspectives_of(records['gate']))
        self.assertTrue(runtime.parallel(records['whole-run']))
        self.assertFalse(runtime.parallel(records['gate']))

    def test_basic_phase_completes_without_verifier(self):
        self.plan_with(**{'whole-run': {'kind': 'phase', 'grade': 'basic'}})
        tx(self.root, {'op': 'reconcile', 'reason': 'basic phase'})
        self.finish_steps()
        read_all(self.root, 'whole-run', 'integrator', 'implementer')
        tx(self.root, {'op': 'set', 'record': 'whole-run', 'status': 'checking', 'context_id': 'integrator', 'actor': None, 'workspace': str(self.root.parent.resolve()), 'target': ['src.py']})
        record_success(self.root, 'whole-run', 'integrator')
        self.assertEqual('verified', state(self.root)['records']['whole-run']['status'])
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])

    def test_whole_run_parallel_accept(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        rec = state(self.root)['records']['whole-run']
        self.assertEqual(('checking', None), (rec['status'], rec['current_verifier']))
        self.result('verified', {'goal': verdict('v1'), 'abuse': verdict('v2'), 'money': verdict('v3')})
        self.assertEqual('verified', state(self.root)['records']['whole-run']['status'])
        self.assertEqual(1, state(self.root)['scopes']['scope-whole-run']['round'])
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])

    def test_whole_run_needs_distinct_independent_verifiers(self):
        self.finish_steps()
        self.raises('invalid_input', self.enter, {'goal': 'v1', 'abuse': 'v1', 'money': 'v3'})
        self.raises('not_independent', self.enter, {'goal': 'v1', 'abuse': 'v2', 'money': 'worker'})
        self.raises('invalid_input', self.enter, {'goal': 'v1', 'abuse': 'v2'})

    def test_whole_run_verified_needs_every_perspective(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.raises('not_independent', self.result, 'verified', {'goal': verdict('v1'), 'abuse': verdict('v2')})
        self.raises('not_independent', self.result, 'verified', {'goal': verdict('v1'), 'abuse': verdict('v2'), 'money': verdict('v9')})

    def test_whole_run_reject_reruns_only_rejecting_perspective(self):
        self.reject_abuse_round()
        self.assertEqual({'goal': 'v1', 'money': 'v3'}, state(self.root)['records']['whole-run']['accepted_perspectives'])
        self.raises('invalid_input', self.enter, {'goal': 'v5', 'abuse': 'v4'})
        self.enter({'abuse': 'v4'})
        self.assertEqual(2, state(self.root)['records']['whole-run']['round'])
        self.result('verified', {'abuse': verdict('v4')}, resolved_findings=['abuse-1'])
        self.assertEqual('verified', state(self.root)['records']['whole-run']['status'])
        self.assertEqual(2, state(self.root)['scopes']['scope-whole-run']['round'])
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])

    def test_whole_run_fixed_now_reruns_perspective(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.result('fixing', {'goal': verdict('v1'), 'abuse': verdict('v2'), 'money': verdict('v3')}, recheck_perspectives=['goal'])
        read_all(self.root, 'whole-run', 'fixer', 'implementer')
        self.raises('invalid_input', self.enter, {'goal': 'v4', 'abuse': 'v5'})
        self.enter({'goal': 'v4'})
        self.assertEqual(2, state(self.root)['records']['whole-run']['round'])
        self.result('verified', {'goal': verdict('v4')})
        self.assertEqual('verified', state(self.root)['records']['whole-run']['status'])

    def test_whole_run_fixing_needs_findings_or_recheck(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.raises('invalid_input', self.result, 'fixing', {'goal': verdict('v1')})

    def test_whole_run_finding_needs_perspective_prefix(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.raises('invalid_input', self.result, 'fixing', {}, findings=[{'id': 'x-1', 'clause': 'works', 'reproduction': 'r'}])

    def test_whole_run_rerun_perspectives_reopens_accepted(self):
        self.reject_abuse_round()
        self.raises('invalid_input', self.enter, {'abuse': 'v4'}, rerun_perspectives=['money'])
        self.enter({'abuse': 'v4', 'money': 'v5'}, rerun_perspectives=['money'])
        self.assertEqual({'goal': 'v1'}, state(self.root)['records']['whole-run']['accepted_perspectives'])

    def test_single_perspective_whole_run_keeps_single_verifier_path(self):
        self.plan_with(**{'whole-run': {'perspectives': ['goal']}})
        tx(self.root, {'op': 'reconcile', 'reason': 'single perspective'})
        self.finish_steps()
        start(self.root, 'whole-run', 'final', 'verifier')
        record_success(self.root, 'whole-run', 'final', True)
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])


    def test_whole_run_verified_before_upgrade_stays_valid(self):
        with patch.object(runtime, 'parallel', return_value=False):
            self.finish_steps()
            start(self.root, 'whole-run', 'final', 'verifier')
            record_success(self.root, 'whole-run', 'final', True)
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])

    def test_whole_run_round_started_before_upgrade_finishes_single(self):
        with patch.object(runtime, 'parallel', return_value=False):
            self.finish_steps()
            start(self.root, 'whole-run', 'final', 'verifier')
        record_success(self.root, 'whole-run', 'final', True)
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])

    def test_whole_run_resumes_inflight_round_with_same_verifiers(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        tx(self.root, {'op': 'set', 'record': 'whole-run', 'status': 'stopped', 'reason': 'user interruption'})
        read_all(self.root, 'whole-run', 'v1', 'verifier')
        tx(self.root, {'op': 'set', 'record': 'whole-run', 'status': 'checking', 'context_id': 'v1'})
        self.assertEqual(1, state(self.root)['records']['whole-run']['round'])
        self.result('verified', {'goal': verdict('v1'), 'abuse': verdict('v2'), 'money': verdict('v3')})
        self.assertEqual('verified', state(self.root)['records']['whole-run']['status'])

    def test_whole_run_replacement_verifier_starts_new_round(self):
        self.finish_steps()
        self.enter({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        tx(self.root, {'op': 'set', 'record': 'whole-run', 'status': 'stopped', 'reason': 'verifier lost'})
        for cid in ['v1', 'v4', 'v3']:
            read_all(self.root, 'whole-run', cid, 'verifier')
        tx(self.root, {'op': 'set', 'record': 'whole-run', 'status': 'checking', 'context_id': 'v1', 'verifier_context_ids': {'goal': 'v1', 'abuse': 'v4', 'money': 'v3'}})
        self.assertEqual(2, state(self.root)['records']['whole-run']['round'])
        self.raises('not_independent', self.result, 'verified', {'goal': verdict('v1'), 'abuse': verdict('v2'), 'money': verdict('v3')})
        self.result('verified', {'goal': verdict('v1'), 'abuse': verdict('v4'), 'money': verdict('v3')})

    def test_contract_change_clears_accepted_perspectives(self):
        self.reject_abuse_round()
        self.plan_with(**{'whole-run': {'goal': 'Whole run meets begin.md, revised'}})
        tx(self.root, {'op': 'reconcile', 'reason': 'whole-run contract changed'})
        self.assertEqual({}, state(self.root)['records']['whole-run']['accepted_perspectives'])
        self.raises('invalid_input', self.enter, {'abuse': 'v4'})


if __name__ == '__main__':
    unittest.main()
