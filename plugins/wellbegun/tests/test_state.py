import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from test_support import add_decision, attach_decision, change_decision, checking, single_kind, create_project, read_all, record_success, runtime, start, state, success_payload, tx, write_plan


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = create_project(self.temp.name)

    def raises(self, code, func, *args, **kwargs):
        with self.assertRaises(runtime.Error) as caught:
            func(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def basic(self):
        if state(self.root)['records']['producer']['status'] == 'stopped':
            read_all(self.root); checking(self.root); record_success(self.root)
        else:
            start(self.root); checking(self.root); record_success(self.root)

    def fail(self, fid='F1', cid='worker'):
        return tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'fixing', 'context_id': cid, 'findings': [{'id': fid, 'clause': 'works', 'reproduction': 'python3 check.py reproduces contract failure'}]})

    def fresh_producer(self):
        records, _ = runtime.plan(self.root)
        records['producer']['grade'] = 'fresh'
        write_plan(self.root, list(records.values()))
        tx(self.root, {'op': 'reconcile', 'reason': 'fresh boundary'})

    def test_expected_consumer_edits_only_stale_broad_checks(self):
        root = self.root
        (root.parent / 'consumer.py').write_text('value = 1\n')
        start(root)
        checking(root)
        payload = success_payload()
        payload['checks'][0]['files'].append('consumer.py')
        tx(root, payload)
        start(root, 'gate', 'independent', 'verifier')
        payload = success_payload('gate', 'independent', True)
        payload['checks'][0]['files'].append('consumer.py')
        tx(root, payload)
        read_all(root, 'consumer')
        tx(root, {'op': 'set', 'record': 'consumer', 'status': 'implementing', 'context_id': 'worker', 'actor': None, 'workspace': str(root.parent), 'target': ['consumer.py']})
        (root.parent / 'consumer.py').write_text('value = 2\n')
        payload = success_payload('consumer')
        payload.update(op='complete-basic', target=['consumer.py'])
        payload['checks'][0]['files'].append('consumer.py')
        tx(root, payload)
        self.assertEqual('complete', runtime.validate(root)['cursor'])
        packet = runtime.context(root, 'producer', context_id='worker')
        self.assertFalse(packet['sections']['state']['checks'][0]['reusable'])
        self.assertEqual(1, state(root)['records']['gate']['round'])
        self.assertEqual('archived', tx(root, {'op': 'archive'})['status'])

    def test_same_file_consumer_append_needs_no_foundation_recheck(self):
        root = self.root
        (root.parent / 'check.py').write_text('from pathlib import Path\nns = {}\nexec(Path("src.py").read_text(), ns)\nassert ns["value"] == 1\n')
        def checked(record='producer', cid='worker', fresh=False):
            result = subprocess.run(['python3', 'check.py'], cwd=root.parent, capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr.decode())
            payload = success_payload(record, cid, fresh)
            payload['checks'][0]['exit_status'] = result.returncode
            if not fresh:
                payload['op'] = 'complete-basic'
            return tx(root, payload)
        start(root); checked()
        start(root, 'gate', 'v1', 'verifier'); checked('gate', 'v1', True)
        start(root, 'consumer', 'consumer-writer')
        owner = state(root)['records']['consumer']['context_id']
        for iteration in range(4):
            with (root.parent / 'src.py').open('a') as file:
                file.write('consumer_' + str(iteration) + ' = value + 1\n')
            tx(root, {'op': 'checkpoint', 'record': 'consumer', 'reason': 'normal same-file addition', 'target': ['src.py']})
            self.assertEqual('ok', runtime.context(root, context_id=owner)['status'])
            for key in ['producer', 'gate']:
                self.assertEqual('verified', state(root)['records'][key]['status'])
            self.assertEqual('consumer', state(root)['cursor'])
        checked('consumer', owner)
        self.assertEqual('complete', runtime.validate(root)['cursor'])
        self.assertEqual(1, state(root)['records']['producer']['round'])
        self.assertEqual(1, state(root)['records']['gate']['round'])
        self.assertEqual({}, state(root)['findings'])

    def test_g1_009_concrete_action_survives_same_file_recheck_and_saved_stops(self):
        # The consumer's own target drift still forces a recheck; verified
        # foundations stay verified.
        action = 'Implement render_consumer() output escaping; parsing is done, keep existing parser.'
        for stopped in [None, 'user interruption', 'pending decision']:
            with self.subTest(stopped=stopped), tempfile.TemporaryDirectory() as directory:
                root = create_project(directory)
                (root.parent / 'check.py').write_text('from pathlib import Path\nns = {}\nexec(Path("src.py").read_text(), ns)\nassert ns["value"] == 1\n')
                start(root); checking(root); record_success(root)
                start(root, 'gate', 'v1', 'verifier'); record_success(root, 'gate', 'v1', True)
                start(root, 'consumer', 'consumer-writer')
                tx(root, {'op': 'checkpoint', 'record': 'consumer', 'reason': 'save continuation before edits', 'next_action': action})
                checkpoint = runtime.load_evidence(root, state(root)['events'][-1])
                self.assertEqual(action, checkpoint['next_action'])
                if stopped:
                    payload = {'op': 'set', 'record': 'consumer', 'status': 'stopped', 'reason': stopped}
                    if stopped == 'pending decision':
                        pending = root / 'pending'; pending.mkdir()
                        (pending / 'Q.json').write_text(json.dumps({'question': 'Continue renderer?'}))
                        payload['pending'] = 'pending/Q.json'
                    tx(root, payload)
                    self.assertEqual(action, state(root)['records']['consumer']['next_action'])
                with (root.parent / 'src.py').open('a') as file:
                    file.write('def parse_consumer(text):\n    return value + int(text)\n')
                tx(root, {'op': 'reconcile', 'reason': 'normal same-file addition'})
                consumer = state(root)['records']['consumer']
                self.assertEqual('verified', state(root)['records']['producer']['status'])
                self.assertEqual('verified', state(root)['records']['gate']['status'])
                self.assertEqual(action, consumer['next_action'])
                invalidation = runtime.load_evidence(root, consumer['evidence'][-1])
                self.assertEqual(action, invalidation['previous_next_action'])
                if stopped:
                    self.assertEqual(stopped, consumer['stop_reason'])
                if stopped == 'pending decision':
                    self.assertEqual('blocked', state(root)['cursor'])
                    self.raises('pending_mismatch', tx, root, {'op': 'set', 'record': 'consumer', 'status': 'implementing'})
                    (root / 'pending/Q.json').write_text(json.dumps({'question': 'Continue renderer?', 'answer': 'Continue with current owner.', 'decision_key': 'theme.owner'}))
                    tx(root, {'op': 'resolve-pending', 'record': 'consumer', 'decision_key': 'theme.owner'})
                    self.assertEqual(action, state(root)['records']['consumer']['next_action'])
                result = subprocess.run(['python3', 'check.py'], cwd=root.parent, capture_output=True)
                self.assertEqual(0, result.returncode, result.stderr.decode())
                packet = runtime.context(root, 'consumer', context_id='consumer-writer', remember=True)
                self.assertEqual(action, packet['sections']['state']['next_action'])
                tx(root, {'op': 'set', 'record': 'consumer', 'status': 'implementing'})
                self.assertEqual(action, state(root)['records']['consumer']['next_action'])
                self.assertIn('def parse_consumer', (root.parent / 'src.py').read_text())
                payload = success_payload('consumer', 'consumer-writer'); payload['op'] = 'complete-basic'
                payload['checks'][0]['exit_status'] = result.returncode
                tx(root, payload)
                self.assertEqual('complete', runtime.validate(root)['cursor'])

    def test_same_file_foundation_break_is_caught_by_consumer_checks(self):
        root = self.root
        (root.parent / 'check.py').write_text('from pathlib import Path\nns = {}\nexec(Path("src.py").read_text(), ns)\nassert ns["value"] == 1\n')
        self.basic(); start(root, 'gate', 'v1', 'verifier'); record_success(root, 'gate', 'v1', True)
        start(root, 'consumer')
        with (root.parent / 'src.py').open('a') as file:
            file.write('consumer = value + 1\nvalue = 0\n')
        tx(root, {'op': 'checkpoint', 'record': 'consumer', 'reason': 'consumer changed shared file', 'target': ['src.py']})
        tx(root, {'op': 'reconcile', 'reason': 'verified foundations are not reopened by code edits'})
        for key in ['producer', 'gate']:
            self.assertEqual('verified', state(root)['records'][key]['status'])
        runtime.context(root, 'consumer', context_id='worker', remember=True)
        checking(root, 'consumer')
        result = subprocess.run(['python3', 'check.py'], cwd=root.parent, capture_output=True)
        self.assertNotEqual(0, result.returncode)
        payload = success_payload('consumer'); payload['checks'][0]['exit_status'] = result.returncode
        self.raises('failed_checks', tx, root, payload)
        payload.update(status='fixing', findings=[{'id': 'SAME-FILE-FOUNDATION', 'clause': 'works', 'reproduction': 'python3 check.py fails: value must remain 1'}])
        tx(root, payload)
        self.assertEqual('unresolved', state(root)['findings']['SAME-FILE-FOUNDATION']['status'])
        self.assertEqual('fixing', state(root)['records']['consumer']['status'])

    def test_g1_008_stopped_consumer_preserves_ownership_without_bypassing_blockers(self):
        root = self.root
        contracts, _ = runtime.plan(root)
        after = copy.deepcopy(contracts['consumer'])
        after.update(id='after', scope_id='after-scope', requires=['consumer'])
        write_plan(root, [*contracts.values(), after])
        tx(root, {'op': 'reconcile', 'reason': 'downstream fixture', 'approved_new_scopes': ['after-scope'], 'approval': 'fixture'})
        add_decision(root)
        (root.parent / 'consumer.py').write_text('value = 1\n')
        (root.parent / 'after.py').write_text('value = 1\n')
        start(root); checking(root)
        payload = success_payload(); payload['checks'][0]['files'].append('consumer.py')
        tx(root, payload)
        start(root, 'gate', 'independent', 'verifier')
        payload = success_payload('gate', 'independent', True)
        payload['checks'][0]['files'].append('consumer.py'); tx(root, payload)
        runtime.context(root, 'consumer', context_id='worker', remember=True)
        tx(root, {'op': 'set', 'record': 'consumer', 'status': 'implementing', 'context_id': 'worker', 'actor': None, 'workspace': str(root.parent), 'target': ['consumer.py']})
        (root.parent / 'consumer.py').write_text('value = 2\n')
        tx(root, {'op': 'checkpoint', 'record': 'consumer', 'reason': 'normal edit before interruption', 'target': ['consumer.py']})
        tx(root, {'op': 'set', 'record': 'consumer', 'status': 'stopped', 'reason': 'user interruption'})
        runtime.context(root, 'consumer', context_id='worker', remember=True)
        self.assertEqual('ok', runtime.validate(root)['status'])
        tx(root, {'op': 'reconcile', 'reason': 'resume identity check'})
        for key in ['producer', 'gate']:
            self.assertEqual('verified', state(root)['records'][key]['status'])
            self.assertEqual(1, state(root)['records'][key]['round'])
        runtime.context(root, 'consumer', context_id='worker', remember=True)
        # A verified foundation's code change is not a blocker; later checks own it.
        foundation = root.parent / 'src.py'; original = foundation.read_text()
        foundation.write_text('broken foundation\n')
        self.assertEqual('ok', runtime.context(root, 'consumer', context_id='worker')['status'])
        foundation.write_text(original)
        tx(root, {'op': 'set', 'record': 'consumer', 'status': 'implementing'})
        pending = root / 'pending'; pending.mkdir()
        question = pending / 'q.json'; question.write_text(json.dumps({'question': 'Continue?'}))
        tx(root, {'op': 'set', 'record': 'consumer', 'status': 'stopped', 'reason': 'decision required', 'pending': 'pending/q.json'})
        self.raises('pending_mismatch', tx, root, {'op': 'set', 'record': 'consumer', 'status': 'implementing'})
        question.write_text(json.dumps({'question': 'Continue?', 'answer': 'Continue with current owner', 'decision_key': 'theme.owner'}))
        tx(root, {'op': 'resolve-pending', 'record': 'consumer', 'decision_key': 'theme.owner'})
        runtime.context(root, 'consumer', context_id='worker', remember=True)
        tx(root, {'op': 'set', 'record': 'consumer', 'status': 'implementing'})
        payload = success_payload('consumer'); payload['op'] = 'complete-basic'
        payload['checks'][0]['files'].append('consumer.py'); tx(root, payload)
        runtime.context(root, 'after', context_id='worker', remember=True)
        tx(root, {'op': 'set', 'record': 'after', 'status': 'implementing', 'context_id': 'worker', 'actor': None, 'workspace': str(root.parent), 'target': ['after.py']})
        payload = success_payload('after'); payload['op'] = 'complete-basic'
        payload['checks'][0]['files'].append('after.py'); tx(root, payload)
        self.assertEqual('complete', runtime.validate(root)['cursor'])
        packet = runtime.context(root, 'producer', context_id='worker')
        self.assertFalse(packet['sections']['state']['checks'][0]['reusable'])
        self.assertEqual({}, state(root)['findings'])
        self.assertEqual('archived', tx(root, {'op': 'archive'})['status'])

    def test_direct_basic_is_atomic_and_blocks_pending_and_foundation_input_drift(self):
        index = attach_decision(self.root)
        start(self.root)
        payload = success_payload(); payload['op'] = 'complete-basic'
        bad = copy.deepcopy(payload); bad['checks'][0]['exit_status'] = 1
        before = state(self.root)
        self.raises('failed_checks', tx, self.root, bad)
        self.assertEqual(before, state(self.root))
        pending = self.root / 'pending'; pending.mkdir()
        (pending / 'q.json').write_text('{"question":"unanswered"}')
        self.raises('pending_mismatch', tx, self.root, payload)
        (pending / 'q.json').unlink(); pending.rmdir()
        tx(self.root, payload)
        start(self.root, 'gate', 'independent', 'verifier')
        record_success(self.root, 'gate', 'independent', True)
        start(self.root, 'consumer')
        (self.root.parent / 'src.py').write_text('broken foundation\n')
        payload = success_payload('consumer'); payload.update(op='complete-basic', target=['src.py'])
        change_decision(self.root, index, 'Foundation constraint revised.')
        self.raises('code_drift', tx, self.root, payload)

    def test_successful_rechecks_preserve_rounds_without_spending_failure_cap(self):
        index = attach_decision(self.root)
        for cycle in range(5):
            if state(self.root)['records']['producer']['status'] == 'stopped':
                read_all(self.root)
            else:
                start(self.root)
            payload = success_payload(); payload['op'] = 'complete-basic'
            tx(self.root, payload)
            self.assertEqual(cycle + 1, state(self.root)['records']['producer']['round'])
            if cycle < 4:
                change_decision(self.root, index, 'Revision ' + str(cycle))
                tx(self.root, {'op': 'reconcile', 'reason': 'new intentional foundation revision'})
        change_decision(self.root, index, 'Failing revision')
        tx(self.root, {'op': 'reconcile', 'reason': 'new failing candidate'})
        start(self.root)
        for attempt in range(3):
            checking(self.root)
            self.fail()
        rec = state(self.root)['records']['producer']
        self.assertEqual('stopped', rec['status'])
        self.assertEqual('round_cap', rec['stop_reason'])
        self.assertEqual(8, rec['round'])

    def test_wording_reconcile_does_not_extend_round_allowance(self):
        self.basic()
        records, _ = runtime.plan(self.root)
        records['producer']['goal'] += ' clarified'
        write_plan(self.root, list(records.values()))
        tx(self.root, {'op': 'reconcile', 'reason': 'wording only'})
        self.assertEqual(3, state(self.root)['scopes'][records['producer']['scope_id']]['limit'])

    def test_cli_stdin_direct_basic(self):
        start(self.root)
        payload = success_payload(); payload['op'] = 'complete-basic'
        with patch('sys.stdin', io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(io.StringIO()) as output:
            code = runtime.main(['transition', '--root', str(self.root), '--expected-revision', str(state(self.root)['revision']), '--input', '-'])
        self.assertEqual(0, code)
        self.assertEqual('ok', json.loads(output.getvalue())['status'])
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])

    def test_basic_needs_no_verifier(self):
        self.basic()
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])

    def test_consumer_blocked_until_independent_gate(self):
        self.basic()
        self.raises('blocked', start, self.root, 'consumer')
        self.raises('not_independent', start, self.root, 'gate', 'worker', 'verifier')
        start(self.root, 'gate', 'independent', 'verifier')
        record_success(self.root, 'gate', 'independent', True)
        start(self.root, 'consumer')

    def test_gate_transitive_bypass_validation(self):
        records, _ = runtime.plan(self.root)
        records['consumer']['requires'] = ['producer']
        write_plan(self.root, list(records.values()))
        self.raises('invalid_plan', runtime.plan, self.root)

    def test_fresh_unavailable_stops_and_separate_session_resumes(self):
        self.fresh_producer(); start(self.root); checking(self.root)
        self.assertEqual('independent_verifier_unavailable', state(self.root)['records']['producer']['stop_reason'])
        read_all(self.root, context_id='fresh', audience='verifier')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'context_id': 'fresh', 'verifier_context_id': 'fresh'})
        record_success(self.root, context_id='fresh', fresh=True)
        self.assertEqual(1, state(self.root)['records']['producer']['round'])

    def test_current_round_verifier_required(self):
        self.fresh_producer(); start(self.root)
        read_all(self.root, context_id='v1', audience='verifier')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'verifier_context_id': 'v1'})
        self.fail(cid='v1')
        read_all(self.root, context_id='v2', audience='verifier')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'verifier_context_id': 'v2'})
        old = success_payload(context_id='v1', fresh=True); old['resolved_findings'] = ['F1']
        self.raises('not_independent', tx, self.root, old)
        good = success_payload(context_id='v2', fresh=True); good['resolved_findings'] = ['F1']
        tx(self.root, good)

    def test_g1_001_resumed_writer_cannot_verify_own_work(self):
        self.fresh_producer(); start(self.root, context_id='implementer-A')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'context exhausted'})
        read_all(self.root, context_id='implementer-B')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'implementing', 'context_id': 'implementer-B'})
        (self.root.parent / 'src.py').write_text('value = 2\n')
        tx(self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'B implemented', 'target': ['src.py']})
        read_all(self.root, context_id='implementer-B', audience='verifier')
        self.raises('not_independent', tx, self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'context_id': 'implementer-B', 'verifier_context_id': 'implementer-B'})
        self.assertEqual(['implementer-A', 'implementer-B'], state(self.root)['records']['producer']['implementer_contexts'])
        read_all(self.root, context_id='independent-C', audience='verifier')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'context_id': 'implementer-B', 'verifier_context_id': 'independent-C'})
        record_success(self.root, context_id='independent-C', fresh=True)

    def test_g1_001_fixer_context_recorded_and_cannot_verify_gate(self):
        start(self.root, context_id='original'); checking(self.root, context_id='original'); self.fail(cid='original')
        read_all(self.root, context_id='fixer')
        (self.root.parent / 'src.py').write_text('value = 3\n')
        tx(self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'fixer changed implementation', 'target': ['src.py'], 'context_id': 'fixer'})
        checking(self.root, context_id='fixer')
        payload = success_payload(context_id='fixer'); payload['resolved_findings'] = ['F1']; tx(self.root, payload)
        self.raises('not_independent', start, self.root, 'gate', 'fixer', 'verifier')

    def test_g1_001_lost_verifier_replaced_in_new_counted_round(self):
        self.fresh_producer(); start(self.root)
        read_all(self.root, context_id='v1', audience='verifier')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'verifier_context_id': 'v1'})
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'verifier context lost'})
        read_all(self.root, context_id='v2', audience='verifier')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'context_id': 'v2', 'verifier_context_id': 'v2'})
        self.assertEqual(2, state(self.root)['records']['producer']['round'])
        self.raises('not_independent', record_success, self.root, context_id='v1', fresh=True)
        record_success(self.root, context_id='v2', fresh=True)

    def test_g1_001_verifier_replacement_cannot_bypass_round_cap(self):
        self.fresh_producer(); start(self.root)
        read_all(self.root, context_id='v1', audience='verifier')
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'verifier_context_id': 'v1'})
        for num in range(2, 5):
            tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'verifier context lost'})
            cid = 'v' + str(num)
            read_all(self.root, context_id=cid, audience='verifier')
            tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking', 'context_id': cid, 'verifier_context_id': cid})
        rec = state(self.root)['records']['producer']
        self.assertEqual(('stopped', 3, 'round_cap'), (rec['status'], rec['round'], rec['stop_reason']))

    def test_g1_001_i2_001_all_fresh_kinds_exclude_current_and_ancestor_fixers(self):
        for kind in ['gate', 'phase', 'whole-run']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = create_project(directory)
                records, _ = runtime.plan(root)
                records['gate'].update(single_kind(kind))
                records['consumer'].update(kind='phase', grade='fresh')
                write_plan(root, list(records.values()))
                tx(root, {'op': 'reconcile', 'reason': 'test all supported fresh record kinds'})
                start(root); checking(root); record_success(root)
                start(root, 'gate', 'reviewer', 'verifier')
                tx(root, {'op': 'set', 'record': 'gate', 'status': 'fixing', 'context_id': 'reviewer', 'findings': [{'id': 'G1-001', 'clause': 'works', 'reproduction': 'Fresh scope needs implementation repair'}]})
                read_all(root, 'gate', 'fixer', 'implementer')
                (root.parent / 'repair.py').write_text('repaired = True\n')
                tx(root, {'op': 'checkpoint', 'record': 'gate', 'reason': 'repair current verification scope', 'context_id': 'fixer', 'target': ['repair.py']})
                read_all(root, 'gate', 'fixer', 'verifier')
                self.raises('not_independent', tx, root, {'op': 'set', 'record': 'gate', 'status': 'checking', 'context_id': 'fixer', 'verifier_context_id': 'fixer'})
                read_all(root, 'gate', 'independent', 'verifier')
                tx(root, {'op': 'set', 'record': 'gate', 'status': 'checking', 'context_id': 'fixer', 'verifier_context_id': 'independent'})
                payload = success_payload('gate', 'independent', True)
                payload['checks'][0]['files'] = ['repair.py', 'check.py']; payload['resolved_findings'] = ['G1-001']
                tx(root, payload)
                self.raises('not_independent', start, root, 'consumer', 'fixer', 'verifier')
                start(root, 'consumer', 'next-independent', 'verifier')

    def test_g1_001_i2_001_resumed_fixer_recorded_for_every_kind(self):
        for kind in ['gate', 'phase', 'whole-run']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = create_project(directory)
                records, _ = runtime.plan(root); records['gate'].update(single_kind(kind))
                write_plan(root, list(records.values())); tx(root, {'op': 'reconcile', 'reason': 'fresh record kind'})
                start(root); checking(root); record_success(root)
                start(root, 'gate', 'reviewer', 'verifier')
                tx(root, {'op': 'set', 'record': 'gate', 'status': 'fixing', 'context_id': 'reviewer', 'findings': [{'id': 'G1-001', 'clause': 'works', 'reproduction': 'Repair required'}]})
                tx(root, {'op': 'set', 'record': 'gate', 'status': 'stopped', 'reason': 'fixer context unavailable'})
                read_all(root, 'gate', 'resumed-fixer', 'implementer')
                tx(root, {'op': 'set', 'record': 'gate', 'status': 'fixing', 'context_id': 'resumed-fixer'})
                self.assertIn('resumed-fixer', state(root)['records']['gate']['implementer_contexts'])
                read_all(root, 'gate', 'resumed-fixer', 'verifier')
                self.raises('not_independent', tx, root, {'op': 'set', 'record': 'gate', 'status': 'checking', 'context_id': 'resumed-fixer', 'verifier_context_id': 'resumed-fixer'})

    def test_g1_002_decision_supersede_invalidates_producer_and_gate(self):
        index = add_decision(self.root)
        records, _ = runtime.plan(self.root)
        for rec in records.values():
            rec['decisions'] = ['theme.owner']
        write_plan(self.root, list(records.values())); tx(self.root, {'op': 'reconcile', 'reason': 'selected shared contract'})
        self.basic(); start(self.root, 'gate', 'v', 'verifier'); record_success(self.root, 'gate', 'v', True)
        index['records'][0]['status'] = 'superseded'
        changed = copy.deepcopy(index['records'][0]); changed.update(id='D2', status='approved', source=None, constraints='Shared owner prohibited; require isolated owners.')
        index['records'].append(changed); index['active'][0]['id'] = 'D2'
        (self.root / 'decisions.index.json').write_text(json.dumps(index))
        self.raises('code_drift', runtime.validate, self.root)
        self.raises('code_drift', start, self.root, 'consumer')
        tx(self.root, {'op': 'reconcile', 'reason': 'G1-002 superseded effective contract'})
        self.assertTrue(all(r['status'] == 'queued' for r in state(self.root)['records'].values()))
        self.raises('blocked', start, self.root, 'consumer')
        self.basic(); start(self.root, 'gate', 'new-v', 'verifier'); record_success(self.root, 'gate', 'new-v', True)
        start(self.root, 'consumer')

    def test_g1_002_registry_constraint_change_invalidates_even_with_same_plan(self):
        entries = {'schema': 1, 'entries': [{'key': 'theme', 'status': 'active', 'location': 'src.py', 'contract': 'one owner', 'constraints': 'share state', 'decisions': []}]}
        (self.root / 'registry.index.json').write_text(json.dumps(entries))
        records, _ = runtime.plan(self.root); records['producer']['registry'] = ['theme']
        write_plan(self.root, list(records.values())); tx(self.root, {'op': 'reconcile', 'reason': 'selected registry'})
        self.basic(); start(self.root, 'gate', 'v', 'verifier'); record_success(self.root, 'gate', 'v', True)
        entries['entries'][0]['constraints'] = 'isolate state'
        (self.root / 'registry.index.json').write_text(json.dumps(entries))
        self.raises('code_drift', runtime.context, self.root)
        tx(self.root, {'op': 'reconcile', 'reason': 'G1-002 changed registry contract'})
        self.assertEqual('queued', state(self.root)['records']['producer']['status'])
        self.assertEqual('stopped', state(self.root)['records']['gate']['status'])
        self.assertEqual('checking', state(self.root)['records']['gate']['resume_status'])

    def select_theme_registry(self):
        entries = {'schema': 1, 'entries': [{'key': 'theme', 'status': 'active', 'location': 'src.py', 'contract': 'one owner', 'constraints': 'share state', 'decisions': []}]}
        (self.root / 'registry.index.json').write_text(json.dumps(entries))
        records, _ = runtime.plan(self.root); records['producer']['registry'] = ['theme']
        write_plan(self.root, list(records.values())); tx(self.root, {'op': 'reconcile', 'reason': 'selected registry'})
        return entries

    def test_registry_location_only_change_keeps_verified_records(self):
        entries = self.select_theme_registry()
        self.basic(); start(self.root, 'gate', 'v', 'verifier'); record_success(self.root, 'gate', 'v', True)
        entries['entries'][0]['location'] = 'src.py, shared/save.py'
        (self.root / 'registry.index.json').write_text(json.dumps(entries))
        runtime.context(self.root)
        tx(self.root, {'op': 'reconcile', 'reason': 'registry lists a new file'})
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])
        self.assertEqual('verified', state(self.root)['records']['gate']['status'])

    def test_registry_location_change_with_contract_change_still_invalidates(self):
        entries = self.select_theme_registry()
        self.basic()
        entries['entries'][0].update(location='shared/save.py', contract='two owners')
        (self.root / 'registry.index.json').write_text(json.dumps(entries))
        self.raises('code_drift', runtime.context, self.root)

    def test_input_digest_from_before_082_is_still_accepted(self):
        self.select_theme_registry()
        start(self.root)
        saved = state(self.root)
        records, _ = runtime.plan(self.root)
        saved['records']['producer']['input_digest'] = runtime.digest(runtime.selected_sections(self.root, records['producer']))
        del saved['records']['producer']['registry_locations']
        (self.root / 'state.json').write_text(json.dumps(saved))
        checking(self.root); record_success(self.root)
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])

    def make_081_state(self):
        saved = state(self.root)
        records, _ = runtime.plan(self.root)
        for key, rec in saved['records'].items():
            if rec['input_digest']:
                rec['input_digest'] = runtime.digest(runtime.selected_sections(self.root, records[key]))
                rec.pop('input_identity', None); rec.pop('registry_locations', None)
                if rec['current_result']:
                    evidence = runtime.load_evidence(self.root, rec['current_result'])
                    evidence['input_digest'] = rec['input_digest']
                    pointer = runtime.write_evidence(self.root, evidence)
                    rec['evidence'] = [pointer if e == rec['current_result'] else e for e in rec['evidence']]
                    rec['current_result'] = pointer
        (self.root / 'state.json').write_text(json.dumps(saved))

    def test_081_verified_record_survives_location_change_after_one_helper_call(self):
        entries = self.select_theme_registry()
        self.basic(); start(self.root, 'gate', 'v', 'verifier'); record_success(self.root, 'gate', 'v', True)
        self.make_081_state()
        runtime.context(self.root)
        self.assertIn('input_identity', state(self.root)['records']['producer'])
        entries['entries'][0]['location'] = 'src.py, shared/save.py'
        (self.root / 'registry.index.json').write_text(json.dumps(entries))
        runtime.context(self.root)
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])
        self.assertEqual('verified', state(self.root)['records']['gate']['status'])

    def test_completed_cycle_drift_names_next_step(self):
        records, _ = runtime.plan(self.root)
        records['producer']['registry'] = []
        attach_decision(self.root)
        self.basic(); start(self.root, 'gate', 'v', 'verifier'); record_success(self.root, 'gate', 'v', True)
        start(self.root, 'consumer'); checking(self.root, 'consumer'); record_success(self.root, 'consumer')
        self.assertEqual('complete', state(self.root)['cursor'])
        index = json.loads((self.root / 'decisions.index.json').read_text())
        change_decision(self.root, index, 'Use two owners.')
        with self.assertRaises(runtime.Error) as caught:
            runtime.context(self.root)
        self.assertIn('reconcile', caught.exception.details['next'])

    def test_missing_verification_command_names_expected_and_given(self):
        start(self.root); checking(self.root)
        payload = success_payload()
        payload['checks'][0]['command'] = 'python3 check.py -v'
        with self.assertRaises(runtime.Error) as caught:
            tx(self.root, payload)
        self.assertEqual('failed_checks', caught.exception.code)
        self.assertEqual(['python3 check.py'], caught.exception.details['missing'])
        self.assertEqual(['python3 check.py -v'], caught.exception.details['given'])

    def test_target_changed_while_checking_names_files_and_recovery(self):
        start(self.root); checking(self.root)
        (self.root.parent / 'src.py').write_text('value = 9\n')
        with self.assertRaises(runtime.Error) as caught:
            record_success(self.root)
        self.assertEqual('code_drift', caught.exception.code)
        self.assertEqual(['src.py'], caught.exception.details['files'])
        self.assertIn('reconcile', caught.exception.details['next'])
        tx(self.root, {'op': 'reconcile', 'reason': 'edited target during checking'})
        read_all(self.root); checking(self.root); record_success(self.root)
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])

    def test_g1_002_unrelated_decision_history_does_not_invalidate_success(self):
        self.basic()
        index = add_decision(self.root)
        index['records'][0]['reason'] = 'Unrelated decision update'
        (self.root / 'decisions.index.json').write_text(json.dumps(index))
        self.assertEqual('ok', runtime.validate(self.root)['status'])
        tx(self.root, {'op': 'reconcile', 'reason': 'unrelated update'})
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])

    def test_g1_006_only_selected_input_drift_blocks_checking_and_completion(self):
        for boundary in ['checking', 'verified']:
            for changed in ['source', 'check', 'decision', 'registry', 'runtime']:
                with self.subTest(boundary=boundary, changed=changed), tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as patches:
                    root = create_project(directory)
                    index = add_decision(root)
                    registry = {'schema': 1, 'entries': [{'key': 'foundation', 'status': 'active', 'location': 'src.py', 'contract': 'shared owner', 'constraints': 'single owner', 'decisions': []}]}
                    (root / 'registry.index.json').write_text(json.dumps(registry))
                    contracts, _ = runtime.plan(root)
                    contracts['producer'].update(decisions=['theme.owner'], registry=['foundation'])
                    write_plan(root, list(contracts.values())); tx(root, {'op': 'reconcile', 'reason': 'explicit producer inputs'})
                    start(root); checking(root); record_success(root)
                    start(root, 'gate', 'v', 'verifier'); record_success(root, 'gate', 'v', True)
                    (root.parent / 'consumer.py').write_text('consumer = True\n')
                    read_all(root, 'consumer', 'consumer-worker')
                    tx(root, {'op': 'set', 'record': 'consumer', 'status': 'implementing', 'context_id': 'consumer-worker', 'actor': None, 'workspace': str(root.parent), 'target': ['consumer.py']})
                    if boundary == 'verified':
                        checking(root, 'consumer', 'consumer-worker')
                    if changed == 'source':
                        (root.parent / 'src.py').write_text('value = 2\n')
                    elif changed == 'check':
                        (root.parent / 'check.py').write_text('assert True  # changed input\n')
                    elif changed == 'decision':
                        index['records'][0]['constraints'] = 'require isolated owners'
                        (root / 'decisions.index.json').write_text(json.dumps(index))
                    elif changed == 'registry':
                        registry['entries'][0]['constraints'] = 'require isolated ownership'
                        (root / 'registry.index.json').write_text(json.dumps(registry))
                    else:
                        patches.enter_context(patch.object(runtime, 'runtime_environment', return_value={'python': 'changed', 'platform': 'changed'}))
                    if changed in {'source', 'check', 'runtime'}:
                        # Code, check-input and runtime changes do not reopen verified prerequisites.
                        self.assertEqual('ok', runtime.context(root, 'consumer', context_id='consumer-worker')['status'])
                        runtime.validate(root)
                        if boundary == 'checking':
                            checking(root, 'consumer', 'consumer-worker')
                        else:
                            payload = success_payload('consumer', 'consumer-worker')
                            payload['checks'][0]['files'] = ['consumer.py', 'check.py']
                            tx(root, payload)
                            self.assertEqual('verified', state(root)['records']['consumer']['status'])
                        self.assertEqual('verified', state(root)['records']['gate']['status'])
                        continue
                    before = (root / 'state.json').read_bytes()
                    self.raises('code_drift', runtime.context, root, 'consumer', context_id='consumer-worker')
                    self.raises('code_drift', runtime.validate, root)
                    if boundary == 'checking':
                        self.raises('code_drift', checking, root, 'consumer', 'consumer-worker')
                    else:
                        payload = success_payload('consumer', 'consumer-worker')
                        payload['checks'][0]['files'] = ['consumer.py', 'check.py']
                        self.raises('code_drift', tx, root, payload)
                    self.assertEqual(before, (root / 'state.json').read_bytes())
                    self.assertNotEqual('complete', state(root)['cursor'])
                    tx(root, {'op': 'reconcile', 'reason': 'G1-006 prerequisite changed'})
                    self.assertNotEqual('verified', state(root)['records']['gate']['status'])
                    self.assertNotEqual('verified', state(root)['records']['consumer']['status'])

    def test_g1_006_all_fresh_kinds_check_actual_prerequisite_inputs(self):
        for kind in ['gate', 'phase', 'whole-run']:
            for boundary in ['checking', 'verified']:
                with self.subTest(kind=kind, boundary=boundary), tempfile.TemporaryDirectory() as directory:
                    root = create_project(directory)
                    contracts, _ = runtime.plan(root); contracts['gate'].update(single_kind(kind))
                    write_plan(root, list(contracts.values())); tx(root, {'op': 'reconcile', 'reason': 'supported fresh scope'})
                    index = attach_decision(root)
                    start(root); checking(root); record_success(root)
                    (root.parent / 'review.py').write_text('review_target = True\n')
                    read_all(root, 'gate', 'reviewer', 'verifier')
                    tx(root, {'op': 'set', 'record': 'gate', 'status': 'checking', 'context_id': 'reviewer', 'verifier_context_id': 'reviewer', 'actor': None, 'workspace': str(root.parent), 'target': ['review.py']})
                    if boundary == 'checking':
                        tx(root, {'op': 'set', 'record': 'gate', 'status': 'fixing', 'context_id': 'reviewer', 'findings': [{'id': 'repair', 'clause': 'works', 'reproduction': 'Review needs repair'}]})
                        read_all(root, 'gate', 'fixer', 'implementer')
                        read_all(root, 'gate', 'new-reviewer', 'verifier')
                    change_decision(root, index, 'Producer constraint revised.')
                    before = (root / 'state.json').read_bytes()
                    if boundary == 'checking':
                        self.raises('code_drift', tx, root, {'op': 'set', 'record': 'gate', 'status': 'checking', 'context_id': 'fixer', 'verifier_context_id': 'new-reviewer'})
                    else:
                        payload = success_payload('gate', 'reviewer', True); payload['checks'][0]['files'] = ['review.py', 'check.py']
                        self.raises('code_drift', tx, root, payload)
                    self.assertEqual(before, (root / 'state.json').read_bytes())

    def test_g1_007_reconcile_keeps_pending_and_saved_resume_for_each_active_state(self):
        for resume in ['implementing', 'checking', 'fixing']:
            with self.subTest(resume=resume), tempfile.TemporaryDirectory() as directory:
                root = create_project(directory, basic_only=True)
                start(root)
                if resume in {'checking', 'fixing'}:
                    checking(root)
                if resume == 'fixing':
                    tx(root, {'op': 'set', 'record': 'producer', 'status': 'fixing', 'context_id': 'worker', 'findings': [{'id': 'F1', 'clause': 'works', 'reproduction': 'Repair required'}]})
                pending = root / 'pending'; pending.mkdir()
                question = pending / 'Q.json'; question.write_text(json.dumps({'question': 'Which contract is approved?'}))
                tx(root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'await approved decision', 'pending': 'pending/Q.json'})
                pointer = state(root)['records']['producer']['pending']
                (root.parent / 'src.py').write_text('value = 2\n')
                tx(root, {'op': 'reconcile', 'reason': 'G1-007 code changed during pending decision'})
                rec = state(root)['records']['producer']
                self.assertEqual(('stopped', resume, 'await approved decision'), (rec['status'], rec['resume_status'], rec['stop_reason']))
                self.assertEqual(pointer, rec['pending'])
                self.assertEqual('blocked', runtime.validate(root)['cursor'])
                read_all(root)
                self.raises('pending_mismatch', tx, root, {'op': 'set', 'record': 'producer', 'status': resume, 'context_id': 'worker'})
                question.write_text(json.dumps({'question': 'Which contract is approved?', 'answer': 'Use the approved theme owner.', 'decision_key': 'theme.owner'}))
                tx(root, {'op': 'resolve-pending', 'record': 'producer', 'decision_key': 'theme.owner'})
                read_all(root)
                tx(root, {'op': 'set', 'record': 'producer', 'status': resume, 'context_id': 'worker'})
                if resume != 'checking':
                    checking(root)
                payload = success_payload()
                if resume == 'fixing':
                    payload['resolved_findings'] = ['F1']
                tx(root, payload)
                self.assertEqual('complete', state(root)['cursor'])

    def test_g1_007_pending_gate_can_resolve_after_upstream_invalidation(self):
        index = attach_decision(self.root)
        self.basic(); start(self.root, 'gate', 'reviewer', 'verifier')
        pending = self.root / 'pending'; pending.mkdir()
        question = pending / 'Q.json'; question.write_text(json.dumps({'question': 'Which gate constraint?'}))
        tx(self.root, {'op': 'set', 'record': 'gate', 'status': 'stopped', 'reason': 'await L decision', 'pending': 'pending/Q.json'})
        change_decision(self.root, index, 'Upstream constraint revised.')
        tx(self.root, {'op': 'reconcile', 'reason': 'upstream drift while gate decision pending'})
        self.assertEqual('queued', state(self.root)['records']['producer']['status'])
        self.assertEqual('stopped', state(self.root)['records']['gate']['status'])
        self.raises('pending_mismatch', start, self.root)
        question.write_text(json.dumps({'question': 'Which gate constraint?', 'answer': 'Use current approved owner.', 'decision_key': 'theme.owner'}))
        tx(self.root, {'op': 'resolve-pending', 'record': 'gate', 'decision_key': 'theme.owner'})
        self.basic()
        read_all(self.root, 'gate', 'replacement-reviewer', 'verifier')
        tx(self.root, {'op': 'set', 'record': 'gate', 'status': 'checking', 'context_id': 'replacement-reviewer', 'verifier_context_id': 'replacement-reviewer'})
        record_success(self.root, 'gate', 'replacement-reviewer', True)
        start(self.root, 'consumer'); checking(self.root, 'consumer'); record_success(self.root, 'consumer')
        self.assertEqual('complete', state(self.root)['cursor'])

    def test_g1_007_pending_record_cannot_be_forged_as_queued_or_verified(self):
        start(self.root)
        pending = self.root / 'pending'; pending.mkdir()
        (pending / 'Q.json').write_text(json.dumps({'question': 'Which contract?'}))
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'decision', 'pending': 'pending/Q.json'})
        original = state(self.root)
        for status in ['queued', 'verified']:
            changed = copy.deepcopy(original); changed['records']['producer']['status'] = status
            (self.root / 'state.json').write_text(json.dumps(changed))
            self.raises('invalid_state', runtime.validate, self.root)

    def test_g1_007_orphan_mailbox_blocks_completion_and_dispatch(self):
        start(self.root); checking(self.root)
        pending = self.root / 'pending'; pending.mkdir()
        (pending / 'unrecorded.json').write_text(json.dumps({'question': 'Interrupted before storing pending pointer'}))
        before = (self.root / 'state.json').read_bytes()
        self.raises('pending_mismatch', record_success, self.root)
        self.raises('pending_mismatch', runtime.context, self.root)
        self.assertEqual(before, (self.root / 'state.json').read_bytes())

    def test_round_cap_never_auto_accepts(self):
        start(self.root)
        for number in range(1, 4):
            checking(self.root); self.fail()
            self.assertEqual(number, state(self.root)['scopes']['scope-producer']['round'])
        rec = state(self.root)['records']['producer']
        self.assertEqual(('stopped', 'round_cap'), (rec['status'], rec['stop_reason']))
        self.raises('invalid_transition', record_success, self.root)
        read_all(self.root)
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'fixing'})
        checking(self.root)
        self.assertEqual(3, state(self.root)['records']['producer']['round'])
        self.assertEqual('stopped', state(self.root)['records']['producer']['status'])

    def test_explicit_additional_round_preserves_unresolved_until_pass(self):
        start(self.root)
        for _ in range(3):
            checking(self.root); self.fail()
        tx(self.root, {'op': 'approve-rounds', 'scope_id': 'scope-producer', 'additional': 1, 'approval': 'User approved one additional round'})
        read_all(self.root)
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'fixing'})
        checking(self.root)
        self.raises('unresolved', record_success, self.root)
        payload = success_payload(); payload['resolved_findings'] = ['F1']; tx(self.root, payload)
        self.assertEqual(4, state(self.root)['records']['producer']['round'])

    def test_stopped_inflight_round_resume_does_not_consume_extra_round(self):
        start(self.root); checking(self.root)
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'host context boundary'})
        read_all(self.root)
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'checking'})
        self.assertEqual(1, state(self.root)['records']['producer']['round'])
        record_success(self.root)

    def test_pending_question_replacement_cannot_be_adopted(self):
        start(self.root)
        pending = self.root / 'pending'; pending.mkdir()
        path = pending / 'Q.json'; path.write_text(json.dumps({'question': 'Original question'}))
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'decision', 'pending': 'pending/Q.json'})
        path.write_text(json.dumps({'question': 'Different question', 'answer': 'Approved', 'decision_key': 'theme.owner'}))
        self.raises('pending_mismatch', tx, self.root, {'op': 'resolve-pending', 'record': 'producer', 'decision_key': 'theme.owner'})

    def test_scope_rename_does_not_reset_round_or_finding(self):
        start(self.root); checking(self.root); self.fail()
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'rename review'})
        records, _ = runtime.plan(self.root)
        producer = records.pop('producer'); producer['id'] = 'renamed'
        records['gate']['requires'] = ['renamed']; records['gate']['producers'] = ['renamed']
        write_plan(self.root, [producer] + list(records.values()))
        tx(self.root, {'op': 'reconcile', 'reason': 'display rename'})
        self.assertEqual(1, state(self.root)['records']['renamed']['round'])
        self.assertEqual('unresolved', state(self.root)['findings']['F1']['status'])

    def test_new_scope_needs_approval_old_findings_remain(self):
        start(self.root); checking(self.root); self.fail()
        records, _ = runtime.plan(self.root); records['producer']['scope_id'] = 'new-scope'
        write_plan(self.root, list(records.values()))
        self.raises('scope_change', tx, self.root, {'op': 'reconcile', 'reason': 'renamed scope'})

    def test_stale_revision_lock_and_candidate_atomic_validation(self):
        self.raises('stale_revision', runtime.transition, self.root, 0, {'op': 'checkpoint', 'record': 'producer', 'reason': 'stale'})
        (self.root / '.state.lock').write_text('external writer')
        self.raises('locked', tx, self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'locked'})
        (self.root / '.state.lock').unlink()
        before = (self.root / 'state.json').read_bytes()
        with patch.object(runtime, 'validate_state', side_effect=runtime.Error('invalid_state', 'candidate rejected')):
            self.raises('invalid_state', tx, self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'candidate'})
        self.assertEqual(before, (self.root / 'state.json').read_bytes())

    def test_interruption_before_atomic_replace_leaves_orphan_not_success(self):
        start(self.root); checking(self.root)
        before = (self.root / 'state.json').read_bytes()
        with patch.object(runtime.os, 'replace', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):
                record_success(self.root)
        self.assertEqual(before, (self.root / 'state.json').read_bytes())
        orphans = list((self.root / 'evidence').glob('*.json'))
        self.assertEqual(1, len(orphans))
        self.raises('invalid_evidence', tx, self.root, {'op': 'set', 'record': 'producer', 'status': 'verified', 'context_id': 'worker', 'reuse': [{'evidence': orphans[0].stem, 'covers': ['works']}], 'environment': {'dependencies': 'stdlib'}})
        record_success(self.root)

    def test_post_save_render_failure_reports_saved_revision(self):
        with patch.object(runtime, 'render', side_effect=runtime.Error('invalid_artifact', 'derived failure')):
            result = tx(self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'boundary'})
        self.assertEqual('ok', result['status'])
        self.assertEqual('regenerate with render', result['derived'])
        self.assertEqual(result['revision'], state(self.root)['revision'])

    def test_render_loss_does_not_change_current_state(self):
        start(self.root)
        (self.root / 'run.md').unlink()
        (self.root / 'HANDOFF.md').write_text('requested derived handoff')
        before = state(self.root)
        runtime.render(self.root)
        before['handoff_requested'] = True
        before['revision'] += 1
        self.assertEqual(before, state(self.root))
        self.assertIn('producer', (self.root / 'HANDOFF.md').read_text())

    def test_no_handoff_created_without_request(self):
        self.assertFalse((self.root / 'HANDOFF.md').exists())

    def test_g1_005_requested_handoff_regenerates_after_actual_loss(self):
        (self.root / 'HANDOFF.md').write_text('explicit existing request')
        runtime.render(self.root)
        self.assertTrue(state(self.root)['handoff_requested'])
        before = state(self.root)
        (self.root / 'HANDOFF.md').unlink()
        runtime.render(self.root)
        self.assertTrue((self.root / 'HANDOFF.md').exists())
        self.assertEqual(before, state(self.root))

    def test_g1_005_public_opt_in_survives_generation_failure(self):
        before = state(self.root)
        original_write = Path.write_text
        def fail_handoff(path, *args, **kwargs):
            if path == self.root / 'HANDOFF.md':
                raise OSError('generation interrupted')
            return original_write(path, *args, **kwargs)
        with patch.object(Path, 'write_text', fail_handoff):
            with self.assertRaises(OSError):
                runtime.render(self.root, handoff=True, expected_revision=before['revision'])
        self.assertTrue(state(self.root)['handoff_requested'])
        self.assertFalse((self.root / 'HANDOFF.md').exists())
        runtime.render(self.root)
        self.assertTrue((self.root / 'HANDOFF.md').exists())

    def test_g1_005_opt_in_revision_and_default_no_file(self):
        before = state(self.root)
        runtime.render(self.root)
        self.assertEqual(before, state(self.root))
        self.assertFalse((self.root / 'HANDOFF.md').exists())
        self.raises('stale_revision', runtime.render, self.root, True, before['revision'] - 1)
        self.assertFalse(state(self.root)['handoff_requested'])
        runtime.render(self.root, handoff=True, expected_revision=before['revision'])
        self.assertEqual(before['revision'] + 1, state(self.root)['revision'])
        self.assertTrue((self.root / 'HANDOFF.md').exists())

    def test_g1_005_public_render_cli_creates_and_recreates_requested_handoff(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = runtime.main(['render', '--root', str(self.root), '--handoff', '--expected-revision', str(state(self.root)['revision'])])
        self.assertEqual(0, result)
        self.assertEqual('ok', json.loads(output.getvalue())['status'])
        (self.root / 'HANDOFF.md').unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, runtime.main(['render', '--root', str(self.root)]))
        self.assertTrue((self.root / 'HANDOFF.md').exists())

    def test_check_input_change_keeps_verified_records(self):
        self.basic(); start(self.root, 'gate', 'v', 'verifier'); record_success(self.root, 'gate', 'v', True)
        (self.root.parent / 'check.py').write_text('assert 1 == 1\n')
        self.assertEqual('ok', runtime.context(self.root)['status'])
        tx(self.root, {'op': 'reconcile', 'reason': 'test input changed'})
        self.assertEqual('consumer', state(self.root)['cursor'])
        self.assertTrue(all(state(self.root)['records'][key]['status'] == 'verified' for key in ['producer', 'gate']))
        self.assertEqual(1, state(self.root)['scopes']['scope-producer']['round'])

    def test_runtime_change_keeps_verified_prerequisites(self):
        self.basic(); start(self.root, 'gate', 'v1', 'verifier'); record_success(self.root, 'gate', 'v1', True)
        changed_runtime = {**runtime.runtime_environment(), 'python': 'different-runtime'}
        with patch.object(runtime, 'runtime_environment', return_value=changed_runtime):
            packet = runtime.sections(self.root, runtime.plan(self.root)[0], state(self.root), 'gate', 'verifier')
            self.assertFalse(packet['state']['checks'][0]['reusable'])
            runtime.validate(self.root)
            start(self.root, 'consumer')
            self.assertEqual('implementing', state(self.root)['records']['consumer']['status'])
            self.assertTrue(all(state(self.root)['records'][key]['status'] == 'verified' for key in ['producer', 'gate']))

    def test_dirty_target_not_identified_by_git_head(self):
        start(self.root)
        (self.root.parent / 'src.py').write_text('value = 2\n')
        self.raises('code_drift', runtime.context, self.root)
        tx(self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'implementation edit', 'target': ['src.py']})
        checking(self.root); record_success(self.root)

    def test_deleted_and_new_target_files_are_detected(self):
        start(self.root)
        tx(self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'planned added file', 'target': ['src.py', 'new.py']})
        (self.root.parent / 'new.py').write_text('created')
        self.raises('code_drift', runtime.context, self.root)
        (self.root.parent / 'new.py').unlink(); (self.root.parent / 'src.py').unlink()
        self.raises('code_drift', runtime.context, self.root)

    def test_contract_drift_requires_explicit_invalidation(self):
        self.basic()
        records, _ = runtime.plan(self.root); records['producer']['goal'] += ' revised'
        write_plan(self.root, list(records.values()))
        self.raises('plan_drift', runtime.context, self.root)
        tx(self.root, {'op': 'reconcile', 'reason': 'contract update'})
        rec = state(self.root)['records']['producer']
        self.assertEqual('queued', rec['status'])
        self.assertTrue(rec['evidence'])

    def test_successful_command_facts_reused_across_gate(self):
        self.basic()
        pointer = state(self.root)['records']['producer']['current_result']
        start(self.root, 'gate', 'v', 'verifier')
        payload = success_payload('gate', 'v', True); del payload['checks']
        payload.update(reuse=[{'evidence': pointer, 'covers': ['works']}], environment={'dependencies': 'stdlib'})
        tx(self.root, payload)
        self.assertEqual('verified', state(self.root)['records']['gate']['status'])

    def test_failed_command_is_not_advertised_or_accepted_as_reusable(self):
        start(self.root); checking(self.root)
        payload = success_payload()
        payload.update(status='fixing', findings=[{'id': 'failed-command', 'clause': 'works', 'reproduction': 'python3 check.py exits 1'}])
        payload['checks'][0]['exit_status'] = 1
        tx(self.root, payload)
        packet = runtime.context(self.root, 'producer', context_id='worker')
        self.assertFalse(packet['sections']['state']['checks'][0]['reusable'])
        pointer = state(self.root)['records']['producer']['current_result']
        checking(self.root)
        payload = success_payload(); del payload['checks']
        payload.update(reuse=[{'evidence': pointer, 'covers': ['works']}], environment={'dependencies': 'stdlib'}, resolved_findings=['failed-command'])
        self.raises('stale_evidence', tx, self.root, payload)
        self.assertEqual('unresolved', state(self.root)['findings']['failed-command']['status'])
        payload = success_payload(); payload['resolved_findings'] = ['failed-command']
        tx(self.root, payload)
        packet = runtime.context(self.root, 'producer', context_id='worker')
        self.assertTrue(packet['sections']['state']['checks'][0]['reusable'])

    def test_external_unknown_or_environment_drift_cannot_reuse(self):
        for mutation in [{'external_state': True}, {'environment_known': False}, {'environment': {'dependencies': 'changed'}}]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = create_project(directory)
                start(root); checking(root)
                payload = success_payload(); payload['checks'][0].update(mutation); tx(root, payload)
                packet = runtime.context(root, 'producer', context_id='worker')
                self.assertEqual('environment' in mutation, packet['sections']['state']['checks'][0]['reusable'])
                pointer = state(root)['records']['producer']['current_result']
                start(root, 'gate', 'v', 'verifier')
                payload = success_payload('gate', 'v', True); del payload['checks']
                payload.update(reuse=[{'evidence': pointer, 'covers': ['works']}], environment={'dependencies': 'stdlib'})
                self.raises('stale_evidence', tx, root, payload)

    def test_evidence_tampering_and_json_corruption_block_dispatch(self):
        self.basic()
        pointer = state(self.root)['records']['producer']['current_result']
        path = self.root / 'evidence' / (pointer + '.json')
        original = path.read_text(); path.write_text(original.replace('stdlib', 'tampered'))
        self.raises('invalid_evidence', runtime.context, self.root)
        path.write_text(original)
        saved = state(self.root); saved['records']['producer']['current_result'] = None
        (self.root / 'state.json').write_text(json.dumps(saved))
        self.raises('invalid_state', runtime.context, self.root)
        (self.root / 'state.json').write_text('{')
        self.raises('invalid_artifact', runtime.context, self.root)

    def test_pending_answer_requires_matching_decision_and_actual_answer(self):
        start(self.root)
        pending = self.root / 'pending'; pending.mkdir()
        path = pending / 'Q1.json'; path.write_text(json.dumps({'question': 'Owner?', 'answer': '', 'decision_key': 'theme.owner'}))
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'decision', 'pending': 'pending/Q1.json'})
        self.raises('pending_mismatch', tx, self.root, {'op': 'resolve-pending', 'record': 'producer', 'decision_key': 'theme.owner'})
        path.write_text(json.dumps({'question': 'Owner?', 'answer': 'Use shared owner.', 'decision_key': 'theme.owner'}))
        self.raises('pending_mismatch', runtime.context, self.root)
        tx(self.root, {'op': 'resolve-pending', 'record': 'producer', 'decision_key': 'theme.owner'})
        self.assertFalse(path.exists())
        read_all(self.root)
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'implementing'})
        self.assertEqual('implementing', state(self.root)['records']['producer']['status'])

    def test_resume_workspace_or_target_drift_never_guessed_complete(self):
        start(self.root)
        tx(self.root, {'op': 'set', 'record': 'producer', 'status': 'stopped', 'reason': 'context exhausted'})
        read_all(self.root)
        self.raises('workspace_drift', tx, self.root, {'op': 'set', 'record': 'producer', 'status': 'implementing', 'workspace': '/somewhere'})
        (self.root.parent / 'src.py').write_text('changed')
        self.raises('code_drift', tx, self.root, {'op': 'set', 'record': 'producer', 'status': 'implementing'})

    def test_legacy_init_cannot_overwrite_existing_run(self):
        (self.root / 'state.json').unlink()
        before = (self.root / 'run.md').read_bytes()
        self.raises('legacy', runtime.transition, self.root, 0, {'op': 'init', 'cycle': 'new', 'mode': 'companion'})
        self.assertEqual(before, (self.root / 'run.md').read_bytes())

    def complete(self):
        self.basic()
        start(self.root, 'gate', 'v', 'verifier'); record_success(self.root, 'gate', 'v', True)
        start(self.root, 'consumer'); checking(self.root, 'consumer'); record_success(self.root, 'consumer')

    def test_archive_complete_bundle_keeps_project_decisions(self):
        self.complete()
        old = state(self.root)
        decisions = (self.root / 'decisions.index.json').read_bytes()
        result = tx(self.root, {'op': 'archive'})
        self.assertEqual('archived', result['status'])
        destination = Path(result['destination'])
        self.assertEqual(old, json.loads((destination / 'state.json').read_text()))
        for name in ['plan.md', 'run.md', 'evidence']:
            self.assertTrue((destination / name).exists())
            self.assertFalse((self.root / name).exists())
        self.assertEqual(decisions, (self.root / 'decisions.index.json').read_bytes())
        self.assertFalse((self.root / 'state.json').exists())

    def test_archive_blocks_incomplete_and_orphan_pending(self):
        self.raises('blocked', tx, self.root, {'op': 'archive'})
        self.complete()
        pending = self.root / 'pending'; pending.mkdir(); (pending / 'unanswered.json').write_text('{}')
        self.raises('pending_mismatch', tx, self.root, {'op': 'archive'})

    def test_archive_interrupted_cleanup_resumes_from_manifest(self):
        self.complete()
        revision = state(self.root)['revision']
        original_unlink = Path.unlink
        interrupted = []
        def unlink(path, *args, **kwargs):
            if path == self.root / 'state.json' and not interrupted:
                interrupted.append(True)
                raise OSError('interrupted archive cleanup')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', unlink):
            with self.assertRaises(OSError):
                tx(self.root, {'op': 'archive'})
        self.assertTrue((self.root / '.archive.json').exists())
        self.raises('archive_in_progress', runtime.context, self.root)
        result = runtime.transition(self.root, revision, {'op': 'archive'})
        self.assertEqual('archived', result['status'])
        self.assertFalse((self.root / '.archive.json').exists())

    def verify_producer_and_gate(self):
        start(self.root); checking(self.root); record_success(self.root)
        start(self.root, 'gate', 'independent', 'verifier'); record_success(self.root, 'gate', 'independent', True)

    def test_verified_record_survives_later_code_change(self):
        self.verify_producer_and_gate()
        (self.root.parent / 'src.py').write_text('value = 2\n')
        self.assertEqual('ok', runtime.context(self.root, 'consumer', context_id='consumer-worker')['status'])
        runtime.validate(self.root)
        self.assertEqual('verified', state(self.root)['records']['producer']['status'])
        self.assertEqual('verified', state(self.root)['records']['gate']['status'])

    def test_verified_record_survives_runtime_change(self):
        self.verify_producer_and_gate()
        with patch.object(runtime, 'runtime_environment', return_value={'python': '0.0', 'platform': 'other'}):
            runtime.validate(self.root)
            self.assertEqual('ok', runtime.context(self.root, 'consumer', context_id='consumer-worker')['status'])



class RecheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = create_project(self.temp.name, whole_run=True)

    def raises(self, code, func, *args, **kwargs):
        with self.assertRaises(runtime.Error) as caught:
            func(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def change_contract(self, key, text):
        records, _ = runtime.plan(self.root)
        records[key]['completion'][0]['text'] = text
        write_plan(self.root, list(records.values()))
        tx(self.root, {'op': 'reconcile', 'reason': 'contract wording changed'})

    def recheck(self, key, cid='rechecker', reason='wording only', **extra):
        read_all(self.root, key, cid, 'implementer')
        payload = {'op': 'set', 'record': key, 'status': 'checking', 'context_id': cid, 'recheck_reason': reason, **extra}
        if state(self.root)['records'][key]['status'] == 'queued':
            payload.update(actor=None, workspace=str(self.root.parent.resolve()), target=['src.py'])
        return tx(self.root, payload)

    def test_contract_change_recheck_with_reason_skips_verifier(self):
        start(self.root); checking(self.root); record_success(self.root)
        start(self.root, 'gate', 'independent', 'verifier'); record_success(self.root, 'gate', 'independent', True)
        self.change_contract('gate', 'Observable contract holds, worded more clearly.')
        self.assertEqual('queued', state(self.root)['records']['gate']['status'])
        self.recheck('gate')
        tx(self.root, success_payload('gate', 'rechecker'))
        gate = state(self.root)['records']['gate']
        self.assertEqual('verified', gate['status'])
        self.assertEqual('wording only', runtime.load_evidence(self.root, gate['current_result'])['recheck_reason'])
        runtime.validate(self.root)
        notes = runtime.context(self.root, 'whole-run', context_id='final')['notes']
        self.assertEqual([{'record': 'gate', 'reason': 'wording only'}], notes['rechecks'])

    def test_recheck_reason_rejected_without_prior_accept(self):
        start(self.root); checking(self.root); record_success(self.root)
        self.raises('invalid_transition', self.recheck, 'gate')
        self.assertEqual('queued', state(self.root)['records']['gate']['status'])

    def test_recheck_reason_rejected_while_fixing(self):
        start(self.root); checking(self.root); record_success(self.root)
        start(self.root, 'gate', 'v1', 'verifier'); record_success(self.root, 'gate', 'v1', True)
        self.change_contract('gate', 'Observable contract holds, worded more clearly.')
        read_all(self.root, 'gate', 'v2', 'verifier')
        tx(self.root, {'op': 'set', 'record': 'gate', 'status': 'checking', 'context_id': 'v2', 'verifier_context_id': 'v2', 'actor': None, 'workspace': str(self.root.parent.resolve()), 'target': ['src.py']})
        tx(self.root, {'op': 'set', 'record': 'gate', 'status': 'fixing', 'context_id': 'v2', 'findings': [{'id': 'F1', 'clause': 'works', 'reproduction': 'r'}]})
        self.raises('invalid_transition', self.recheck, 'gate', 'fixer')

    def finish_steps(self):
        start(self.root); checking(self.root); record_success(self.root)
        start(self.root, 'gate', 'independent', 'verifier'); record_success(self.root, 'gate', 'independent', True)
        start(self.root, 'consumer'); checking(self.root, 'consumer'); record_success(self.root, 'consumer')

    def enter_whole_run(self, verifiers):
        for cid in verifiers.values():
            read_all(self.root, 'whole-run', cid, 'verifier')
        tx(self.root, {'op': 'set', 'record': 'whole-run', 'status': 'checking', 'context_id': next(iter(verifiers.values())), 'verifier_context_ids': verifiers, 'actor': None, 'workspace': str(self.root.parent.resolve()), 'target': ['src.py']})

    def whole_run_result(self, status, verdicts, **extra):
        payload = success_payload('whole-run', 'conductor')
        payload.update(status=status, verdicts={p: {'status': 'ACCEPT', 'independent': True, 'context_id': cid} for p, cid in verdicts.items()}, **extra)
        tx(self.root, payload)

    def test_partial_whole_run_accept_cannot_recheck(self):
        self.finish_steps()
        self.enter_whole_run({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.whole_run_result('fixing', {'goal': 'v1'}, recheck_perspectives=['abuse'])
        self.change_contract('whole-run', 'Observable contract holds, worded more clearly.')
        self.raises('invalid_transition', self.recheck, 'whole-run', 'worker')

    def test_fixed_now_round_cannot_recheck_after_contract_change(self):
        self.finish_steps()
        self.enter_whole_run({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.whole_run_result('fixing', {'goal': 'v1', 'abuse': 'v2', 'money': 'v3'}, recheck_perspectives=['abuse'])
        self.change_contract('whole-run', 'Observable contract holds, worded more clearly.')
        self.raises('invalid_transition', self.recheck, 'whole-run')

    def test_stopped_whole_run_rechecks_with_implementer_reads(self):
        self.finish_steps()
        self.enter_whole_run({'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.whole_run_result('verified', {'goal': 'v1', 'abuse': 'v2', 'money': 'v3'})
        self.change_contract('gate', 'Observable contract holds, worded more clearly.')
        self.assertEqual(('stopped', 'checking'), (state(self.root)['records']['whole-run']['status'], state(self.root)['records']['whole-run']['resume_status']))
        self.recheck('gate')
        tx(self.root, success_payload('gate', 'rechecker'))
        runtime.context(self.root, 'consumer', context_id='worker', remember=True)
        tx(self.root, {**success_payload('consumer'), 'op': 'complete-basic'})
        self.recheck('whole-run', 'rechecker-2', 'gate wording only')
        tx(self.root, success_payload('whole-run', 'rechecker-2'))
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])

    def test_parallel_whole_run_recheck_skips_verifiers(self):
        start(self.root); checking(self.root); record_success(self.root)
        start(self.root, 'gate', 'independent', 'verifier'); record_success(self.root, 'gate', 'independent', True)
        start(self.root, 'consumer'); checking(self.root, 'consumer'); record_success(self.root, 'consumer')
        verifiers = {'goal': 'v1', 'abuse': 'v2', 'money': 'v3'}
        for cid in verifiers.values():
            read_all(self.root, 'whole-run', cid, 'verifier')
        tx(self.root, {'op': 'set', 'record': 'whole-run', 'status': 'checking', 'context_id': 'v1', 'verifier_context_ids': verifiers, 'actor': None, 'workspace': str(self.root.parent.resolve()), 'target': ['src.py']})
        payload = success_payload('whole-run', 'conductor')
        payload['verdicts'] = {p: {'status': 'ACCEPT', 'independent': True, 'context_id': cid} for p, cid in verifiers.items()}
        tx(self.root, payload)
        self.change_contract('whole-run', 'Observable contract holds, worded more clearly.')
        self.recheck('whole-run')
        tx(self.root, success_payload('whole-run', 'rechecker'))
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])


if __name__ == '__main__':
    unittest.main()
