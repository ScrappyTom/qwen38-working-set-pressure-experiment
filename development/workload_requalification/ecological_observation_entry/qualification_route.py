"""Evaluator-only exact observation/source/feedback route; zero model inference."""
import ast
import copy
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

PREFIX = 'src/addressable_information_layer/'
TARGET = PREFIX + 'summary_graph.py'
NAMED = (TARGET, PREFIX + 'summaries.py', PREFIX + 'records.py', PREFIX + 'policy.py')
CLASSIFICATION = 'evaluator-authored observation/source/feedback engineering journey; no model inference'


def shown_complete(view, path):
    rows = [row for row in view['working_set']['sources'] if row['path'] == path]
    if len(rows) != 1:
        raise ValueError('named exact current source not uniquely shown: ' + path)
    row = rows[0]
    if (row['kind'] != 'current_source' or row['returned_start_line'] != 1
            or row['returned_end_line'] != row['file_total_lines']
            or not row['whole_file_shown'] or not row['returned_extent_complete']
            or sha256_bytes(row['content'].encode()) != row['file_sha256']):
        raise ValueError('named complete source not actually delivered: ' + path)
    return row


def capture_shown(view, handle, raw):
    results = []
    if view['latest_feedback']:
        results.append(view['latest_feedback']['result'])
    for page in view['working_set']['saved_results']:
        if page.get('offset') == 0 and page.get('next_offset') is None:
            results.append(load_json_strict(page['exact_utf8']))
    matches = [row for row in results if row.get('kind') == 'imported_observation'
               and row.get('handle') == handle]
    if len(matches) != 1 or matches[0]['content_utf8'].encode() != raw:
        raise ValueError('complete acquired observation is not uniquely shown')
    return matches[0]


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
    label = 'status_pair'
    branch = Path(folder) / 'scripted' / label
    prospective = module.initial_session()
    prospective_bytes = canonical_json_bytes(module.snapshot(prospective))
    session = module.initial_session()
    initial = session.candidate
    module.attach_observations(session, branch, loop.log)
    adapter.preceding_feedback.clear()
    trials, checks, deliveries = [], [], []
    stem_base = 'scripted/' + label
    original, inventory, bodies = module.imports()
    entries = session.view()['imported_observations']['entries']
    bound = [row for row in entries if row['observed_candidate_id'] == initial.candidate_id]
    if (len(bound) != 1 or len(entries) != 2 or session.pairs or session.requests_used
            or session.calls_used or session.ranges or session.saved
            or session.working_account() is not None):
        raise ValueError('engineering route not at original empty two-observation entry')
    chosen = bound[0]['handle']

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
                handle = f'{kind}-{number:04d}'
                if restored.payload(handle) != session.payload(handle):
                    raise ValueError('actual archive payload failed reconstruction')
        return state, candidate

    def act(action, basis):
        before = copy.deepcopy(session.view())
        before_receipts = copy.deepcopy(adapter.preceding_feedback)
        request = adapter.request_for(before)
        count = loop.measure(before)
        if count > 23808 or session.delivery_blocked:
            raise ValueError('scripted actual input unavailable')
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis, operation=action)
        outcome = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        operations = outcome['operations']
        if len(operations) != 1 or not operations[0]['result'].get('accepted'):
            raise ValueError('scripted operation not accepted: ' + repr(outcome))
        result = operations[0]['result']
        after = copy.deepcopy(session.view())
        following = loop.measure(after)
        if following > 23808 or session.delivery_blocked:
            raise ValueError('complete actual feedback unavailable')
        if any(session.candidate.file_map[p] != raw for p, raw in initial.files if p != TARGET):
            raise ValueError('non-target file changed')
        capture_shown(after, chosen, bodies[chosen])
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
        number = len(trials) + 1
        stem = stem_base + f'/steps/{number:02d}'
        row = dict(before_view=before, preceding_before=before_receipts, before_request=request,
            reply=reply, outcome=copy.deepcopy(outcome), after_view=after,
            preceding_after=copy.deepcopy(adapter.preceding_feedback), input_tokens=count,
            next_input_tokens=following, information_path_justification=basis, classification=CLASSIFICATION)
        artifact = store.put(stem + '.json', canonical_json_bytes(row))
        loop.log.append('scripted_information_path_step', dict(route=label, step=number,
            input_tokens=count, next_input_tokens=following, completion_sent=False), [artifact])
        state, candidate = snapshot(stem)
        trials.append(dict(route=label, step=number, action=action['action'], input_tokens=count,
            next_input_tokens=following, requests_used=session.requests_used, operations_used=session.calls_used,
            candidate_id=session.candidate.candidate_id, actual_checks=actual_checks,
            snapshot_sha256=sha256_bytes(state), candidate_sha256=sha256_bytes(candidate),
            information_path_justification=basis))
        return result

    snapshot(stem_base + '/starting')
    store.put(stem_base + '/INFORMATION_PATH.md', (
        '# Evaluator-only observation/source correction route\n\n'
        'The displayed directory supplies exact candidate bindings; select its unique current row, '
        'then inspect the actual acquired body. The task names four source files and defines both '
        'status contracts; their displayed implementation establishes the two incorrect expressions. '
        'Real public assertions provide original and remaining-failure feedback; no hidden checker '
        'or donor correction enters any decision. Captures remain historical, while checks bind '
        'actual new successors. All choices are evaluator-authored feasibility, not Qwen behavior.\n'
    ).encode())
    capture = act(dict(action='reopen_observation', handle=chosen),
        'The displayed observation directory has exactly one recorded candidate equal to the current candidate. Retrieve that row, not the differently bound passing record; this is historical acquisition, not verification.')
    if capture['observed_candidate_id'] != initial.candidate_id or capture['content_utf8'].encode() != bodies[chosen]:
        raise ValueError('correctly bound exact capture not acquired')
    actual_body = load_json_strict(capture['content_utf8'])
    if actual_body['candidate_id'] != initial.candidate_id or actual_body['status'] != 'failed':
        raise ValueError('acquired body does not report this original incident')
    for path in NAMED:
        act(dict(action='read', path=path, start_line=1, end_line=0),
            'The original task names this current source for inspection before mutation. Obtain its complete body for the evaluator feasibility route; this is not an additional actor every-line gate.')
        row = shown_complete(session.view(), path)
        if row['content'].encode() != initial.file_map[path]:
            raise ValueError('original delivered source differs')
        deliveries.append(dict(path=path, candidate_id=row['candidate_id'], file_sha256=row['file_sha256'],
            start_line=1, end_line=row['returned_end_line'], actual_body_in_next_view=True))
    original_check = act(dict(action='check', check_id='public', expected_candidate_id=initial.candidate_id),
        'The correctly bound historical body reports status regressions, and the source exposes the implementation. Execute unchanged public on the original candidate to preserve the actual current failure.')
    first_diagnostic = failed_diagnostic(session.view(), original_check, 'assert status["collection_stale"] is True')
    source = shown_complete(session.view(), TARGET)
    old = '    collection_stale = bool(stale_artifact_summary_ids) and current_summary_ids != graph_summary_ids\n'
    new = old.replace(' and ', ' or ')
    if source['content'].count(old) != 1:
        raise ValueError('visible stale-status anchor differs')
    act(dict(action='patch', path=TARGET, old=old, new=new, expected_candidate_id=session.candidate.candidate_id,
        expected_file_sha256=source['file_sha256']),
        'The actual failed collection_stale assertion and displayed and-expression conflict with the task any-condition contract. Change only and to or, preserving the existing collection-input comparison.')
    intermediate = session.candidate
    second_check = act(dict(action='check', check_id='public', expected_candidate_id=intermediate.candidate_id),
        'The stale-status edit is saved and refreshed. Execute public on its actual successor; the historical incident and one saved edit do not prove the remaining missing-ID contract.')
    second_diagnostic = failed_diagnostic(session.view(), second_check, 'assert status["missing_artifact_ids"] == [b.artifact_id]')
    source = shown_complete(session.view(), TARGET)
    old_missing = '    missing_artifact_ids = sorted(artifact_id for artifact_id in address_maps if artifact_id not in summaries)\n'
    new_missing = old_missing.replace('in address_maps if artifact_id not in summaries', 'in summaries if artifact_id not in address_maps')
    if source['content'].count(old_missing) != 1:
        raise ValueError('visible missing-ID anchor differs')
    act(dict(action='patch', path=TARGET, old=old_missing, new=new_missing,
        expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=source['file_sha256']),
        'The actual remaining assertion, historical direction report and displayed comprehension conflict with the task: list summary artifacts lacking maps. Reverse only membership direction while preserving deterministic sorting.')
    final = session.candidate
    expected = initial.file_map[TARGET].decode().replace(old, new).replace(old_missing, new_missing).encode()
    if final.file_map[TARGET] != expected or public_api(final.file_map[TARGET]) != public_api(initial.file_map[TARGET]):
        raise ValueError('saved two-line contribution or public signatures differ')
    passed = act(dict(action='check', check_id='public', expected_candidate_id=final.candidate_id),
        'Both source-derived changes are saved together; all24other file bodies are exact. Execute unchanged public on this successor and consume the actual observation.')
    if not passed['passed'] or not session.view()['verification']['submission']['eligible']:
        raise ValueError('final candidate lacks current public pass')
    act(dict(action='submit', expected_candidate_id=final.candidate_id),
        'The actual public execution passes on the unchanged successor. Submit that checked candidate; imported incident records and earlier failures remain historical.')
    if session.requests_used != 11 or session.calls_used != 11 or not session.submitted:
        raise ValueError('eleven-decision evaluator journey did not close')
    if canonical_json_bytes(module.snapshot(prospective)) != prospective_bytes:
        raise ValueError('qualification changed fresh prospective entry')
    if [row['passed'] for row in checks] != [False, False, True]:
        raise ValueError('actual failure/correction sequence differs')
    return dict(classification=CLASSIFICATION, trials=trials, submitted=True,
        checks_executed=3, completion_requests=0, model_starting_state_untouched=True,
        named_source_deliveries=deliveries, chosen_observation=chosen,
        original_primary_diagnostic=first_diagnostic, single_repair_primary_diagnostic=second_diagnostic,
        final_candidate_id=final.candidate_id, untouched_file_bodies=24,
        checks=dict(original_failure_preserved=True, single_repair_failure_preserved=True,
                    current_public_pass=True, exact_checkpoint_restore=True,
                    retained_exact_capture=True, untouched_files_preserved=True))
