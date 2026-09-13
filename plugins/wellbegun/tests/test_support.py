"""Synthetic fixtures shared by runtime and independent lifecycle tests."""
import importlib.util
import json
from pathlib import Path
import shutil

PLUGIN = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wellbegun_artifacts', PLUGIN / 'scripts/artifacts.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def create_project(directory, basic_only=False):
    root = Path(directory).resolve() / '.wellbegun'
    root.mkdir(parents=True)
    for file in (PLUGIN / 'tests/fixtures').iterdir():
        shutil.copyfile(file, root / file.name)
    (root.parent / 'src.py').write_text('value = 1\n')
    (root.parent / 'check.py').write_text('assert True\n')
    if basic_only:
        records, _ = runtime.plan(root)
        write_plan(root, [records['producer']])
    runtime.transition(root, 0, json.loads((root / 'init.json').read_text()))
    return root


def write_plan(root, records):
    (root / 'plan.md').write_text('---\nstatus: approved\n---\n\n' + '\n\n'.join('<!-- wellbegun:contract ' + r['id'] + ' -->\n' + json.dumps(r, ensure_ascii=False) + '\n<!-- /wellbegun:contract -->' for r in records) + '\n')


def state(root):
    return json.loads((root / 'state.json').read_text())


def tx(root, payload):
    return runtime.transition(root, state(root)['revision'], payload)


def read_all(root, record='producer', context_id='worker', audience='implementer'):
    packet = runtime.context(root, record, context_id=context_id, audience=audience)
    receipts = list(packet.get('receipts', []))
    required = list(packet.get('required_sections', []))
    next_section = packet.get('next_section')
    while next_section:
        page = runtime.context(root, record, next_section, context_id, audience)
        required.extend(page['required_sections'])
        next_section = page.get('next_section')
    for section in required:
        receipts.extend(runtime.context(root, record, section, context_id, audience)['receipts'])
    tx(root, {'op': 'read', 'receipts': receipts})
    return packet


def start(root, record='producer', context_id='worker', audience='implementer'):
    read_all(root, record, context_id, audience)
    contracts, _ = runtime.plan(root)
    payload = {'op': 'set', 'record': record, 'status': 'implementing' if contracts[record]['kind'] == 'step' else 'checking', 'context_id': context_id, 'actor': None, 'workspace': str(root.parent.resolve()), 'target': ['src.py']}
    if contracts[record]['kind'] != 'step':
        payload['verifier_context_id'] = context_id
    return tx(root, payload)


def checking(root, record='producer', context_id='worker'):
    return tx(root, {'op': 'set', 'record': record, 'status': 'checking', 'context_id': context_id})


def success_payload(record='producer', context_id='worker', fresh=False):
    result = {'op': 'set', 'record': record, 'status': 'verified', 'context_id': context_id, 'checks': [{'command': 'python3 check.py', 'files': ['src.py', 'check.py'], 'exit_status': 0, 'environment': {'dependencies': 'stdlib'}, 'environment_known': True, 'external_state': False, 'covers': ['works']}]}
    if fresh:
        result['verdict'] = {'status': 'ACCEPT', 'independent': True, 'context_id': context_id}
    return result


def record_success(root, record='producer', context_id='worker', fresh=False):
    return tx(root, success_payload(record, context_id, fresh))


def add_decision(root, key='theme.owner', constraints='Use one owner.', legacy=False):
    original = '\nOriginal current constraint: ' + constraints + '\n'
    active = '\n' + key + ' -> D1 approved\n'
    (root / 'decisions.md').write_text('<!-- current -->' + active + '<!-- /current -->\n<!-- D1 -->' + original + '<!-- /D1 -->\n')
    ref = lambda start, end, text: {'path': 'decisions.md', 'start': start, 'end': end, 'sha256': runtime.hashlib.sha256(text.encode()).hexdigest()}
    item = {'key': key, 'id': 'D1', 'grade': 'S' if legacy else 'L', 'status': 'approved', 'choice': 'Shared owner', 'scope': 'theme', 'constraints': constraints, 'reason': 'Consistent appearance', 'source': ref('<!-- D1 -->', '<!-- /D1 -->', original), 'required_sections': {}}
    if legacy:
        item.update(legacy=True, active_source=ref('<!-- current -->', '<!-- /current -->', active))
    index = {'schema': 1, 'active': [{'key': key, 'id': 'D1'}], 'records': [item]}
    (root / 'decisions.index.json').write_text(json.dumps(index))
    return index
