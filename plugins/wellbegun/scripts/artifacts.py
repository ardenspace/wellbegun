#!/usr/bin/env python3
"""Small, standard-library artifact runtime. See references/runtime-contract.md."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile
import uuid
from contextlib import contextmanager

LIMIT = 12 * 1024
DECISION_LIMIT = 1024
PAGE = 6000
STATUSES = {'queued', 'implementing', 'checking', 'fixing', 'stopped', 'verified'}
ACTIVE = {'implementing', 'checking', 'fixing'}


class Error(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.details = code, details


def need(condition, code, message, **details):
    if not condition:
        raise Error(code, message, **details)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise Error('invalid_artifact', f'Cannot read {path.name}: {exc}') from exc


def fields(value, names, label):
    need(isinstance(value, dict), 'invalid_schema', f'{label} must be an object')
    need(all(k in value for k in names), 'invalid_schema', f'{label} requires {", ".join(names)}')


def strings(value, label, empty=True):
    need(isinstance(value, list) and all(isinstance(x, str) and x for x in value),
         'invalid_schema', f'{label} must be a string list')
    need(empty or bool(value), 'invalid_schema', f'{label} must not be empty')
    need(len(set(value)) == len(value), 'invalid_schema', f'{label} contains duplicates')


def identifier(value, label='identifier'):
    need(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', value), 'invalid_schema', f'{label} must be 1–120 ASCII letters, digits, dots, underscores or hyphens')


def selector_page(names, selector=None, count=24):
    try:
        page = int(selector.split('@')[1]) if selector else 1
    except (IndexError, ValueError) as exc:
        raise Error('unknown_section', 'Invalid selector-list page') from exc
    need(page > 0 and (page - 1) * count < len(names), 'unknown_section', 'Selector-list page does not exist')
    selected = names[(page - 1) * count:page * count]
    return {'required_sections': selected, 'next_section': f'sections@{page + 1}' if page * count < len(names) else None}


def inside(base, name, boundary=None):
    need(isinstance(name, str) and bool(name), 'invalid_path', 'A relative path is required')
    path = (base / name).resolve()
    need(not Path(name).is_absolute() and path.is_relative_to((boundary or base).resolve()),
         'invalid_path', f'Path escapes permitted root: {name}')
    return path


def plan(root):
    try:
        text = (root / 'plan.md').read_text(encoding='utf-8')
    except OSError as exc:
        raise Error('invalid_plan', str(exc)) from exc
    need(re.match(r'\A---\s*\n(?:(?!\n---).)*\bstatus:\s*approved\b(?:(?!\n---).)*\n---', text, re.S), 'unapproved_plan', 'Runtime requires an approved plan')
    pattern = r'<!-- wellbegun:contract ([\w.-]+) -->\s*(.*?)\s*<!-- /wellbegun:contract -->'
    matches = re.findall(pattern, text, re.S)
    need(matches and text.count('<!-- wellbegun:contract ') == len(matches), 'invalid_plan', 'Missing or malformed contract markers')
    records = {}
    for key, body in matches:
        try:
            rec = json.loads(body)
        except ValueError as exc:
            raise Error('invalid_plan', f'{key}: invalid contract JSON') from exc
        fields(rec, ['id', 'kind', 'scope_id', 'goal', 'completion', 'verification', 'decisions', 'registry', 'discretion', 'requires', 'grade'], key)
        identifier(rec['id']); identifier(rec['scope_id'])
        need(key == rec['id'] and key not in records, 'invalid_plan', 'Duplicate or mismatched contract ID')
        need(rec['kind'] in {'step', 'gate', 'phase', 'whole-run'} and rec['grade'] in {'basic', 'fresh'}, 'invalid_plan', 'Invalid kind or grade')
        need(rec['kind'] == 'step' or rec['grade'] == 'fresh', 'invalid_plan', 'Gates and integration require fresh verification')
        for name in ['scope_id', 'goal', 'discretion']:
            need(isinstance(rec[name], str) and rec[name], 'invalid_plan', f'{key}: {name} must be nonempty')
        for name in ['verification', 'decisions', 'registry', 'requires']:
            strings(rec[name], name, empty=name != 'verification')
            if name != 'verification':
                for value in rec[name]:
                    identifier(value)
        need(isinstance(rec['completion'], list) and rec['completion'], 'invalid_plan', 'Completion clauses are required')
        for clause in rec['completion']:
            fields(clause, ['id', 'text'], 'completion clause')
            need(all(isinstance(clause[n], str) and clause[n] for n in ['id', 'text']), 'invalid_plan', 'Invalid completion clause')
        need(len({c['id'] for c in rec['completion']}) == len(rec['completion']), 'invalid_plan', 'Duplicate clause ID')
        records[key] = rec
    need(len({r['scope_id'] for r in records.values()}) == len(records), 'invalid_plan', 'Duplicate scope_id')
    positions = {key: i for i, key in enumerate(records)}
    for key, rec in records.items():
        need(all(dep in records for dep in rec['requires']), 'invalid_plan', f'{key}: missing dependency')
        need(all(positions[dep] < positions[key] for dep in rec['requires']), 'invalid_plan', f'{key}: dependency cycle or order violation')
    def ancestors(key):
        result = set(records[key]['requires'])
        for dep in records[key]['requires']:
            result |= ancestors(dep)
        return result
    for key, rec in records.items():
        if rec['kind'] != 'gate':
            continue
        fields(rec, ['producers', 'consumers'], key)
        strings(rec['producers'], 'producers', False)
        strings(rec['consumers'], 'consumers', False)
        need(all(p in records and p in ancestors(key) for p in rec['producers']), 'invalid_plan', 'Gate must depend on producers')
        need(all(c in records and key in ancestors(c) for c in rec['consumers']), 'invalid_plan', 'Consumer bypasses gate')
        for consumer, other in records.items():
            if consumer == key or consumer in rec['producers']:
                continue
            if any(p in ancestors(consumer) for p in rec['producers']):
                need(key in ancestors(consumer), 'invalid_plan', f'{consumer}: transitive gate bypass')
    return records, digest(records)


def source(root, ref):
    fields(ref, ['path', 'start', 'end', 'sha256'], 'source reference')
    path = inside(root, ref['path'], root.parent)
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        raise Error('source_changed', f'Missing source {ref["path"]}') from exc
    need(isinstance(ref['start'], str) and ref['start'] and isinstance(ref['end'], str) and ref['end'], 'invalid_schema', 'Source delimiters must be nonempty')
    need(text.count(ref['start']) == 1 and text.count(ref['end']) == 1, 'ambiguous', 'Source delimiters must select exactly one range', source=ref['path'])
    start = text.index(ref['start']) + len(ref['start'])
    end = text.index(ref['end'])
    need(end >= start, 'ambiguous', 'Source delimiters are reversed')
    selected = text[start:end]
    need(hashlib.sha256(selected.encode()).hexdigest() == ref['sha256'], 'source_changed', 'Selected source changed; review mapping again', source=ref['path'])
    return selected


def decision(root, key):
    identifier(key, 'decision key')
    index = read_json(root / 'decisions.index.json')
    fields(index, ['schema', 'active', 'records'], 'decision index')
    need(index['schema'] == 1 and isinstance(index['active'], list) and isinstance(index['records'], list), 'invalid_schema', 'Invalid decision index')
    for pointer in index['active']:
        fields(pointer, ['key', 'id'], 'active pointer')
        identifier(pointer['key']); identifier(pointer['id'])
    pointers = [p for p in index['active'] if p['key'] == key]
    candidates = [{'key': p['key'], 'id': p['id']} for p in index['active'] if p['key'].split('.')[0] == key.split('.')[0]][:20]
    need(pointers, 'unknown', 'No active pointer for requested key', candidates=candidates)
    need(len(pointers) == 1, 'ambiguous', 'Duplicate active pointer', candidates=pointers[:20])
    found = [r for r in index['records'] if isinstance(r, dict) and r.get('id') == pointers[0]['id']]
    need(len(found) == 1, 'ambiguous', 'Active ID must select exactly one record')
    rec = found[0]
    fields(rec, ['id', 'key', 'grade', 'status', 'choice', 'scope', 'constraints', 'reason', 'source', 'required_sections'], 'decision record')
    need(rec['key'] == key, 'ambiguous', 'Active key and record key disagree')
    need(rec['status'] == 'approved', rec['status'] if rec['status'] in {'proposed', 'superseded'} else 'ambiguous', 'Decision is not approved and active')
    need(rec['grade'] in {'S', 'M', 'L', 'XL'}, 'invalid_schema', 'Invalid decision grade')
    for name in ['choice', 'scope', 'constraints', 'reason']:
        need(isinstance(rec[name], str), 'invalid_schema', f'Decision {name} must be text')
    need(isinstance(rec['required_sections'], dict), 'invalid_schema', 'required_sections must map names to source references')
    for name in rec['required_sections']:
        identifier(name, 'detail name')
    if rec['source'] is not None:
        source(root, rec['source'])
    if rec.get('legacy'):
        need(rec.get('source') and rec.get('active_source'), 'ambiguous', 'Legacy mapping needs original and current active-pointer evidence')
        source(root, rec['active_source'])
    for ref in rec['required_sections'].values():
        source(root, ref)
    return rec


def registry(root, key):
    identifier(key, 'registry key')
    index = read_json(root / 'registry.index.json')
    fields(index, ['schema', 'entries'], 'registry index')
    need(index['schema'] == 1 and isinstance(index['entries'], list), 'invalid_schema', 'Invalid registry index')
    found = [r for r in index['entries'] if isinstance(r, dict) and r.get('key') == key]
    need(len(found) == 1, 'ambiguous' if found else 'unknown', 'Registry key must select one entry')
    rec = found[0]
    fields(rec, ['key', 'status'], 'registry entry')
    need(rec['status'] in {'active', 'N/A'}, 'invalid_schema', 'Invalid registry status')
    if rec['status'] == 'N/A':
        return {'key': key, 'status': 'N/A', 'decisions': []}
    fields(rec, ['location', 'contract', 'constraints', 'decisions'], 'active registry')
    strings(rec['decisions'], 'registry decisions')
    if rec.get('source'):
        source(root, rec['source'])
    result = {k: rec[k] for k in ['key', 'status', 'location', 'contract', 'constraints', 'decisions']}
    if rec.get('source'):
        result['source'] = rec['source']
    return result


def snapshot(root, paths):
    strings(paths, 'target/input files', False)
    return {p: file_digest(inside(root.parent, p)) for p in paths}


def valid_snapshot(root, snap):
    need(isinstance(snap, dict) and bool(snap), 'invalid_schema', 'Content snapshot must not be empty')
    return snapshot(root, list(snap)) == snap


def runtime_environment():
    return {'python': platform.python_version(), 'platform': platform.platform()}


def reusable_check(root, check):
    """A current successful command fact; foundation acceptance has separate rules."""
    return (check['exit_status'] == 0 and check['environment_known']
            and not check['external_state'] and check['runtime'] == runtime_environment()
            and valid_snapshot(root, check['inputs']))


def load_evidence(root, pointer):
    need(isinstance(pointer, str) and re.fullmatch(r'[a-f0-9]{64}', pointer), 'invalid_evidence', 'Invalid evidence ID')
    value = read_json(root / 'evidence' / (pointer + '.json'))
    need(digest(value) == pointer, 'invalid_evidence', 'Evidence digest mismatch')
    fields(value, ['kind'], 'evidence')
    if value['kind'] == 'result':
        fields(value, ['record', 'scope_id', 'contract_digest', 'input_digest', 'target', 'round', 'checks', 'verdict', 'finding_ids'], 'result evidence')
        need(isinstance(value['checks'], list), 'invalid_evidence', 'Checks must be a list')
        for check in value['checks']:
            fields(check, ['command', 'exit_status', 'environment', 'environment_known', 'external_state', 'covers', 'inputs', 'runtime'], 'check evidence')
            need(isinstance(check['inputs'], dict) and check['inputs'] and isinstance(check['environment'], dict) and check['environment'], 'invalid_evidence', 'Check needs input/environment identity')
            need(type(check['exit_status']) is int and type(check['environment_known']) is bool and type(check['external_state']) is bool, 'invalid_evidence', 'Invalid check status or flags')
            strings(check['covers'], 'evidence covers')
            need(all(v is None or isinstance(v, str) and re.fullmatch(r'[a-f0-9]{64}', v) for v in check['inputs'].values()), 'invalid_evidence', 'Invalid input content fingerprint')
    return value


def cursor(state, records):
    active = [k for k, r in state['records'].items() if r['status'] in ACTIVE]
    need(len(active) <= 1, 'invalid_state', 'At most one active record is allowed')
    if active:
        return active[0]
    if any(r['pending'] is not None for r in state['records'].values()):
        return 'blocked'
    for key, rec in records.items():
        current = state['records'][key]
        runnable = current['status'] == 'queued' or current['status'] == 'stopped' and current['stop_reason'] == 'recheck_required'
        if runnable and all(state['records'][d]['status'] == 'verified' for d in rec['requires']):
            return key
    if all(r['status'] == 'verified' for r in state['records'].values()) and not any(f['status'] == 'unresolved' for f in state['findings'].values()):
        return 'complete'
    return 'blocked'


def validate_state(root, state, records, pdigest, drift=False):
    fields(state, ['schema', 'cycle', 'revision', 'plan_digest', 'mode', 'cursor', 'records', 'scopes', 'findings', 'reads', 'events', 'handoff_requested'], 'state')
    need(type(state['handoff_requested']) is bool, 'invalid_state', 'handoff_requested must be boolean')
    need(state['schema'] == 2 and type(state['revision']) is int and state['revision'] >= 1, 'invalid_state', 'Invalid state schema/revision')
    need(isinstance(state['records'], dict) and isinstance(state['scopes'], dict) and isinstance(state['findings'], dict) and isinstance(state['reads'], dict) and isinstance(state['events'], list), 'invalid_state', 'Invalid state collections')
    need(drift or state['plan_digest'] == pdigest, 'plan_drift', 'Plan changed; reconcile before dispatch')
    need(drift or set(state['records']) == set(records), 'invalid_state', 'State and plan record IDs disagree')
    for key, rec in state['records'].items():
        fields(rec, ['status', 'scope_id', 'contract_digest', 'input_digest', 'target', 'actor', 'workspace', 'context_id', 'implementer_contexts', 'round', 'finding_ids', 'next_action', 'stop_reason', 'resume_status', 'pending', 'evidence', 'current_result', 'verifier_contexts', 'current_verifier', 'round_inflight'], f'state record {key}')
        need(rec['status'] in STATUSES and rec['scope_id'] in state['scopes'], 'invalid_state', 'Invalid record status/scope')
        need(type(rec['round']) is int and rec['round'] >= 0, 'invalid_state', 'Invalid round')
        need(isinstance(rec['evidence'], list) and isinstance(rec['finding_ids'], list), 'invalid_state', 'Invalid result pointers')
        need(isinstance(rec['verifier_contexts'], list) and type(rec['round_inflight']) is bool, 'invalid_state', 'Invalid verifier/round fields')
        strings(rec['implementer_contexts'], 'implementer contexts')
        need(rec['scope_id'] in state['scopes'] and rec['round'] == state['scopes'][rec['scope_id']]['round'], 'invalid_state', 'Record/scope round mismatch')
        if not drift:
            need(rec['scope_id'] == records[key]['scope_id'] and rec['contract_digest'] == digest(records[key]), 'invalid_state', 'Record contract identity differs')
        if rec['status'] != 'queued':
            need(isinstance(rec['target'], dict) and rec['target'] and any(v is not None for v in rec['target'].values()), 'invalid_state', 'Started record needs content target')
            need(rec['workspace'] == str(root.parent.resolve()) and isinstance(rec['context_id'], str) and rec['context_id'], 'invalid_state', 'Invalid execution identity')
            need(isinstance(rec['input_digest'], str) and re.fullmatch(r'[a-f0-9]{64}', rec['input_digest']), 'invalid_state', 'Started record needs selected input identity')
            if not drift and records[key]['kind'] == 'step':
                need(rec['context_id'] in rec['implementer_contexts'], 'invalid_state', 'Current implementer identity is not tracked')
        if rec['status'] == 'stopped':
            need(rec['resume_status'] in ACTIVE and rec['stop_reason'], 'invalid_state', 'Stopped record needs resume state and reason')
        if rec['pending'] is not None:
            need(rec['status'] == 'stopped', 'invalid_state', 'A pending question must remain a stopped blocker')
        if rec['current_result'] is not None:
            need(rec['current_result'] in rec['evidence'], 'invalid_state', 'Current result is not referenced')
        if rec['status'] == 'verified':
            need(rec['current_result'] is not None and not rec['round_inflight'] and rec['round'] > 0, 'invalid_state', 'Verified record lacks completed result')
            result = load_evidence(root, rec['current_result'])
            need(result.get('kind') == 'result' and result.get('scope_id') == rec['scope_id'] and result.get('contract_digest') == rec['contract_digest'] and result.get('input_digest') == rec['input_digest'] and result.get('target') == rec['target'] and result.get('round') == rec['round'], 'invalid_evidence', 'Verified evidence does not identify current contract/inputs/target/round')
            checks = result.get('checks', [])
            need(checks and all(c.get('exit_status') == 0 for c in checks), 'invalid_evidence', 'Verified record lacks successful checks')
            if not drift:
                contract = records[key]
                need(set(contract['verification']) <= {c['command'] for c in checks} and {c['id'] for c in contract['completion']} <= {clause for c in checks for clause in c['covers']}, 'invalid_evidence', 'Verified result does not cover contract')
                need(all(state['records'][d]['status'] == 'verified' for d in contract['requires']), 'invalid_state', 'Verified prerequisite is not verified')
                if contract['grade'] == 'fresh':
                    verdict = result.get('verdict') or {}
                    need(verdict.get('status') == 'ACCEPT' and verdict.get('independent') is True and verdict.get('context_id') == rec['current_verifier'], 'invalid_evidence', 'Fresh result lacks current independent ACCEPT')
                    independent(records, state, key, rec['current_verifier'])
            need(not any(f.get('scope_id') == rec['scope_id'] and f.get('status') == 'unresolved' for f in state['findings'].values()), 'invalid_state', 'Verified record has unresolved finding')
    for scope in state['scopes'].values():
        fields(scope, ['round', 'limit'], 'scope')
        need(type(scope['round']) is int and type(scope['limit']) is int and 0 <= scope['round'] <= scope['limit'], 'invalid_state', 'Invalid scope rounds')
    for finding in state['findings'].values():
        fields(finding, ['id', 'scope_id', 'clause', 'reproduction', 'status', 'round'], 'finding')
        need(finding['status'] in {'unresolved', 'resolved', 'excluded'}, 'invalid_state', 'Invalid finding disposition')
        identifier(finding['id'], 'finding ID')
    if not drift:
        need(state['cursor'] == cursor(state, records), 'invalid_state', 'Cursor disagrees with records')
        if state['cursor'] == 'complete':
            no_pending_dispatch(root, state)
            changed = drifted(root, state, records)
            need(not changed, 'code_drift', 'Completion cannot retain invalid input/evidence success', records=changed)
    return state


def load_state(root, records, pdigest, drift=False):
    return validate_state(root, read_json(root / 'state.json'), records, pdigest, drift)


def independent(records, state, key, cid, current_target=False):
    covered = set()
    def visit(record):
        if record in covered:
            return
        covered.add(record)
        for dep in records[record]['requires']:
            visit(dep)
    visit(key)
    implementers = {cid for k in covered for cid in state['records'][k]['implementer_contexts']}
    if current_target:
        paths = set(state['records'][key]['target'] or {})
        implementers |= {writer for rec in state['records'].values()
                         if paths.intersection(rec['target'] or {})
                         for writer in rec['implementer_contexts']}
    need(cid and cid not in implementers, 'not_independent', 'Verifier context implemented this scope, a prerequisite, or the current shared target')


def check_pending(root, rec):
    if rec['pending'] is None:
        return
    pending = rec['pending']
    fields(pending, ['path', 'sha256'], 'pending pointer')
    path = inside(root, pending['path'])
    need(path.is_relative_to(root / 'pending'), 'invalid_path', 'Question must be under pending/')
    need(path.exists(), 'pending_mismatch', 'Pending question missing; reconcile answer and decision')
    if file_digest(path) != pending['sha256']:
        raise Error('pending_mismatch', 'Mailbox changed; resolve-pending must record actual answer and decision')


def drifted(root, state, records=None, only=None):
    if records is None:
        records, _ = plan(root)
    changed = []
    for key, rec in state['records'].items():
        if only is not None and key not in only:
            continue
        if rec['input_digest'] and key in records and rec['input_digest'] != digest(selected_sections(root, records[key])):
            changed.append(key)
        if rec['target'] and not valid_snapshot(root, rec['target']):
            changed.append(key)
        if rec['status'] == 'verified':
            for pointer in [rec['current_result']] if rec['current_result'] else []:
                evidence = load_evidence(root, pointer)
                for check in evidence.get('checks', []):
                    if check['runtime'] != runtime_environment():
                        changed.append(key)
                    if not valid_snapshot(root, check['inputs']):
                        changed_files = {p for p, h in check['inputs'].items() if file_digest(inside(root.parent, p)) != h}
                        owned = set()
                        for consumer, active in state['records'].items():
                            if active['status'] in ACTIVE | {'verified', 'stopped'} and depends_on(records, consumer, key):
                                owned.update(active['target'] or {})
                        # Stopping preserves declared ownership; target drift and pending
                        # dispatch checks remain independent blockers.
                        # Broad regression facts become stale; expected downstream edits
                        # do not revoke an unchanged foundation contract.
                        if not changed_files <= owned:
                            changed.append(key)
    return sorted(set(changed))


def depends_on(records, consumer, producer):
    return any(dep == producer or depends_on(records, dep, producer) for dep in records[consumer]['requires'])


def current_prerequisites(root, records, state, key):
    """Status labels alone cannot authorize consuming an earlier result."""
    required = set()
    def visit(record):
        for dep in records[record]['requires']:
            if dep not in required:
                required.add(dep)
                visit(dep)
    visit(key)
    need(all(state['records'][dep]['status'] == 'verified' for dep in required), 'blocked', 'Predecessor/gate is not verified')
    changed = drifted(root, state, records, required)
    need(not changed, 'code_drift', 'Predecessor/gate inputs changed; reconcile before checking or completion', records=changed)


def mailbox_files(root):
    directory = root / 'pending'
    return [str(path.relative_to(root)) for path in directory.rglob('*') if path.is_file()] if directory.exists() else []


def check_mailbox(root, state):
    referenced = {rec['pending']['path'] for rec in state['records'].values() if rec['pending'] is not None}
    unreferenced = sorted(set(mailbox_files(root)) - referenced)
    need(not unreferenced, 'pending_mismatch', 'Unreferenced mailbox files require answer/evidence reconciliation', files=unreferenced[:20])


def no_pending_dispatch(root, state):
    pending = [key for key, rec in state['records'].items() if rec['pending'] is not None]
    need(not pending and not mailbox_files(root), 'pending_mismatch', 'Resolve actual pending answers and record their decisions before dispatch/completion', records=pending)


def sections(root, records, state, key, audience):
    need(key in records, 'unknown', 'Unknown record')
    rec, current = records[key], state['records'][key]
    check_pending(root, current)
    result = {'contract': rec}
    # Structured facts only: no implementer reports or previous verdict narratives.
    state_fields = ['status', 'target', 'actor', 'workspace', 'round', 'resume_status']
    if audience == 'implementer':
        state_fields += ['next_action', 'stop_reason']
    result['state'] = {k: current[k] for k in state_fields}
    result['state']['revision'] = state['revision']
    result['state']['mode'] = state['mode']
    result['state']['blockers'] = [k for k, r in state['records'].items() if r['status'] == 'stopped']
    result['state']['findings'] = [{k: f[k] for k in ['id', 'clause', 'reproduction', 'status', 'round']} for f in state['findings'].values() if f['scope_id'] == rec['scope_id'] and f['status'] == 'unresolved']
    summaries = []
    for pointer in [current['current_result']] if current['current_result'] else []:
        evidence = load_evidence(root, pointer)
        for check in evidence.get('checks', []):
            summaries.append({'evidence': pointer, 'command': check['command'], 'exit_status': check['exit_status'], 'inputs': check['inputs'], 'environment': check['environment'], 'reusable': reusable_check(root, check)})
    result['state']['checks'] = summaries
    result.update(selected_sections(root, rec))
    return result


def selected_sections(root, rec):
    """Current required contract inputs, independent of execution state/history."""
    result = {}
    keys = list(rec['decisions'])
    for regkey in rec['registry']:
        item = registry(root, regkey)
        result['registry:' + regkey] = item
        keys.extend(item['decisions'])
    ids = set()
    for deckey in dict.fromkeys(keys):
        item = decision(root, deckey)
        if item['id'] in ids:
            continue
        ids.add(item['id'])
        result['decision:' + deckey] = {k: item[k] for k in ['key', 'id', 'grade', 'status', 'choice', 'scope', 'constraints', 'reason', 'source']}
        if item.get('active_source'):
            result['decision:' + deckey]['active_source'] = item['active_source']
        for name, ref in item['required_sections'].items():
            result['detail:' + deckey + ':' + name] = {'source': ref, 'text': source(root, ref)}
    return result


def pages(value):
    # Budget each character *after* fragment escaping in the outer response JSON.
    # PAGE leaves room for section names, receipt and response metadata under LIMIT.
    text = encoded(value).decode('utf-8')
    chunks, current, size, costs = [], [], 0, {}
    for char in text:
        if char not in costs:
            costs[char] = len(encoded(char)) - 2
        length = costs[char]
        if size + length > PAGE:
            chunks.append(''.join(current)); current, size = [], 0
        current.append(char); size += length
    chunks.append(''.join(current))
    return chunks


def section_map(root, records, state, key, audience):
    raw = sections(root, records, state, key, audience)
    result = {}
    for name, value in raw.items():
        chunks = pages(value)
        if len(chunks) == 1:
            result[name] = value
        else:
            for i, chunk in enumerate(chunks, 1):
                result[f'{name}@{i}'] = {'part': i, 'parts': len(chunks), 'json_fragment': chunk}
    return result


def receipt(state, key, cid, audience, name, value):
    return {'context_id': cid, 'audience': audience, 'record': key, 'section': name, 'digest': digest(value), 'plan_digest': state['plan_digest']}


def context(root, record=None, section=None, context_id=None, audience='implementer', remember=False, _locked=False):
    root = Path(root).resolve()
    if remember and not _locked:
        with writer_lock(root):
            return context(root, record, section, context_id, audience, True, True)
    need(not (root / '.archive.json').exists(), 'archive_in_progress', 'Resume the recorded archive before dispatch or initialization')
    if not (root / 'state.json').exists():
        need(section and section.startswith('decision:'), 'legacy', 'Legacy cycle: retain existing state; use decision-get or context --section decision:<key>')
        return decision_get(root, section[len('decision:'):])
    records, pdigest = plan(root)
    state = load_state(root, records, pdigest)
    check_mailbox(root, state)
    for current in state['records'].values():
        check_pending(root, current)
    changed = drifted(root, state)
    need(not changed, 'code_drift', 'Target or check inputs changed; reconcile/checkpoint before dispatch', records=changed)
    key = record or state['cursor']
    if key in {'complete', 'blocked'}:
        return {'status': key, 'revision': state['revision'], 'blockers': [k for k, r in state['records'].items() if r['status'] == 'stopped']}
    cid = context_id or uuid.uuid4().hex
    identifier(cid, 'context ID')
    parts = section_map(root, records, state, key, audience)
    reused = {name: digest(value) for name, value in parts.items()
              if name.startswith(('decision:', 'registry:', 'detail:')) and known_read(state, cid, audience, name, value)}
    if not section:
        parts = {name: value for name, value in parts.items() if name not in reused}
    if section and section.startswith('sections@'):
        return {'status': 'overflow', 'record': key, 'context_id': cid, 'audience': audience, 'revision': state['revision'], **selector_page(list(parts), section)}
    need(section is None or section in parts, 'unknown_section', 'Unknown section', sections=list(parts))
    base = {'status': 'ok', 'record': key, 'context_id': cid, 'audience': audience, 'revision': state['revision'], 'reused_sections': {} if section else reused}
    if section:
        base.update(section=section, content=parts[section], receipts=[receipt(state, key, cid, audience, section, parts[section])])
    else:
        required = [n for n, v in parts.items() if n.startswith('detail:') or '@' in n or (n.startswith('decision:') and len(encoded(v)) > DECISION_LIMIT)]
        selected = {n: v for n, v in parts.items() if n not in required}
        base.update(sections=selected, required_sections=required, receipts=[receipt(state, key, cid, audience, n, v) for n, v in selected.items()])
        if len(encoded(base)) > LIMIT:
            return {**{k: v for k, v in base.items() if k not in {'sections', 'receipts', 'required_sections', 'reused_sections'}}, 'status': 'overflow', 'cursor': key, **selector_page(list(parts)), 'next': 'context --record <id> --context-id <same-id> --section <section>'}
    need(len(encoded(base)) <= LIMIT, 'overflow', 'Section metadata exceeds packet budget')
    if remember:
        saved = state['reads'].setdefault(cid, {})
        for token in base['receipts']:
            saved[key + '/' + token['section']] = token
        state['revision'] += 1
        validate_state(root, state, records, pdigest)
        atomic_json(root / 'state.json', state)
        base['revision'] = state['revision']
        base.pop('receipts')
        base['remembered'] = True
    return base


def decision_get(root, key=None, section=None, domain=None):
    root = Path(root).resolve()
    if domain is not None:
        identifier(domain, 'domain')
        index = read_json(root / 'decisions.index.json')
        for pointer in index['active']:
            fields(pointer, ['key', 'id'], 'active pointer')
            identifier(pointer['key']); identifier(pointer['id'])
        candidates = [p for p in index['active'] if p['key'].split('.')[0] == domain]
        return {'status': 'candidates', 'candidates': candidates[:20], 'more': len(candidates) > 20}
    need(key, 'invalid_input', 'decision-get needs --key or --domain')
    item = decision(root, key)
    detail_selectors = ['detail:' + name for name in item['required_sections']]
    if section and section.startswith('sections@'):
        return {'status': 'overflow', 'key': key, **selector_page(['record'] + detail_selectors, section, 3)}
    if section:
        name, _, page = section.partition('@')
        if name == 'record':
            value = item
            output_section = 'record'
        else:
            if name.startswith('detail:'):
                name = name[len('detail:'):]
            need(name in item['required_sections'], 'unknown_section', 'Unknown decision detail')
            ref = item['required_sections'][name]
            value = {'source': ref, 'text': source(root, ref)}
            output_section = 'detail:' + name
        chunks = pages(value)
        try:
            pos = int(page or '1') - 1
        except ValueError as exc:
            raise Error('unknown_section', 'Invalid page') from exc
        need(0 <= pos < len(chunks), 'unknown_section', 'Invalid page')
        return {'status': 'ok', 'key': key, 'section': output_section, 'part': pos + 1, 'parts': len(chunks), 'content': value if len(chunks) == 1 else chunks[pos]}
    small = {k: item[k] for k in ['key', 'id', 'grade', 'status', 'choice', 'scope', 'constraints', 'reason', 'source']}
    result = {'status': 'ok', 'decision': small, 'required_sections': detail_selectors}
    if len(encoded(result)) > DECISION_LIMIT:
        return {'status': 'overflow', 'key': key, 'id': item['id'], **selector_page(['record'] + detail_selectors, count=3), 'next': 'decision-get --key <key> --section record[@N]'}
    return result


@contextmanager
def writer_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / '.state.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise Error('locked', 'Writer lock exists; diagnose interrupted writer before removing lock') from exc
    try:
        os.write(fd, str(os.getpid()).encode()); os.fsync(fd); os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_evidence(root, evidence):
    pointer = digest(evidence)
    directory = root / 'evidence'
    directory.mkdir(exist_ok=True)
    path = directory / (pointer + '.json')
    try:
        with path.open('xb') as stream:
            stream.write(encoded(evidence) + b'\n'); stream.flush(); os.fsync(stream.fileno())
    except FileExistsError:
        load_evidence(root, pointer)
    return pointer


def new_record(rec):
    return {'status': 'queued', 'scope_id': rec['scope_id'], 'contract_digest': digest(rec), 'input_digest': None,
            'target': None, 'actor': None, 'workspace': None, 'context_id': None, 'implementer_contexts': [], 'round': 0,
            'finding_ids': [], 'next_action': 'start', 'stop_reason': None, 'resume_status': None,
            'pending': None, 'evidence': [], 'current_result': None, 'verifier_contexts': [], 'current_verifier': None, 'round_inflight': False}


def known_read(state, cid, audience, name, value):
    return any(token.get('context_id') == cid and token.get('audience') == audience
               and token.get('plan_digest') == state['plan_digest']
               and token.get('section') == name and token.get('digest') == digest(value)
               for token in state['reads'].get(cid, {}).values())


def ensure_reads(root, records, state, key, cid, audience):
    need(isinstance(cid, str) and cid, 'unread_context', 'context_id is required')
    parts = section_map(root, records, state, key, audience)
    saved = state['reads'].get(cid, {})
    missing = []
    for name, value in parts.items():
        # State revision changes on receipt storage; contract/source facts remain required.
        if name == 'state' or name.startswith('state@'):
            token = saved.get(key + '/' + name, {})
            if token.get('record') != key or token.get('audience') != audience or token.get('context_id') != cid:
                missing.append(name)
            continue
        if name.startswith(('decision:', 'registry:', 'detail:')) and known_read(state, cid, audience, name, value):
            continue
        expected = receipt(state, key, cid, audience, name, value)
        if saved.get(key + '/' + name) != expected:
            missing.append(name)
    need(not missing, 'unread_context', 'Read all required sections in this context before dispatch', required_sections=missing)
    need(any(v.get('record') == key and v.get('audience') == audience and v.get('section', '').startswith('state') for v in saved.values()), 'unread_context', 'Current state must be read')


def invalidate(root, state, records, changed, reason, content_changed=(), preserve_progress=()):
    renewed = set(content_changed)
    renewed |= {key for key in records if any(depends_on(records, key, dep) for dep in content_changed)}
    affected = set(changed)
    while True:
        more = {k for k, r in records.items() if any(d in affected for d in r['requires'])}
        if more <= affected:
            break
        affected |= more
    for key in affected:
        if key not in state['records']:
            continue
        rec = state['records'][key]
        if key in renewed and rec['status'] == 'verified' and not any(f['scope_id'] == rec['scope_id'] and f['status'] == 'unresolved' for f in state['findings'].values()):
            # A completed acceptance starts a new failure episode after real drift.
            # Preserve total round history; do not spend failure allowance on success.
            scope = state['scopes'][rec['scope_id']]
            scope['limit'] = max(scope['limit'], scope['round'] + 3)
        if rec['status'] != 'queued':
            pointer = write_evidence(root, {'kind': 'invalidation', 'record': key, 'reason': reason, 'previous_status': rec['status'], 'previous_next_action': rec['next_action'], 'previous_evidence': rec['evidence'], 'revision': state['revision']})
            rec['evidence'].append(pointer)
        if key in preserve_progress and rec['status'] in ACTIVE | {'verified'}:
            previous = rec['status']
            if previous == 'verified':
                rec['next_action'] = 'run contract checks'
            rec.update(status='stopped', resume_status='checking' if previous == 'verified' else previous,
                       stop_reason='recheck_required')
        if rec['status'] == 'stopped':
            # Invalidating success never answers a question or releases a saved stop.
            # Reconcile acknowledges current identities, not a successful check.
            rec.update(target=snapshot(root, list(rec['target'])), input_digest=digest(selected_sections(root, records[key])),
                       current_result=None, current_verifier=None, round_inflight=False)
        else:
            rec.update(status='queued', next_action='recheck invalidated contract', stop_reason=None, resume_status=None, target=None, input_digest=None, current_result=None, current_verifier=None, round_inflight=False)
    # Content-addressed selected facts survive a code-only recheck in the same
    # context. Fresh state and contract reads are still required before dispatch.
    state['reads'] = {cid: {name: token for name, token in saved.items()
                            if token['section'].startswith(('decision:', 'registry:', 'detail:'))}
                      for cid, saved in state['reads'].items()}
    return sorted(affected)


def check_results(root, state, rec, contract, payload):
    checks = []
    for incoming in payload.get('checks', []):
        fields(incoming, ['command', 'files', 'exit_status', 'environment', 'environment_known', 'external_state', 'covers'], 'check')
        need(isinstance(incoming['command'], str) and incoming['command'] and type(incoming['exit_status']) is int, 'invalid_evidence', 'Invalid command/status')
        need(isinstance(incoming['environment'], dict) and incoming['environment'], 'invalid_evidence', 'Declare relevant environment/dependency identity')
        need(type(incoming['environment_known']) is bool and type(incoming['external_state']) is bool, 'invalid_evidence', 'Environment flags must be boolean')
        strings(incoming['covers'], 'covers')
        inputs = snapshot(root, incoming['files'])
        need(set(rec['target']) <= set(inputs), 'invalid_evidence', 'Check inputs must cover target files')
        checks.append({k: incoming[k] for k in ['command', 'exit_status', 'environment', 'environment_known', 'external_state', 'covers']} | {'inputs': inputs, 'runtime': runtime_environment()})
    referenced = {p for r in state['records'].values() for p in r['evidence']}
    for reused in payload.get('reuse', []):
        fields(reused, ['evidence', 'covers'], 'reuse')
        strings(reused['covers'], 'reuse covers', False)
        pointer = reused['evidence']
        need(pointer in referenced, 'invalid_evidence', 'Unreferenced evidence cannot be adopted')
        old = load_evidence(root, pointer)
        need(old.get('kind') == 'result', 'invalid_evidence', 'Only command results can be reused')
        for check in old['checks']:
            need(reusable_check(root, check) and check['environment'] == payload.get('environment'), 'stale_evidence', 'Evidence inputs/environment changed or cannot be identified')
            need(set(rec['target']) <= set(check['inputs']), 'stale_evidence', 'Evidence target differs')
            need(check['command'] in contract['verification'], 'stale_evidence', 'Command is not required by current contract')
            checks.append({**check, 'covers': reused['covers'], 'reused_from': pointer})
    return checks


def transition(root, expected_revision, payload):
    root = Path(root).resolve()
    fields(payload, ['op'], 'transition')
    cleanup = None
    with writer_lock(root):
        if payload['op'] == 'archive':
            return archive(root, expected_revision, payload)
        need(not (root / '.archive.json').exists(), 'archive_in_progress', 'Resume the recorded archive before any other transition')
        records, pdigest = plan(root)
        op = payload['op']
        if op == 'init':
            need(expected_revision == 0 and not (root / 'state.json').exists(), 'stale_revision', 'Initialization requires absent state and revision 0')
            need(not (root / 'run.md').exists() and not (root / 'HANDOFF.md').exists() and not (root / 'pending').exists(), 'legacy', 'Existing execution artifacts must finish/archive before new-cycle initialization')
            fields(payload, ['cycle', 'mode'], 'init')
            identifier(payload['cycle'], 'cycle')
            need(isinstance(payload['cycle'], str) and payload['cycle'] and payload['mode'] in {'companion', 'autonomous'}, 'invalid_input', 'Invalid cycle/mode')
            state = {'schema': 2, 'cycle': payload['cycle'], 'revision': 0, 'plan_digest': pdigest, 'mode': payload['mode'], 'cursor': next(iter(records)), 'records': {k: new_record(r) for k, r in records.items()}, 'scopes': {r['scope_id']: {'round': 0, 'limit': 3} for r in records.values()}, 'findings': {}, 'reads': {}, 'events': [], 'handoff_requested': False}
        else:
            state = load_state(root, records, pdigest, drift=op == 'reconcile')
            need(state['revision'] == expected_revision, 'stale_revision', 'Expected revision does not match', revision=state['revision'])
            if op == 'read':
                fields(payload, ['receipts'], 'read')
                need(isinstance(payload['receipts'], list) and payload['receipts'], 'invalid_input', 'Read receipts required')
                for token in payload['receipts']:
                    fields(token, ['context_id', 'audience', 'record', 'section', 'digest', 'plan_digest'], 'receipt')
                    need(token['audience'] in {'implementer', 'verifier'} and isinstance(token['context_id'], str) and token['context_id'], 'invalid_input', 'Invalid context identity')
                    parts = section_map(root, records, state, token['record'], token['audience'])
                    need(token['section'] in parts and token == receipt(state, token['record'], token['context_id'], token['audience'], token['section'], parts[token['section']]), 'stale_receipt', 'Read receipt no longer matches source/context')
                    saved = state['reads'].setdefault(token['context_id'], {})
                    saved[token['record'] + '/' + token['section']] = token
            elif op == 'reconcile':
                fields(payload, ['reason'], 'reconcile')
                old = state['records']
                by_scope = {r['scope_id']: r for r in old.values()}
                changed = set(drifted(root, state, records))
                content_changed = set(changed)
                preserve_progress = {key for key, rec in old.items() if key in records
                                     and rec['contract_digest'] == digest(records[key])
                                     and rec['input_digest'] == digest(selected_sections(root, records[key]))
                                     and rec['target'] and any(snapshot(root, list(rec['target'])).values())}
                updated = {}
                for key, contract in records.items():
                    existing = old.get(key) or by_scope.get(contract['scope_id'])
                    if existing and existing['scope_id'] != contract['scope_id']:
                        need(contract['scope_id'] in payload.get('approved_new_scopes', []) and payload.get('approval'), 'scope_change', 'New verification scope requires explicit approval')
                        existing = None
                    if existing is None:
                        need(contract['scope_id'] in payload.get('approved_new_scopes', []) and payload.get('approval'), 'scope_change', 'New scope requires explicit approval')
                        existing = new_record(contract)
                    elif existing['contract_digest'] != digest(contract):
                        changed.add(key)
                    updated[key] = copy.deepcopy(existing)
                    updated[key].update(contract_digest=digest(contract), scope_id=contract['scope_id'])
                    state['scopes'].setdefault(contract['scope_id'], {'round': 0, 'limit': 3})
                removed = set(old) - set(records)
                need(not any(old[k]['status'] in ACTIVE or old[k]['pending'] for k in removed), 'scope_change', 'Cannot drop active or pending record')
                for fid, status in payload.get('finding_dispositions', {}).items():
                    need(fid in state['findings'] and status == 'excluded' and payload.get('approval'), 'scope_change', 'Exclusions require explicit approval and existing finding')
                    state['findings'][fid]['status'] = status
                state['records'] = updated
                invalidate(root, state, records, changed & set(records), payload['reason'], content_changed & set(records), preserve_progress)
                state['plan_digest'] = pdigest
            elif op == 'approve-rounds':
                fields(payload, ['scope_id', 'additional', 'approval'], op)
                need(payload['scope_id'] in state['scopes'] and type(payload['additional']) is int and payload['additional'] > 0 and bool(payload['approval']), 'invalid_input', 'Explicit approval and positive additional rounds required')
                state['scopes'][payload['scope_id']]['limit'] += payload['additional']
                state['events'].append(write_evidence(root, {'kind': 'round-approval', **payload, 'revision': state['revision']}))
            elif op == 'resolve-pending':
                fields(payload, ['record', 'decision_key'], op)
                need(payload['record'] in state['records'], 'unknown', 'Unknown record')
                rec = state['records'][payload['record']]
                need(rec['status'] == 'stopped' and rec['pending'], 'pending_mismatch', 'No stopped question to resolve')
                path = inside(root, rec['pending']['path'])
                answer = read_json(path)
                fields(answer, ['question', 'answer', 'decision_key'], 'answered question')
                need(digest(answer['question']) == rec['pending'].get('question_digest'), 'pending_mismatch', 'Answered question identity differs from saved pending question')
                need(isinstance(answer['answer'], str) and answer['answer'].strip() and answer['decision_key'] == payload['decision_key'], 'pending_mismatch', 'Actual answer and matching decision reference required')
                item = decision(root, payload['decision_key'])
                pointer = write_evidence(root, {'kind': 'pending-resolution', 'record': payload['record'], 'answer': answer, 'decision_id': item['id'], 'decision_digest': digest(item)})
                rec['evidence'].append(pointer); rec['pending'] = None
                cleanup = path
            elif op == 'checkpoint':
                fields(payload, ['record', 'reason'], op)
                need(payload['record'] in state['records'], 'unknown', 'Unknown record')
                rec = state['records'][payload['record']]
                check_pending(root, rec)
                if 'target' in payload:
                    need(rec['status'] in {'implementing', 'fixing'}, 'invalid_transition', 'Only implementation/fixing may update target at checkpoint')
                    need(rec['input_digest'] == digest(selected_sections(root, records[payload['record']])), 'input_drift', 'Required constraints changed; reconcile before implementation')
                    register_implementer(root, records, state, payload['record'], payload.get('context_id', rec['context_id']))
                    rec['target'] = snapshot(root, payload['target'])
                rec['next_action'] = payload.get('next_action', rec['next_action'])
                state['events'].append(write_evidence(root, {'kind': 'checkpoint', 'record': payload['record'], 'reason': payload['reason'], 'target': rec['target'], 'next_action': rec['next_action'], 'revision': state['revision']}))
            elif op == 'complete-basic':
                fields(payload, ['record'], op)
                key = payload['record']
                need(key in records and records[key]['grade'] == 'basic' and records[key]['kind'] == 'step', 'invalid_transition', 'Direct completion requires a basic step')
                rec = state['records'][key]
                recheck = rec['status'] == 'stopped' and rec['stop_reason'] == 'recheck_required' and rec['resume_status'] == 'checking'
                need(rec['status'] in {'implementing', 'fixing', 'checking'} or recheck, 'invalid_transition', 'Start implementation or resume its saved state before direct completion')
                if state['records'][key]['status'] != 'checking':
                    apply_status(root, records, state, {**payload, 'status': 'checking'})
                if state['records'][key]['status'] == 'checking':
                    apply_status(root, records, state, {**payload, 'status': 'verified'})
            elif op == 'set':
                apply_status(root, records, state, payload)
            else:
                raise Error('invalid_input', 'Unknown transition operation')
        if (root / 'HANDOFF.md').exists():
            state['handoff_requested'] = True
        state['revision'] += 1
        state['cursor'] = cursor(state, records)
        # Validate all structural/completion invariants before committing the candidate.
        validate_state(root, state, records, pdigest)
        atomic_json(root / 'state.json', state)
        if cleanup:
            cleanup.unlink(missing_ok=True)
        try:
            render(root, _locked=True)
            derived = 'ok'
        except (OSError, Error):
            derived = 'regenerate with render'
        return {'status': 'ok', 'revision': state['revision'], 'cursor': state['cursor'], 'derived': derived}


def apply_status(root, records, state, payload):
    fields(payload, ['record', 'status'], 'set')
    key, target_status = payload['record'], payload['status']
    need(key in records and target_status in STATUSES, 'invalid_input', 'Unknown record/status')
    rec, contract = state['records'][key], records[key]
    old = rec['status']
    check_pending(root, rec)
    allowed = {'queued': {'implementing'} if contract['kind'] == 'step' else {'checking'}, 'implementing': {'checking', 'stopped'}, 'checking': {'verified', 'fixing', 'stopped'}, 'fixing': {'checking', 'stopped'}, 'stopped': {rec['resume_status']}, 'verified': set()}
    need(target_status in allowed[old], 'invalid_transition', f'{old} cannot transition to {target_status}')
    cid = payload.get('context_id', rec['context_id'])
    if target_status in {'implementing', 'checking', 'verified'} or old == 'stopped' and target_status == 'fixing':
        no_pending_dispatch(root, state)
        current_prerequisites(root, records, state, key)
    if old == 'queued':
        need(not drifted(root, state), 'code_drift', 'Existing target/check inputs changed; reconcile first')
        fields(payload, ['target', 'actor', 'workspace', 'context_id'], 'start')
        need(payload['actor'] is None or isinstance(payload['actor'], str), 'invalid_input', 'actor must be string or null')
        need(payload['workspace'] == str(root.parent.resolve()), 'workspace_drift', 'Workspace must match actual project root')
        audience = 'implementer' if contract['kind'] == 'step' else 'verifier'
        ensure_reads(root, records, state, key, cid, audience)
        snap = snapshot(root, payload['target'])
        need(any(v is not None for v in snap.values()), 'invalid_input', 'Target must identify at least one existing input file')
        rec.update(target=snap, actor=payload['actor'], workspace=payload['workspace'], context_id=cid)
        rec['input_digest'] = digest(selected_sections(root, contract))
        if contract['kind'] == 'step':
            register_implementer(root, records, state, key, cid)
    if old == 'stopped':
        need(rec['pending'] is None, 'pending_mismatch', 'Resolve pending answer before resume')
        need(rec['workspace'] == str(root.parent.resolve()) and (payload.get('workspace', rec['workspace']) == rec['workspace']), 'workspace_drift', 'Resume workspace differs')
        need(rec['target'] and valid_snapshot(root, rec['target']), 'code_drift', 'Resume target changed; reconcile first')
        ensure_reads(root, records, state, key, cid, 'verifier' if target_status == 'checking' and contract['grade'] == 'fresh' else 'implementer')
        if target_status in {'implementing', 'fixing'}:
            register_implementer(root, records, state, key, cid)
        rec.update(stop_reason=None, resume_status=None)
    if target_status == 'stopped':
        need(payload.get('reason'), 'invalid_input', 'Stop reason required')
        rec.update(resume_status=old, stop_reason=payload['reason'], next_action=payload.get('next_action', rec['next_action']))
        if payload.get('pending'):
            path = inside(root, payload['pending'])
            need(path.is_relative_to(root / 'pending') and path.is_file(), 'pending_mismatch', 'Pending question must exist under pending/')
            question = read_json(path)
            fields(question, ['question'], 'pending question')
            need(isinstance(question['question'], str) and question['question'].strip(), 'pending_mismatch', 'Pending question must have a body')
            rec['pending'] = {'path': payload['pending'], 'sha256': file_digest(path), 'question_digest': digest(question['question'])}
    if target_status == 'checking' and (old != 'stopped' or not rec['round_inflight']):
        need(rec['input_digest'] == digest(selected_sections(root, contract)), 'input_drift', 'Required constraints changed; reconcile before checking')
        if old in {'implementing', 'fixing'}:
            register_implementer(root, records, state, key, cid)
        scope = state['scopes'][contract['scope_id']]
        if scope['round'] >= scope['limit']:
            rec.update(status='stopped', resume_status='checking', stop_reason='round_cap')
            return
        if payload.get('target'):
            rec['target'] = snapshot(root, payload['target'])
        need(valid_snapshot(root, rec['target']), 'code_drift', 'Update actual target at checkpoint before checking')
        if contract['grade'] == 'fresh':
            verifier = payload.get('verifier_context_id')
            if not verifier:
                rec.update(status='stopped', resume_status='checking', stop_reason='independent_verifier_unavailable')
                return
            independent(records, state, key, verifier, current_target=True)
            need(verifier not in rec['verifier_contexts'], 'not_independent', 'Reverification requires a new independent context')
            ensure_reads(root, records, state, key, verifier, 'verifier')
            rec['verifier_contexts'].append(verifier)
            rec['current_verifier'] = verifier
        scope['round'] += 1; rec['round'] = scope['round']
        rec['round_inflight'] = True
        if old != 'stopped' or rec['next_action'] in {'start', 'continue'}:
            rec['next_action'] = 'run contract checks'
    elif old == 'stopped' and target_status == 'checking' and contract['grade'] == 'fresh':
        verifier = payload.get('verifier_context_id')
        independent(records, state, key, verifier, current_target=True)
        ensure_reads(root, records, state, key, verifier, 'verifier')
        if verifier != rec['current_verifier']:
            need(verifier not in rec['verifier_contexts'], 'not_independent', 'Replacement verifier must use a new independent context')
            scope = state['scopes'][contract['scope_id']]
            if scope['round'] >= scope['limit']:
                rec.update(status='stopped', resume_status='checking', stop_reason='round_cap', round_inflight=False)
                return
            state['events'].append(write_evidence(root, {'kind': 'verifier-replacement', 'record': key, 'previous_verifier': rec['current_verifier'], 'verifier': verifier, 'previous_round': rec['round'], 'next_round': scope['round'] + 1}))
            scope['round'] += 1; rec['round'] = scope['round']
            rec['verifier_contexts'].append(verifier); rec['current_verifier'] = verifier
    if target_status in {'verified', 'fixing'} and old == 'checking':
        need(rec['round_inflight'], 'invalid_state', 'No in-flight checking round')
        need(valid_snapshot(root, rec['target']), 'code_drift', 'Checked target changed')
        need(rec['input_digest'] == digest(selected_sections(root, contract)), 'input_drift', 'Required constraints changed; reconcile before result')
        ensure_reads(root, records, state, key, cid, 'implementer' if contract['grade'] == 'basic' else 'verifier')
        checks = check_results(root, state, rec, contract, payload)
        clauses = {c['id'] for c in contract['completion']}
        if target_status == 'verified':
            need(checks and all(c['exit_status'] == 0 for c in checks), 'failed_checks', 'Successful checks required')
            need(set(contract['verification']) <= {c['command'] for c in checks}, 'failed_checks', 'Required verification commands missing')
            need(clauses <= {clause for c in checks for clause in c['covers']}, 'failed_checks', 'Completion clauses not covered')
            need(all(state['records'][dep]['status'] == 'verified' for dep in contract['requires']), 'blocked', 'Predecessor/gate invalidated')
            if contract['grade'] == 'fresh':
                verdict = payload.get('verdict', {})
                independent(records, state, key, cid, current_target=True)
                need(verdict.get('status') == 'ACCEPT' and verdict.get('independent') is True and verdict.get('context_id') == cid and cid == rec['current_verifier'], 'not_independent', 'Current independent ACCEPT required')
            for fid in payload.get('resolved_findings', []):
                need(fid in state['findings'] and state['findings'][fid]['scope_id'] == contract['scope_id'], 'invalid_input', 'Unknown finding resolution')
                state['findings'][fid]['status'] = 'resolved'
            need(not any(f['scope_id'] == contract['scope_id'] and f['status'] == 'unresolved' for f in state['findings'].values()), 'unresolved', 'Unresolved contract violations cannot be verified')
        else:
            need(isinstance(payload.get('findings'), list) and payload['findings'], 'invalid_input', 'REJECT needs stable finding and reproduction')
            for f in payload['findings']:
                fields(f, ['id', 'clause', 'reproduction'], 'finding')
                identifier(f['id'], 'finding ID')
                need(f['clause'] in clauses and isinstance(f['reproduction'], str) and f['reproduction'], 'invalid_input', 'Finding needs failed clause and reproduction')
                previous = state['findings'].get(f['id'])
                need(previous is None or previous['scope_id'] == contract['scope_id'], 'invalid_input', 'Finding ID belongs to another scope')
                state['findings'][f['id']] = {**{k: f[k] for k in ['id', 'clause', 'reproduction']}, 'scope_id': contract['scope_id'], 'status': 'unresolved', 'round': rec['round']}
                if f['id'] not in rec['finding_ids']:
                    rec['finding_ids'].append(f['id'])
            if state['scopes'][contract['scope_id']]['round'] >= state['scopes'][contract['scope_id']]['limit']:
                target_status = 'stopped'; rec.update(resume_status='fixing', stop_reason='round_cap')
        pointer = write_evidence(root, {'kind': 'result', 'record': key, 'scope_id': contract['scope_id'], 'contract_digest': digest(contract), 'input_digest': rec['input_digest'], 'target': rec['target'], 'round': rec['round'], 'checks': checks, 'verdict': payload.get('verdict'), 'finding_ids': list(rec['finding_ids'])})
        rec['evidence'].append(pointer)
        rec['current_result'] = pointer
        rec['round_inflight'] = False
        rec['next_action'] = 'continue' if target_status == 'verified' else 'resolve findings'
    rec['status'] = target_status


def register_implementer(root, records, state, key, cid):
    """Keep all writers of a scope, including resumed and fixing contexts."""
    identifier(cid, 'implementer context')
    rec = state['records'][key]
    if cid not in rec['implementer_contexts']:
        ensure_reads(root, records, state, key, cid, 'implementer')
        rec['implementer_contexts'].append(cid)
    rec['context_id'] = cid


def render(root, handoff=False, expected_revision=None, _locked=False):
    root = Path(root).resolve()
    need(not (root / '.archive.json').exists(), 'archive_in_progress', 'Archive in progress; derived files are frozen')
    if not _locked:
        with writer_lock(root):
            records, pdigest = plan(root)
            state = load_state(root, records, pdigest)
            need(expected_revision is None or expected_revision == state['revision'], 'stale_revision', 'Render preference expected revision differs', revision=state['revision'])
            if (handoff or (root / 'HANDOFF.md').exists()) and not state['handoff_requested']:
                state['handoff_requested'] = True
                state['revision'] += 1
                validate_state(root, state, records, pdigest)
                atomic_json(root / 'state.json', state)
            return render(root, _locked=True)
    records, pdigest = plan(root)
    state = load_state(root, records, pdigest)
    rows = ['# Run (derived; state.json is authoritative)', '', f'Cycle: {state["cycle"]}; revision: {state["revision"]}; cursor: {state["cursor"]}', '', '| Record | Status | Round |', '|---|---|---|']
    rows.extend(f'| {k} | {r["status"]} | {r["round"]} |' for k, r in state['records'].items())
    (root / 'run.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    handoff = ['# Handoff (derived)', '', f'Cycle: {state["cycle"]}; revision: {state["revision"]}; cursor: {state["cursor"]}', '', 'Use context for current contract and selected inputs; do not inject this file alongside state.']
    if state['cursor'] in state['records']:
        rec = state['records'][state['cursor']]
        handoff += ['', f'Next: {rec["next_action"]}', f'Stop: {rec["stop_reason"]}']
    if state['handoff_requested'] or (root / 'HANDOFF.md').exists():
        (root / 'HANDOFF.md').write_text('\n'.join(handoff) + '\n', encoding='utf-8')
    return {'status': 'ok', 'revision': state['revision']}


def validate(root):
    need(not (root / '.archive.json').exists(), 'archive_in_progress', 'Archive in progress; resume archive')
    if not (root / 'state.json').exists():
        return {'status': 'legacy', 'message': 'No schema 2 state; preserve existing cycle format'}
    records, pdigest = plan(root)
    state = load_state(root, records, pdigest)
    check_mailbox(root, state)
    for key in records:
        sections(root, records, state, key, 'implementer')
    changed = drifted(root, state)
    need(not changed, 'code_drift', 'Target/check inputs changed', records=changed)
    return {'status': 'ok', 'schema': 2, 'revision': state['revision'], 'cursor': state['cursor']}


def archive(root, expected_revision, payload):
    """Resumable archive under writer lock. Marker is durable before any source removal."""
    marker_path = root / '.archive.json'
    if marker_path.exists():
        marker = read_json(marker_path)
        fields(marker, ['schema', 'cycle', 'revision', 'files'], 'archive marker')
        identifier(marker['cycle'], 'archive cycle')
        need(marker['schema'] == 1 and marker['revision'] == expected_revision, 'stale_revision', 'Resume archive with its recorded expected revision')
        need(isinstance(marker['files'], dict) and {'plan.md', 'state.json', 'run.md'} <= set(marker['files']), 'invalid_artifact', 'Incomplete archive manifest')
    else:
        result = validate(root)
        need(result.get('status') == 'ok' and result.get('cursor') == 'complete', 'blocked', 'Only a fully verified cycle can archive')
        records, pdigest = plan(root)
        state = load_state(root, records, pdigest)
        need(state['revision'] == expected_revision, 'stale_revision', 'Expected revision differs')
        need(not any(r['status'] == 'stopped' or r['pending'] for r in state['records'].values()), 'blocked', 'Stopped or pending work prevents archive')
        need(not (root / 'pending').exists() or not any((root / 'pending').iterdir()), 'pending_mismatch', 'Unresolved mailbox files prevent archive')
        render(root, _locked=True)
        files = ['plan.md', 'state.json', 'run.md']
        if (root / 'HANDOFF.md').exists():
            files.append('HANDOFF.md')
        if (root / 'evidence').exists():
            files.extend(str(path.relative_to(root)) for path in (root / 'evidence').rglob('*') if path.is_file())
        marker = {'schema': 1, 'cycle': state['cycle'], 'revision': state['revision'], 'files': {name: file_digest(inside(root, name)) for name in files}}
        destination = inside(root, 'cycles/' + state['cycle'])
        staging = inside(root, 'cycles/.archive-' + state['cycle'])
        need(not destination.exists() and not staging.exists(), 'archive_exists', 'Archive destination already exists; never overwrite it')
        atomic_json(marker_path, marker)
    for name, fingerprint in marker['files'].items():
        need(name in {'plan.md', 'state.json', 'run.md', 'HANDOFF.md'} or name.startswith('evidence/'), 'invalid_artifact', 'Unexpected archive source')
        inside(root, name)
        need(isinstance(fingerprint, str) and re.fullmatch(r'[a-f0-9]{64}', fingerprint), 'invalid_artifact', 'Invalid archive fingerprint')
    destination = inside(root, 'cycles/' + marker['cycle'])
    staging = inside(root, 'cycles/.archive-' + marker['cycle'])
    if not destination.exists():
        staging.mkdir(parents=True, exist_ok=True)
        for name, fingerprint in marker['files'].items():
            src, dst = inside(root, name), inside(staging, name)
            need(file_digest(src) == fingerprint, 'archive_drift', 'Source changed during archive; preserve files and diagnose', source=name)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                with src.open('rb') as incoming, dst.open('xb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing); outgoing.flush(); os.fsync(outgoing.fileno())
            need(file_digest(dst) == fingerprint, 'archive_drift', 'Staged archive differs from manifest', source=name)
        os.replace(staging, destination)
    for name, fingerprint in marker['files'].items():
        need(file_digest(inside(destination, name)) == fingerprint, 'archive_drift', 'Archive destination integrity differs', source=name)
    for name, fingerprint in marker['files'].items():
        src = inside(root, name)
        if src.exists():
            need(file_digest(src) == fingerprint, 'archive_drift', 'Current source changed; do not delete it', source=name)
            src.unlink()
    for directory in ['evidence', 'pending']:
        base = root / directory
        if base.exists():
            for child in sorted((p for p in base.rglob('*') if p.is_dir()), reverse=True):
                child.rmdir()
            base.rmdir()
    marker_path.unlink()
    return {'status': 'archived', 'cycle': marker['cycle'], 'revision': marker['revision'], 'destination': str(destination)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['validate', 'context', 'transition', 'render', 'decision-get']:
        command = sub.add_parser(name)
        command.add_argument('--root', type=Path, required=True)
        if name == 'context':
            command.add_argument('--record'); command.add_argument('--section'); command.add_argument('--context-id')
            command.add_argument('--remember', action='store_true')
            command.add_argument('--audience', choices=['implementer', 'verifier'], default='implementer')
        elif name == 'transition':
            command.add_argument('--expected-revision', type=int, required=True); command.add_argument('--input', type=Path, required=True)
        elif name == 'decision-get':
            command.add_argument('--key'); command.add_argument('--section'); command.add_argument('--domain')
        elif name == 'render':
            command.add_argument('--handoff', action='store_true')
            command.add_argument('--expected-revision', type=int)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == 'context':
            result = context(root, args.record, args.section, args.context_id, args.audience, args.remember)
        elif args.command == 'transition':
            result = transition(root, args.expected_revision, json.load(sys.stdin) if str(args.input) == '-' else read_json(args.input))
        elif args.command == 'decision-get':
            result = decision_get(root, args.key, args.section, args.domain)
        elif args.command == 'render':
            result = render(root, args.handoff, args.expected_revision)
        else:
            result = {'validate': validate, 'render': render}[args.command](root)
        if len(encoded(result)) > LIMIT:
            result = {'status': 'overflow', 'code': 'output_overflow', 'message': 'Request a narrower record, domain or explicit section; no content was truncated'}
        print(encoded(result).decode())
        return 0
    except Error as exc:
        result = {'status': 'error', 'code': exc.code, 'message': str(exc), **exc.details}
        if len(encoded(result)) > LIMIT:
            result = {'status': 'error', 'code': exc.code, 'message': 'Artifact validation failed; narrow the record/key/section for bounded error details'}
        print(encoded(result).decode())
        return 2
    except (OSError, TypeError, KeyError, ValueError) as exc:
        print(encoded({'status': 'error', 'code': 'invalid_artifact', 'message': str(exc)}).decode())
        return 2


if __name__ == '__main__':
    sys.exit(main())
