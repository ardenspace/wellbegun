import copy
import json
from pathlib import Path
import tempfile
import unittest

from test_support import add_decision, create_project, read_all, runtime, start, state, success_payload, tx, write_plan


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = create_project(self.temp.name, basic_only=True)

    def raises(self, code, func, *args, **kwargs):
        with self.assertRaises(runtime.Error) as caught:
            func(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def attach(self, index=None, registry_keys=None):
        records, _ = runtime.plan(self.root)
        rec = records['producer']
        rec['decisions'] = ['theme.owner'] if index else []
        rec['registry'] = registry_keys or []
        write_plan(self.root, [rec])
        tx(self.root, {'op': 'reconcile', 'reason': 'selected input contract'})

    def save_index(self, index):
        (self.root / 'decisions.index.json').write_text(json.dumps(index))

    def test_remember_and_same_context_reuse_preserve_fresh_reads(self):
        index = add_decision(self.root)
        self.attach(index, ['ui'])
        packet = runtime.context(self.root, context_id='worker', remember=True)
        self.assertTrue(packet['remembered'])
        self.assertNotIn('receipts', packet)
        repeated = runtime.context(self.root, context_id='worker', remember=True)
        self.assertNotIn('decision:theme.owner', repeated['sections'])
        self.assertIn('decision:theme.owner', repeated['reused_sections'])
        self.assertNotIn('registry:ui', repeated['sections'])
        for cid, audience in [('new-worker', 'implementer'), ('worker', 'verifier')]:
            fresh = runtime.context(self.root, context_id=cid, audience=audience)
            self.assertIn('decision:theme.owner', fresh['sections'])
        index['records'][0]['constraints'] = 'Changed current constraint'
        self.save_index(index)
        changed = runtime.context(self.root, context_id='worker')
        self.assertIn('decision:theme.owner', changed['sections'])

    def test_same_context_reuses_selected_bodies_across_records(self):
        index = add_decision(self.root)
        self.attach(index)
        records, _ = runtime.plan(self.root)
        second = copy.deepcopy(records['producer'])
        second.update(id='second', scope_id='second-scope', requires=['producer'])
        write_plan(self.root, [records['producer'], second])
        tx(self.root, {'op': 'reconcile', 'reason': 'second scope', 'approved_new_scopes': ['second-scope'], 'approval': 'test fixture'})
        runtime.context(self.root, 'producer', context_id='worker', remember=True)
        second_packet = runtime.context(self.root, 'second', context_id='worker', remember=True)
        self.assertNotIn('decision:theme.owner', second_packet['sections'])
        self.assertIn('decision:theme.owner', second_packet['reused_sections'])
        contracts, pdigest = runtime.plan(self.root)
        runtime.ensure_reads(self.root, contracts, runtime.load_state(self.root, contracts, pdigest), 'second', 'worker', 'implementer')

    def test_code_recheck_reuses_bodies_but_requires_current_state_read(self):
        index = add_decision(self.root); self.attach(index)
        start(self.root)
        payload = success_payload(); payload['op'] = 'complete-basic'
        tx(self.root, payload)
        with (self.root.parent / 'src.py').open('a') as file:
            file.write('consumer = value + 1\n')
        tx(self.root, {'op': 'reconcile', 'reason': 'same-file code addition'})
        contracts, pdigest = runtime.plan(self.root)
        current = runtime.load_state(self.root, contracts, pdigest)
        self.raises('unread_context', runtime.ensure_reads, self.root, contracts, current, 'producer', 'worker', 'implementer')
        packet = runtime.context(self.root, context_id='worker', remember=True)
        self.assertIn('decision:theme.owner', packet['reused_sections'])
        self.assertNotIn('decision:theme.owner', packet['sections'])
        self.assertIn('state', packet['sections'])
        self.assertIn('contract', packet['sections'])
        tx(self.root, payload)
        self.assertEqual('complete', runtime.validate(self.root)['cursor'])
        fresh = runtime.context(self.root, 'producer', context_id='new-worker')
        self.assertIn('decision:theme.owner', fresh['sections'])

    def test_legacy_lookup_without_plan_or_state(self):
        add_decision(self.root, legacy=True)
        (self.root / 'state.json').unlink()
        (self.root / 'plan.md').unlink()
        result = runtime.decision_get(self.root, 'theme.owner')
        self.assertEqual('S', result['decision']['grade'])
        self.assertEqual('ok', runtime.context(self.root, section='decision:theme.owner')['status'])

    def test_history_growth_does_not_change_packet(self):
        index = add_decision(self.root, legacy=True)
        self.attach(index)
        packet = runtime.context(self.root, context_id='fixed')
        for amount in [352_338, 3_523_380]:
            with (self.root / 'decisions.md').open('a') as stream:
                stream.write('\nUnrelated historical narrative\n' + 'x' * amount)
            self.assertEqual(packet, runtime.context(self.root, context_id='fixed'))
        self.assertLess(len(runtime.encoded(packet)), runtime.LIMIT)

    def test_selected_source_change_invalidates_mapping(self):
        add_decision(self.root, legacy=True)
        path = self.root / 'decisions.md'
        path.write_text(path.read_text().replace('Original current constraint', 'Changed current constraint'))
        self.raises('source_changed', runtime.decision_get, self.root, 'theme.owner')

    def test_active_pointer_source_change_invalidates_approved_summary(self):
        add_decision(self.root, legacy=True)
        path = self.root / 'decisions.md'
        path.write_text(path.read_text().replace('D1 approved', 'D2 approved'))
        self.raises('source_changed', runtime.decision_get, self.root, 'theme.owner')

    def test_date_alone_is_ambiguous(self):
        index = add_decision(self.root, legacy=True)
        path = self.root / 'decisions.md'
        path.write_text(path.read_text() + '\n<!-- D1 -->another same-date decision<!-- /D1 -->')
        self.raises('ambiguous', runtime.decision_get, self.root, 'theme.owner')

    def test_missing_active_status_evidence_is_ambiguous(self):
        index = add_decision(self.root, legacy=True)
        del index['records'][0]['active_source']
        self.save_index(index)
        self.raises('ambiguous', runtime.decision_get, self.root, 'theme.owner')

    def test_unknown_duplicate_proposed_superseded_distinct(self):
        index = add_decision(self.root)
        self.raises('unknown', runtime.decision_get, self.root, 'theme.missing')
        index['active'].append(copy.deepcopy(index['active'][0])); self.save_index(index)
        self.raises('ambiguous', runtime.decision_get, self.root, 'theme.owner')
        index['active'].pop()
        for status in ['proposed', 'superseded']:
            index['records'][0]['status'] = status; self.save_index(index)
            self.raises(status, runtime.decision_get, self.root, 'theme.owner')

    def test_duplicate_record_and_missing_fields_fail(self):
        index = add_decision(self.root)
        index['records'].append(copy.deepcopy(index['records'][0])); self.save_index(index)
        self.raises('ambiguous', runtime.decision_get, self.root, 'theme.owner')
        index['records'].pop(); del index['records'][0]['constraints']; self.save_index(index)
        self.raises('invalid_schema', runtime.decision_get, self.root, 'theme.owner')

    def test_long_decision_requires_explicit_read(self):
        index = add_decision(self.root, constraints='한글제약' * 400, legacy=True)
        self.attach(index)
        result = runtime.decision_get(self.root, 'theme.owner')
        self.assertEqual('overflow', result['status'])
        packet = runtime.context(self.root, context_id='worker')
        self.assertIn('decision:theme.owner', packet['required_sections'])
        tx(self.root, {'op': 'read', 'receipts': packet['receipts']})
        payload = {'op': 'set', 'record': 'producer', 'status': 'implementing', 'context_id': 'worker', 'actor': None, 'workspace': str(self.root.parent.resolve()), 'target': ['src.py']}
        self.raises('unread_context', tx, self.root, payload)
        detail = runtime.context(self.root, 'producer', 'decision:theme.owner', 'worker')
        self.assertEqual(index['records'][0]['constraints'], detail['content']['constraints'])
        tx(self.root, {'op': 'read', 'receipts': detail['receipts']})
        tx(self.root, payload)

    def test_overflow_contract_reconstructs_without_dropping_unicode(self):
        records, _ = runtime.plan(self.root)
        records['producer']['goal'] = '필수😀조건' * 4000
        write_plan(self.root, list(records.values()))
        tx(self.root, {'op': 'reconcile', 'reason': 'large contract'})
        packet = runtime.context(self.root, context_id='worker')
        names = [n for n in packet['required_sections'] if n.startswith('contract@')]
        self.assertGreater(len(names), 1)
        fragments = []
        for name in names:
            result = runtime.context(self.root, 'producer', name, 'worker')
            self.assertLessEqual(len(runtime.encoded(result)), runtime.LIMIT)
            fragments.append(result['content']['json_fragment'])
        self.assertEqual(records['producer'], json.loads(''.join(fragments)))
        read_all(self.root)
        start(self.root)

    def test_g1_003_escaped_fragments_fit_actual_response_and_dispatch(self):
        records, _ = runtime.plan(self.root)
        records['producer']['goal'] = '\\' * 8000 + '\"\n\t' * 2000 + '한글😀'
        write_plan(self.root, list(records.values()))
        tx(self.root, {'op': 'reconcile', 'reason': 'G1-003 escaped required contract'})
        packet = runtime.context(self.root, context_id='worker')
        fragments = []
        for selector in packet['required_sections']:
            result = runtime.context(self.root, 'producer', selector, 'worker')
            self.assertLessEqual(len(runtime.encoded(result)), runtime.LIMIT)
            if selector.startswith('contract@'):
                fragments.append(result['content']['json_fragment'])
        self.assertEqual(records['producer'], json.loads(''.join(fragments)))
        read_all(self.root); start(self.root)

    def test_g1_003_decision_fragment_pages_preserve_escaped_constraint(self):
        text = '\\' * 8000 + '\n' * 2000
        add_decision(self.root, constraints=text)
        first = runtime.decision_get(self.root, 'theme.owner', 'record')
        fragments = [first['content']]
        for page in range(2, first['parts'] + 1):
            result = runtime.decision_get(self.root, 'theme.owner', 'record@' + str(page))
            self.assertLessEqual(len(runtime.encoded(result)), runtime.LIMIT)
            fragments.append(result['content'])
        self.assertEqual(text, json.loads(''.join(fragments))['constraints'])

    def test_g1_004_detail_namespace_covers_reserved_names_and_pagination(self):
        index = add_decision(self.root, legacy=True)
        bodies = {'record': 'Mandatory record detail\\' * 1000, 'sections': 'Mandatory sections detail\n' * 1000, 'normal': 'Mandatory normal detail'}
        for name, body in bodies.items():
            (self.root / (name + '.md')).write_text('<start>' + body + '<end>')
            index['records'][0]['required_sections'][name] = {'path': name + '.md', 'start': '<start>', 'end': '<end>', 'sha256': runtime.hashlib.sha256(body.encode()).hexdigest()}
        self.save_index(index)
        # Legacy planning has no state/plan alternative to decision-get.
        (self.root / 'state.json').unlink(); (self.root / 'plan.md').unlink()
        initial = runtime.decision_get(self.root, 'theme.owner')
        required = list(initial['required_sections']); next_section = initial.get('next_section')
        while next_section:
            result = runtime.decision_get(self.root, 'theme.owner', next_section)
            required.extend(result['required_sections']); next_section = result['next_section']
        for name, body in bodies.items():
            selector = 'detail:' + name
            self.assertIn(selector, required)
            first = runtime.decision_get(self.root, 'theme.owner', selector)
            self.assertEqual(selector, first['section'])
            if first['parts'] == 1:
                content = first['content']
            else:
                fragments = [first['content']]
                for number in range(2, first['parts'] + 1):
                    result = runtime.decision_get(self.root, 'theme.owner', first['section'] + '@' + str(number))
                    self.assertLessEqual(len(runtime.encoded(result)), runtime.LIMIT)
                    fragments.append(result['content'])
                content = json.loads(''.join(fragments))
            self.assertEqual(body, content['text'])
        metadata = runtime.decision_get(self.root, 'theme.owner', 'record')
        self.assertEqual('record', metadata['section'])
        # Unambiguous old aliases remain usable; returned selectors are canonical.
        self.assertEqual('detail:normal', runtime.decision_get(self.root, 'theme.owner', 'normal')['section'])
        self.assertEqual('detail:sections', runtime.decision_get(self.root, 'theme.owner', 'sections')['section'])

    def test_total_packet_overflow_routes_sections(self):
        records, _ = runtime.plan(self.root)
        regs = []
        for i in range(12):
            regs.append({'key': 'reg' + str(i), 'status': 'active', 'location': 'src.py', 'contract': 'x' * 1100, 'constraints': 'c', 'decisions': []})
        (self.root / 'registry.index.json').write_text(json.dumps({'schema': 1, 'entries': regs}))
        self.attach(registry_keys=[r['key'] for r in regs])
        packet = runtime.context(self.root, context_id='worker')
        self.assertEqual('overflow', packet['status'])
        self.assertNotIn('sections', packet)
        read_all(self.root)
        start(self.root)

    def test_required_detail_and_fresh_context_get_body_again(self):
        index = add_decision(self.root)
        text = '\nMandatory detail: preserve accessibility.\n'
        (self.root / 'detail.md').write_text('<start>' + text + '<end>')
        index['records'][0]['required_sections']['accessibility'] = {'path': 'detail.md', 'start': '<start>', 'end': '<end>', 'sha256': runtime.hashlib.sha256(text.encode()).hexdigest()}
        self.save_index(index); self.attach(index)
        read_all(self.root, context_id='old')
        packet = runtime.context(self.root, context_id='new')
        self.assertIn('decision:theme.owner', packet['sections'])
        self.assertIn('detail:theme.owner:accessibility', packet['required_sections'])
        payload = {'op': 'set', 'record': 'producer', 'status': 'implementing', 'context_id': 'new', 'actor': None, 'workspace': str(self.root.parent.resolve()), 'target': ['src.py']}
        self.raises('unread_context', tx, self.root, payload)
        read_all(self.root, context_id='new'); tx(self.root, payload)

    def test_source_change_invalidates_old_receipts(self):
        index = add_decision(self.root); self.attach(index)
        packet = runtime.context(self.root, context_id='worker')
        index['records'][0]['constraints'] = 'New constraint'
        self.save_index(index)
        self.raises('stale_receipt', tx, self.root, {'op': 'read', 'receipts': packet['receipts']})

    def test_plan_registry_handoff_deduplicates_and_ignores_history(self):
        index = add_decision(self.root)
        (self.root / 'registry.index.json').write_text(json.dumps({'schema': 1, 'entries': [{'key': 'theme', 'status': 'active', 'location': 'src.py', 'contract': 'Shared owner', 'constraints': 'Current constraint', 'decisions': ['theme.owner'], 'history': 'SECRET HISTORY' * 1000}]}))
        (self.root / 'HANDOFF.md').write_text('SECRET HISTORY' * 1000)
        self.attach(index, ['theme'])
        text = runtime.encoded(runtime.context(self.root, context_id='worker')).decode()
        self.assertEqual(1, text.count('"id":"D1"'))
        self.assertNotIn('SECRET HISTORY', text)

    def test_na_registry_no_git_or_agents_needed(self):
        self.attach(registry_keys=['ui'])
        packet = runtime.context(self.root)
        self.assertEqual('N/A', packet['sections']['registry:ui']['status'])
        start(self.root)
        self.assertIsNone(state(self.root)['records']['producer']['actor'])

    def test_verifier_does_not_receive_arbitrary_action_narrative(self):
        start(self.root)
        tx(self.root, {'op': 'checkpoint', 'record': 'producer', 'reason': 'boundary', 'next_action': 'IMPLEMENTER THINKS PERFECT'})
        packet = runtime.context(self.root, audience='verifier')
        self.assertNotIn('IMPLEMENTER THINKS PERFECT', runtime.encoded(packet).decode())

    def test_domain_candidates_are_bounded(self):
        index = add_decision(self.root)
        index['active'] = [{'key': 'theme.k' + str(i), 'id': 'D' + str(i)} for i in range(100)]
        self.save_index(index)
        result = runtime.decision_get(self.root, domain='theme')
        self.assertEqual(20, len(result['candidates']))
        self.assertTrue(result['more'])

    def test_many_sections_use_bounded_selector_pages(self):
        entries = [{'key': 'registry-' + str(i), 'status': 'active', 'location': 'src.py', 'contract': 'x' * 700, 'constraints': 'current', 'decisions': []} for i in range(90)]
        (self.root / 'registry.index.json').write_text(json.dumps({'schema': 1, 'entries': entries}))
        self.attach(registry_keys=[r['key'] for r in entries])
        packet = runtime.context(self.root, context_id='worker')
        self.assertEqual('overflow', packet['status'])
        self.assertEqual('sections@2', packet['next_section'])
        self.assertLessEqual(len(runtime.encoded(packet)), runtime.LIMIT)
        read_all(self.root); start(self.root)

    def test_oversized_identifier_is_explicit_schema_error(self):
        index = add_decision(self.root)
        index['active'][0]['key'] = 'theme.' + 'x' * 20000
        self.save_index(index)
        self.raises('invalid_schema', runtime.decision_get, self.root, domain='theme')

    def test_invalid_plan_missing_duplicate_dependency_gate(self):
        root = self.root
        records, _ = runtime.plan(root)
        base = records['producer']
        broken = copy.deepcopy(base); del broken['goal']
        write_plan(root, [broken]); self.raises('invalid_schema', runtime.plan, root)
        write_plan(root, [base, base]); self.raises('invalid_plan', runtime.plan, root)
        broken = copy.deepcopy(base); broken['requires'] = ['missing']
        write_plan(root, [broken]); self.raises('invalid_plan', runtime.plan, root)


if __name__ == '__main__':
    unittest.main()
