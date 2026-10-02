"""Evaluator-only complete-source/correction route; zero completion requests."""
import ast
import copy
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

PREFIX = 'src/addressable_information_layer/'
IMPORTERS, SAVED = PREFIX + 'importers.py', PREFIX + 'saved_runs.py'
GROUPS = (
    ('importers.py', 'saved_runs.py', 'fixture_packs.py', 'records.py'),
    ('artifact_units.py', 'content_log.py', 'hashing.py', 'storage.py'),
    ('renderer.py', 'policy.py', 'readiness.py'))
CLASSIFICATION = 'evaluator-authored complete-source/feedback engineering journey; no model inference'


def shown_complete(view, path):
    displayed = list(view['working_set']['sources'])
    if view['latest_feedback']:
        result = view['latest_feedback']['result']
        displayed.extend([result['source']] if 'source' in result else result.get('sources', []))
    rows = [row for row in displayed if row['path'] == path]
    if len(rows) != 1:
        raise ValueError('exact source not uniquely shown: ' + path)
    row = rows[0]
    if (row['kind'] != 'current_source' or row['returned_start_line'] != 1
            or row['returned_end_line'] != row['file_total_lines']
            or not row['whole_file_shown'] or not row['returned_extent_complete']
            or sha256_bytes(row['content'].encode()) != row['file_sha256']):
        raise ValueError('requested whole-source group was paged or omitted: ' + path)
    return row


def failed_diagnostic(view, result, assertion):
    latest = view['latest_feedback']['result']
    state = view['verification']['checks']['public']
    if (latest['observation'] != result['observation'] or result['passed']
            or not state['applies_to_current'] or state['passed']):
        raise ValueError('actual current failed public result not shown')
    rows = [row for row in latest['report']['criteria']
            if row['criterion'] == 'public_execution' and row['met'] is False]
    if len(rows) != 1 or assertion not in rows[0].get('stderr', {}).get('text', ''):
        raise ValueError('actual primary failure diagnostic omitted')
    return copy.deepcopy(rows[0])


def public_api(body):
    return [(node.name, ast.dump(node.args, include_attributes=False),
             ast.dump(node.returns, include_attributes=False) if node.returns else None)
            for node in ast.walk(ast.parse(body.decode()))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def qualify(module, loop, adapter, store, folder):
    previous = copy.deepcopy(adapter.preceding_feedback)
    try:
        return _qualify(module, loop, adapter, store, folder)
    finally:
        adapter.preceding_feedback[:] = previous


def _qualify(module, loop, adapter, store, folder):
    branch = Path(folder) / 'scripted/import_boundaries'
    prospective = module.initial_session()
    prospective_bytes = canonical_json_bytes(module.snapshot(prospective))
    session, initial = module.initial_session(), module.starting_candidate()
    module.attach_observations(session, branch, loop.log)
    adapter.preceding_feedback.clear()
    trials, checks, deliveries, dispatched = [], [], [], {}
    stem_base = 'scripted/import_boundaries'

    def snapshot(stem):
        state = canonical_json_bytes(module.snapshot(session))
        candidate = module.candidate_bytes(session.candidate)
        artifacts = [store.put(stem + '-state.json', state),
            store.put(stem + '-candidate.json', candidate),
            store.put(stem + '-preceding-feedback.json', canonical_json_bytes(adapter.preceding_feedback))]
        artifacts.extend(store.put(stem + f'-diffs/EVT-{number:04d}.patch', text.encode())
                         for number, text in session.diffs.items())
        loop.log.append('scripted_state_saved', dict(stem=stem, completion_sent=False,
            candidate_id=session.candidate.candidate_id, independent_history_namespace=True), artifacts)
        restored = module.restore(load_json_strict(state), session.candidate, branch, replay=True)
        if (canonical_json_bytes(module.snapshot(restored)) != state or restored.view() != session.view()
                or module.candidate_bytes(restored.candidate) != candidate):
            raise ValueError('actual checkpoint failed exact typed reconstruction')
        for number in range(1, len(session.pairs) + 1):
            for kind in ('RES', 'EVT'):
                if restored.payload(f'{kind}-{number:04d}') != session.payload(f'{kind}-{number:04d}'):
                    raise ValueError('actual archive payload failed reconstruction')
        return state, candidate

    def act(action, basis, accepted=True):
        before, before_receipts = copy.deepcopy(session.view()), copy.deepcopy(adapter.preceding_feedback)
        request, count = adapter.request_for(before), loop.measure(before)
        if count > 23808 or session.delivery_blocked:
            raise ValueError('scripted actual input unavailable')
        session.mark_delivered(before)
        session.begin_request()
        dispatched[session.requests_used] = copy.deepcopy(before)
        reply = dict(discussion=basis, operation=action)
        outcome = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        if len(outcome['operations']) != 1 or outcome['operations'][0]['result'].get('accepted') is not accepted:
            raise ValueError('scripted operation outcome differs: ' + repr(outcome))
        result = outcome['operations'][0]['result']
        after, following = copy.deepcopy(session.view()), loop.measure(session.view())
        if following > 23808 or session.delivery_blocked:
            raise ValueError('complete actual feedback unavailable')
        if any(session.candidate.file_map[p] != raw for p, raw in initial.files if p not in (IMPORTERS, SAVED)):
            raise ValueError('unrelated source changed')
        actual_checks = []
        if action['action'] == 'check':
            observed = session.observations.read(result['observation'])
            if (not observed['capture_complete'] or not observed['executed']
                    or observed['candidate_id'] != session.candidate.candidate_id
                    or observed['streams'] != result['streams']
                    or observed['checker_sha256'] != module.PUBLIC_SHA):
                raise ValueError('actual check/raw observation binding differs')
            checks.append(copy.deepcopy(result))
            actual_checks.append(dict(observation=result['observation'], scope='public',
                candidate_id=result['checked_candidate_id'], passed=result['passed'], capture_complete=True))
        number, stem = len(trials) + 1, stem_base + f'/steps/{len(trials)+1:02d}'
        row = dict(before_view=before, preceding_before=before_receipts, before_request=request,
            reply=reply, outcome=copy.deepcopy(outcome), after_view=after,
            preceding_after=copy.deepcopy(adapter.preceding_feedback), input_tokens=count,
            next_input_tokens=following, information_path_justification=basis, classification=CLASSIFICATION)
        artifact = store.put(stem + '.json', canonical_json_bytes(row))
        loop.log.append('scripted_information_path_step', dict(step=number, input_tokens=count,
            next_input_tokens=following, completion_sent=False), [artifact])
        state, candidate = snapshot(stem)
        trials.append(dict(step=number, action=action['action'], input_tokens=count,
            next_input_tokens=following, requests_used=session.requests_used, operations_used=session.calls_used,
            candidate_id=session.candidate.candidate_id, actual_checks=actual_checks,
            snapshot_sha256=sha256_bytes(state), candidate_sha256=sha256_bytes(candidate),
            information_path_justification=basis))
        return result

    def group(names, basis):
        paths = [PREFIX + name for name in names]
        act(dict(action='work_on', sources=[dict(path=p, start_line=1, end_line=0) for p in paths], results=[]), basis)
        for path in paths:
            row = shown_complete(session.view(), path)
            if row['content'].encode() != session.candidate.file_map[path]:
                raise ValueError('actual selected source bytes differ')
            deliveries.append(dict(path=path, start_line=1, end_line=row['file_total_lines'],
                file_sha256=row['file_sha256'], actually_in_next_view=True))

    def patch(path, old, new, basis, accepted=True):
        source = shown_complete(session.view(), path)
        if source['content'].count(old) != 1:
            raise ValueError('source-derived anchor is not unique')
        return act(dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=source['file_sha256']),
            basis, accepted)

    snapshot(stem_base + '/starting')
    store.put(stem_base + '/INFORMATION_PATH.md', (
        '# Evaluator-only cumulative inspection and correction\n\n'
        'The exact task names eleven source paths and inclusive boundaries. Inspect them '
        'through three bounded replacement groups; actual returned extents must be complete. '
        'Retain cumulative delivered coverage, not permanent co-residence. A premature '
        'source-backed proposal is rejected while seven paths remain absent. Reselect '
        'the two exact targets after all coverage. Real public assertions preserve failed '
        'observations; task and visible source, not the diagnostic alone, justify each '
        'boundary correction. Reference work and choices remain evaluator-only.\n').encode())
    group(GROUPS[0], 'The displayed task names these four files for complete pre-mutation inspection. Replace selection with their exact bodies; the host must report actual extents, not assume end_line=0 returned all lines.')
    refused = patch(IMPORTERS, '        if path.stat().st_size >= max_file_bytes:\n',
        '        if path.stat().st_size > max_file_bytes:\n',
        'Deliberately exercise missing-coverage rejection: displayed source conflicts with the task equality contract, but seven named paths have not reached any dispatched input. Preserve this public proposal without mutation.', False)
    if session.candidate.candidate_id != initial.candidate_id or refused.get('rejection_code') != 'missing_source_coverage':
        raise ValueError('missing-coverage rejection or preservation differs')
    for names in GROUPS[1:]:
        group(names, 'The original task still requires these named current files. Replace inspected bodies with the next exact group; prior real coverage must survive release while current edit authority does not.')
    group(('importers.py', 'saved_runs.py'), 'All eleven files have now actually reached dispatch. Select the two source-identified targets for the local contribution; historical coverage alone cannot authorize their edit.')
    original_check = act(dict(action='check', check_id='public', expected_candidate_id=initial.candidate_id),
        'The task and inspected sources identify inclusive boundaries; execute unchanged public on the original candidate to obtain the actual current observation.')
    diagnostic = failed_diagnostic(session.view(), original_check, 'assert imported["artifacts"] == [{"path": "a.txt"}]')
    patch(IMPORTERS, '        if path.stat().st_size >= max_file_bytes:\n', '        if path.stat().st_size > max_file_bytes:\n',
        'The displayed size guard excludes equality contrary to the task. Preserve all filtering/order and admit equal byte sizes.')
    partial = act(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id),
        'The first repair is saved. Check its actual successor; one changed guard does not establish the file-count or JSONL contracts.')
    remaining = failed_diagnostic(session.view(), partial, 'assert imported["artifacts"] == [{"path": "a.txt"}]')
    old = '        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n        if len(artifacts) > max_files:\n            break\n'
    new = '        if len(artifacts) >= max_files:\n            break\n        rel = path.relative_to(root).as_posix()\n        artifacts.append({"path": rel})\n'
    patch(IMPORTERS, old, new,
        'The task says at most the first N eligible files. Visible source appends before checking >N; check the current count before append so N=0 also admits zero. The unchanged assertion shows a remaining failure but does not by itself isolate this cause.')
    patch(SAVED, '            if idx >= MAX_JSONL_LINES:\n', '            if idx > MAX_JSONL_LINES:\n',
        'The task includes event conversion of record MAX_JSONL_LINES. The inspected loop enumerates from1 and excludes that boundary with >=; change only this exclusion.')
    patch(SAVED, '            if idx >= MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:\n',
        '            if idx > MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:\n',
        'The distinct embedded-artifact loop similarly excludes record MAX_JSONL_LINES. Preserve its independent artifact-count/size caps and converter behavior while including the boundary.')
    final = session.candidate
    for path in (IMPORTERS, SAVED):
        if public_api(final.file_map[path]) != public_api(initial.file_map[path]):
            raise ValueError('public declarations differ')
    passed = act(dict(action='check', check_id='public', expected_candidate_id=final.candidate_id),
        'All four source-derived boundary corrections are saved, with 23 other bodies preserved. Execute unchanged public on the actual successor; evaluator-only zero-count assessment stays separately declared.')
    if not passed['passed'] or not session.view()['verification']['submission']['eligible']:
        raise ValueError('final current public check did not pass')
    act(dict(action='submit', expected_candidate_id=final.candidate_id),
        'Actual unchanged public passed on this current successor; submit it without promoting historical observations or a supplemental evaluator into actor assurance.')
    if session.requests_used != 13 or session.calls_used != 13 or not session.submitted:
        raise ValueError('thirteen-decision feasibility route did not close')
    if [r['passed'] for r in checks] != [False, False, True]:
        raise ValueError('actual failure/correction sequence differs')
    if canonical_json_bytes(module.snapshot(prospective)) != prospective_bytes:
        raise ValueError('qualification changed the fresh prospective entry')
    for path, row in session.prerequisite_state()['coverage'].items():
        for witness in row['witnesses']:
            shown = dispatched[witness['request_number']]
            if sha256_bytes(canonical_json_bytes(shown)) != witness['presentation_sha256']:
                raise ValueError('stored coverage witness differs from actual measured dispatch')
            body = ''.join(initial.file_map[path].decode().splitlines(keepends=True)[
                witness['start_line']-1:witness['end_line']]).encode()
            if sha256_bytes(body) != witness['content_sha256'] or len(body) != witness['size_bytes']:
                raise ValueError('stored witness exact bytes differ')
    return dict(classification=CLASSIFICATION, trials=trials, submitted=True,
        checks_executed=3, completion_requests=0, model_starting_state_untouched=True,
        source_deliveries=deliveries, missing_coverage_rejection=refused,
        coverage_state=module.coverage_state(session), original_primary_diagnostic=diagnostic,
        partial_repair_primary_diagnostic=remaining, final_candidate_id=final.candidate_id,
        untouched_file_bodies=23, exact_checkpoint_restore=True,
        selection_replacement_preserves_coverage=True, authentic_current_public_pass=True)
