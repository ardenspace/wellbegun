"""Execute skill examples and lifecycle through the real CLI, without Git.

Verifier identities here test the protocol, not actual agent defect detection.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_support import PLUGIN, write_plan


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wellbegun-lifecycle-')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve() / 'project with spaces'
        self.root = self.project / '.wellbegun'
        self.root.mkdir(parents=True)
        self.cwd = Path(self.temp.name) / 'unrelated cwd'
        self.cwd.mkdir()
        self.helper = PLUGIN / 'scripts/artifacts.py'
        for name in ('plan.md', 'decisions.index.json', 'registry.index.json'):
            shutil.copyfile(PLUGIN / 'tests/fixtures' / name, self.root / name)
        self.plan = (self.root / 'plan.md').read_text()
        self.records = [json.loads(text) for text in re.findall(
            r'<!-- wellbegun:contract [^>]+ -->\s*(.*?)\s*<!-- /wellbegun:contract -->',
            self.plan, re.S)]
        for record in self.records:
            record['registry'] = ['ui']
            record['decisions'] = ['theme.owner']
        write_plan(self.root, self.records)
        (self.project / 'src.py').write_text('value = 1\n')
        (self.project / 'check.py').write_text('from src import value\nassert value == 1\n')

    def state(self):
        return json.loads((self.root / 'state.json').read_text())

    def cli(self, command, *args, payload=None, code=0):
        proc = subprocess.run(['python3', str(self.helper), command, '--root',
                               str(self.root), *args], cwd=self.cwd, text=True,
                              input=json.dumps(payload) if payload is not None else None,
                              capture_output=True)
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def tx(self, payload, code=0):
        revision = self.state()['revision'] if (self.root / 'state.json').exists() else 0
        return self.cli('transition', '--expected-revision', str(revision),
                        '--input', '-', payload=payload, code=code)

    def example(self, path, needle, payload=None):
        """Run the exact documented shell block from an unrelated directory."""
        blocks = re.findall(r'```sh\n(.*?)```', (PLUGIN / path).read_text(), re.S)
        block = next(block for block in blocks if needle in block)
        env = dict(os.environ, wb_helper=str(self.helper), wb_root=str(self.root),
                   wb_context='writer', wb_revision=str(self.state()['revision'])
                   if (self.root / 'state.json').exists() else '0')
        proc = subprocess.run(['bash', '-c', block], cwd=self.cwd, env=env,
                              input=json.dumps(payload) if payload else None,
                              text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return [json.loads(line) for line in proc.stdout.splitlines()]

    def read(self, record, context='writer', audience='implementer'):
        packet = self.cli('context', '--record', record, '--context-id', context,
                          '--audience', audience, '--remember')
        required = list(packet.get('required_sections', []))
        selector = packet.get('next_section')
        while selector:
            page = self.cli('context', '--record', record, '--context-id', context,
                            '--audience', audience, '--remember', '--section', selector)
            required.extend(page['required_sections'])
            selector = page.get('next_section')
        for selector in required:
            self.cli('context', '--record', record, '--context-id', context,
                     '--audience', audience, '--remember', '--section', selector)
        return packet

    def start(self, record, context='writer', fresh=False):
        self.read(record, context, 'verifier' if fresh else 'implementer')
        payload = dict(op='set', record=record, status='checking' if fresh else 'implementing',
                       context_id=context, actor=None, workspace=str(self.project),
                       target=['src.py'])
        if fresh:
            payload['verifier_context_id'] = context
        return self.tx(payload)

    def test_cli_lifecycle_and_documented_examples(self):
        # Real shell examples: no state/plan-dependent lookup initialization.
        lookups = self.example('references/selected-inputs.md', 'decision-get')
        self.assertEqual(lookups[0]['decision']['id'], 'D1')
        self.assertFalse((self.root / 'state.json').exists())
        self.example('skills/wellrun/SKILL.md', '"op":"init"')
        packet = self.example('references/selected-inputs.md', 'context --root')[0]
        self.assertEqual(packet['record'], 'producer')
        self.assertEqual(packet['sections']['registry:ui'], {'key': 'ui', 'status': 'N/A', 'decisions': []})
        self.assertFalse((self.project / '.git').exists())
        self.start('producer')
        check = subprocess.run(['python3', 'check.py'], cwd=self.project, capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        facts = {'command': 'python3 check.py', 'files': ['src.py', 'check.py'],
                 'exit_status': check.returncode, 'environment': {'dependencies': 'stdlib'},
                 'environment_known': True, 'external_state': False, 'covers': ['works']}
        self.example('skills/wellrun/SKILL.md', '--expected-revision "$wb_revision"',
                     {'op': 'complete-basic', 'record': 'producer', 'checks': [facts]})
        evidence = self.state()['records']['producer']['current_result']
        reuse = {'reuse': [{'evidence': evidence, 'covers': ['works']}],
                 'environment': {'dependencies': 'stdlib'}}
        self.assertEqual(self.state()['records']['producer']['round'], 1)
        blocked = self.start_consumer_before_gate()
        self.assertEqual(blocked['code'], 'blocked')
        self.start('gate', 'independent-gate', fresh=True)
        self.tx(dict(op='set', record='gate', status='verified', context_id='independent-gate',
                     verdict={'status': 'ACCEPT', 'independent': True,
                              'context_id': 'independent-gate'}, **reuse))
        reused = self.read('consumer')
        self.assertIn('decision:theme.owner', reused['reused_sections'])
        self.start('consumer')
        self.tx({'op': 'checkpoint', 'record': 'consumer', 'reason': 'user interruption',
                 'next_action': 'finish the consumer boundary check'})
        pending = self.root / 'pending/choice.json'
        pending.parent.mkdir()
        question = {'question': 'Keep the approved shared owner?'}
        pending.write_text(json.dumps(question))
        self.tx({'op': 'set', 'record': 'consumer', 'status': 'stopped',
                 'reason': 'decision wait', 'pending': 'pending/choice.json'})
        self.tx({'op': 'archive'}, code=2)
        self.assertFalse((self.root / 'cycles/cycle-1').exists())
        pending.write_text(json.dumps(dict(question, answer='Yes', decision_key='theme.owner')))
        self.tx({'op': 'resolve-pending', 'record': 'consumer', 'decision_key': 'theme.owner'})
        self.assertFalse(pending.exists())
        self.assertEqual(self.state()['records']['consumer']['next_action'],
                         'finish the consumer boundary check')
        self.cli('render', '--handoff')
        (self.root / 'run.md').unlink()
        (self.root / 'HANDOFF.md').unlink()
        self.cli('render')
        self.assertTrue((self.root / 'HANDOFF.md').exists())
        resumed = self.read('consumer', 'resumed-writer')
        self.assertIn('decision:theme.owner', resumed['sections'])
        self.tx({'op': 'set', 'record': 'consumer', 'status': 'implementing',
                 'context_id': 'resumed-writer'})
        self.tx(dict(op='complete-basic', record='consumer', **reuse))
        self.assertEqual(self.cli('validate')['cursor'], 'complete')
        decisions_before = (self.root / 'decisions.index.json').read_bytes()
        self.example('skills/wellnext/SKILL.md', '"op":"archive"')
        archived = self.root / 'cycles/cycle-1'
        for name in ('state.json', 'plan.md', 'run.md', 'HANDOFF.md', 'evidence'):
            self.assertTrue((archived / name).exists(), name)
            self.assertFalse((self.root / name).exists(), name)
        self.assertEqual((self.root / 'decisions.index.json').read_bytes(), decisions_before)
        self.assertEqual(self.cli('decision-get', '--key', 'theme.owner')['decision']['id'], 'D1')
        next_record = dict(self.records[0], id='next-work', scope_id='scope-next',
                           goal='Next cycle only', decisions=[], registry=[])
        write_plan(self.root, [next_record])
        self.tx({'op': 'init', 'cycle': 'cycle-2', 'mode': 'companion'})
        current = self.read('next-work', 'cycle-two-writer')
        text = json.dumps(current)
        self.assertNotIn('scope-producer', text)
        self.assertNotIn('finish the consumer boundary check', text)
        self.assertNotIn('theme.owner', text)
        self.assertEqual(list(self.state()['records']), ['next-work'])

    def start_consumer_before_gate(self):
        self.read('consumer')
        return self.tx({'op': 'set', 'record': 'consumer', 'status': 'implementing',
                        'context_id': 'writer', 'actor': None,
                        'workspace': str(self.project), 'target': ['src.py']}, code=2)

    def test_legacy_lookup_preserves_execution_format(self):
        (self.root / 'plan.md').write_text('---\nstatus: approved\n---\nLegacy plan\n')
        (self.root / 'run.md').write_text('---\nmode: companion\n---\n[>] Existing step\n')
        (self.root / 'decisions.md').write_text('Legacy ledger remains untouched.\n')
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.assertEqual(self.cli('validate')['status'], 'legacy')
        self.example('references/selected-inputs.md', 'decision-get')
        result = self.cli('context', '--section', 'decision:theme.owner')
        self.assertEqual(result['decision']['id'], 'D1')
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}, before)
        self.assertFalse((self.root / 'state.json').exists())
        # A marker-form plan still must not partially initialize a legacy run.
        write_plan(self.root, self.records)
        rejected = self.tx({'op': 'init', 'cycle': 'cycle-2', 'mode': 'companion'}, code=2)
        self.assertEqual(rejected['code'], 'legacy')
        self.assertEqual((self.root / 'run.md').read_bytes(), before['run.md'])

    def test_plan_skill_marker_example_initializes(self):
        blocks = re.findall(r'```markdown\n(.*?)```',
                            (PLUGIN / 'skills/wellplan/SKILL.md').read_text(), re.S)
        marker = next(block for block in blocks if '<!-- wellbegun:contract' in block)
        (self.root / 'plan.md').write_text('---\nstatus: approved\n---\n' + marker)
        self.example('skills/wellrun/SKILL.md', '"op":"init"')
        packet = self.example('references/selected-inputs.md', 'context --root')[0]
        self.assertEqual(packet['record'], 'step-1.1')
        self.assertEqual(self.cli('validate')['schema'], 2)


if __name__ == '__main__':
    unittest.main()
