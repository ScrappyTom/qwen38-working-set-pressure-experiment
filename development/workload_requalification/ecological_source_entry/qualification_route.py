"""Evaluator-only E19 source journey; never supplied to the fresh actor.

Root-owned preparation executes the unchanged public script. This route uses
the exact source actually displayed and the resulting real assertion feedback,
not a donor, hidden acceptance, prior model draft or expected-answer artifact.
"""
import ast
import copy
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


PREFIX = 'src/addressable_information_layer/'
TARGET = PREFIX + 'artifact_units.py'
REOPEN = PREFIX + 'reopen.py'
NAMED = (TARGET, REOPEN, PREFIX + 'records.py', PREFIX + 'hashing.py')
INITIAL_ID = 'd2a57a0044458310fbe0b915eb88447b6f76b87dd511d68a0e31c29416342116'
CLASSIFICATION = 'evaluator-authored source/feedback engineering journey; no model inference'


def _shown_complete(view, path):
    """Require a delivered exact body, never an address or stored designation."""
    rows = [row for row in view['working_set']['sources'] if row['path'] == path]
    if len(rows) != 1:
        raise ValueError('the named current source is not uniquely displayed: ' + path)
    row = rows[0]
    if (row.get('kind') != 'current_source' or row['returned_start_line'] != 1
            or not row.get('returned_extent_complete') or not row.get('whole_file_shown')
            or row['returned_end_line'] != row['file_total_lines']):
        raise ValueError('engineering route did not obtain its complete named source: ' + path)
    if sha256_bytes(row['content'].encode('utf-8')) != row['file_sha256']:
        raise ValueError('displayed complete source fingerprint differs: ' + path)
    return row


def _inclusive_change(view):
    """Derive a one-line change from the displayed extraction/hash discrepancy."""
    row = _shown_complete(view, TARGET)
    source = row['content']
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not {'exact_text_for_unit', '_make_unit'} <= functions.keys():
        raise ValueError('displayed source lacks the governing extraction/map definitions')
    extractor = ast.get_source_segment(source, functions['exact_text_for_unit'])
    maker = ast.get_source_segment(source, functions['_make_unit'])
    if ('if unit.inline_text is not None:' not in extractor
            or 'return unit.inline_text' not in extractor
            or 'lines[start_line - 1 : end_line]' not in maker
            or 'content_hash = sha256_text(text)' not in maker):
        raise ValueError('displayed inline behavior or inclusive hashing premise differs')
    lines = [line for line in extractor.splitlines(keepends=True)
        if 'return "\\n".join(lines[' in line]
    if len(lines) != 1 or lines[0].count('unit.end_line - 1') != 1:
        raise ValueError('displayed extraction does not have the qualified omitted-end expression')
    old = lines[0]
    new = old.replace('unit.end_line - 1', 'unit.end_line')
    if source.count(old) != 1:
        raise ValueError('displayed extraction anchor is not unique')
    return row, old, new


def _strict_change(view):
    """Derive strict truncation while keeping mismatch blocking and IDs exact."""
    row = _shown_complete(view, REOPEN)
    source = row['content']
    tree = ast.parse(source)
    function = next((node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'materialize_reopen'), None)
    if function is None:
        raise ValueError('displayed source lacks the governing reopen function')
    body = ast.get_source_segment(source, function)
    if ('if observed_hash != unit.content_hash:' not in body
            or 'ReopenStatus.BLOCKED' not in body or 'stable_id(' not in body):
        raise ValueError('displayed mismatch-blocking or identifier premise differs')
    lines = [line for line in body.splitlines(keepends=True)
        if line.lstrip().startswith('truncated = ')]
    if len(lines) != 1 or lines[0].strip() != 'truncated = len(exact_text) >= max_chars':
        raise ValueError('displayed source lacks the qualified equality-truncation expression')
    old = lines[0]
    new = old.replace(' >= ', ' > ')
    if source.count(old) != 1:
        raise ValueError('displayed truncation anchor is not unique')
    return row, old, new


def _shown_failed_public(view, result, assertion):
    """Require the real failed assertion in the actual next decision input."""
    feedback = view['latest_feedback']
    if (not feedback or feedback['result'].get('observation') != result['observation']
            or feedback['result'].get('checked_candidate_id') != result['checked_candidate_id']):
        raise ValueError('actual failed check receipt is not the displayed latest result')
    state = view['verification']['checks']['public']
    if (not state or not state['applies_to_current'] or state['passed']
            or state['candidate_id'] != result['checked_candidate_id']):
        raise ValueError('displayed public failure does not apply to the current candidate')
    report = feedback['result']['report']
    records = [row for row in report['criteria']
        if row['criterion'] == 'public_execution' and row['met'] is False]
    if len(records) != 1 or assertion not in records[0].get('stderr', {}).get('text', ''):
        raise ValueError('actual displayed primary diagnostic does not expose the expected assertion')
    if not report['observation_capture_complete'] or not report['executed']:
        raise ValueError('the observed public failure did not complete with exact capture')
    return copy.deepcopy(records[0])


def _public_api(source):
    """Compare declarations/signatures without executing candidate code."""
    tree = ast.parse(source)
    return [(node.name, ast.dump(node.args, include_attributes=False),
             ast.dump(node.returns, include_attributes=False) if node.returns else None,
             [ast.dump(item, include_attributes=False) for item in node.decorator_list])
            for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def qualify_contribution(module, session, measure, preceding, record=None, request_for=None):
    """Four named reads, real failure, one repair/failure, second repair/pass.

    Complete reads are an evaluator feasibility choice, not a new every-line
    actor gate. The fresh model still chooses its own acquisition and operations.
    """
    initial = session.candidate
    initial_view = copy.deepcopy(session.view())
    if (initial.candidate_id != INITIAL_ID or len(initial.file_map) != 25
            or sum(map(len, initial.file_map.values())) != 128575
            or session.pairs or session.requests_used or session.calls_used
            or session.working_account() is not None):
        raise ValueError('engineering journey did not begin at the exact empty fresh E19 entry')
    rows, checks, deliveries = [], [], []

    def act(action, basis):
        before = copy.deepcopy(session.view())
        before_receipts = copy.deepcopy(preceding)
        before_request = copy.deepcopy(request_for(before)) if request_for else None
        count = measure(before)
        if count > 23808 or session.delivery_blocked:
            raise ValueError('the actual decision input cannot be delivered')
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis, operation=action)
        outcome = module.process_reply(session, reply, measure, preceding)
        if len(outcome['operations']) != 1 or not outcome['operations'][0]['result'].get('accepted'):
            raise ValueError('scripted E19 operation was not singly accepted: ' + repr(outcome))
        result = outcome['operations'][0]['result']
        after = copy.deepcopy(session.view())
        following = measure(after)
        if following > 23808 or session.delivery_blocked:
            raise ValueError('the actual operation feedback cannot be delivered')
        if any(session.candidate.file_map[path] != raw
                for path, raw in initial.files if path not in (TARGET, REOPEN)):
            raise ValueError('an untouched candidate file changed during qualification')
        row = dict(before_view=before, preceding_before=before_receipts,
            before_request=before_request, reply=reply, outcome=copy.deepcopy(outcome),
            after_view=after, preceding_after=copy.deepcopy(preceding),
            input_tokens=count, next_input_tokens=following,
            information_path_justification=basis, classification=CLASSIFICATION)
        rows.append(row)
        if record:
            record(row, session)
        if action['action'] == 'check':
            if (not result.get('executed') or not result.get('capture_complete')
                    or result['check_id'] != 'public'
                    or result['checked_candidate_id'] != session.candidate.candidate_id):
                raise ValueError('public execution is not complete and bound to the actual successor')
            checks.append(copy.deepcopy(result))
        return result

    for path in NAMED:
        act(dict(action='read', path=path, start_line=1, end_line=0),
            'The exact unchanged task names this source for inspection before mutation. Read its complete current body for this evaluator feasibility route; this does not impose a new every-line actor policy.')
        row = _shown_complete(session.view(), path)
        if row['content'].encode('utf-8') != initial.file_map[path]:
            raise ValueError('the actual complete named read differs from the original source')
        deliveries.append(dict(path=path, candidate_id=row['candidate_id'],
            file_sha256=row['file_sha256'], start_line=row['returned_start_line'],
            end_line=row['returned_end_line'], body_sha256=sha256_bytes(row['content'].encode()),
            request=session.requests_used, actual_body_in_next_view=True))

    # Inspecting these actual sent bodies does not need all four to remain
    # resident forever. This bounded engineering route happens to retain them.
    for path in NAMED:
        _shown_complete(session.view(), path)
    original = act(dict(action='check', check_id='public', expected_candidate_id=initial.candidate_id),
        'The original task supplies both boundary contracts and requests public verification. Execute the original public script on the unchanged original candidate to preserve its real failure before any repair.')
    if original['passed']:
        raise ValueError('the original candidate unexpectedly passed its original public check')
    first_diagnostic = _shown_failed_public(session.view(), original,
        'assert receipt.materialized_text == expected')
    source, old, new = _inclusive_change(session.view())
    act(dict(action='patch', path=TARGET, old=old, new=new,
        expected_candidate_id=session.candidate.candidate_id,
        expected_file_sha256=source['file_sha256']),
        'The actual public diagnostic fails exact materialization. The displayed extraction omits the declared end line, while displayed _make_unit hashes lines[start_line - 1 : end_line] and the task defines inclusive coordinates. Change only the extraction endpoint, keeping inline return behavior and map/identifier construction unchanged.')
    first_repair = session.candidate
    if first_repair.file_map[TARGET] != initial.file_map[TARGET].decode('utf-8').replace(old, new).encode('utf-8'):
        raise ValueError('inclusive repair differs from the one displayed source-derived line')
    if first_repair.file_map[REOPEN] != initial.file_map[REOPEN]:
        raise ValueError('single-repair qualification already altered the second defect')
    single = act(dict(action='check', check_id='public', expected_candidate_id=first_repair.candidate_id),
        'The inclusive extraction patch was actually accepted and source was refreshed. Execute public on that successor; do not assume saving one repair establishes the remaining truncation contract.')
    if single['passed']:
        raise ValueError('the one-repair candidate unexpectedly passed the remaining truncation assertion')
    second_diagnostic = _shown_failed_public(session.view(), single,
        'assert receipt.truncated is False')
    source, old_truncation, new_truncation = _strict_change(session.view())
    act(dict(action='patch', path=REOPEN, old=old_truncation, new=new_truncation,
        expected_candidate_id=session.candidate.candidate_id,
        expected_file_sha256=source['file_sha256']),
        'The actual successor public assertion now fails equality completeness. The displayed reopen comparison is >=, while the task says truncated is true only for text strictly longer than max_chars. Change only that comparison to >; keep hash-mismatch blocking, slicing, receipt identifiers and public arguments intact.')
    final = session.candidate
    if (final.file_map[TARGET] != first_repair.file_map[TARGET]
            or final.file_map[REOPEN] != initial.file_map[REOPEN].decode('utf-8').replace(old_truncation, new_truncation).encode('utf-8')):
        raise ValueError('the final repair did not preserve the first contribution or exact second change')
    for path in (TARGET, REOPEN):
        if _public_api(final.file_map[path].decode('utf-8')) != _public_api(initial.file_map[path].decode('utf-8')):
            raise ValueError('source signature/declaration preservation differs')
    passing = act(dict(action='check', check_id='public', expected_candidate_id=final.candidate_id),
        'Both source-derived boundary edits are saved in the current candidate, with all 23 other file bodies unchanged. Execute the unchanged public script on this exact successor and consume its real observation.')
    if not passing['passed'] or not session.view()['verification']['submission']['eligible']:
        raise ValueError('the completed contribution lacks its actual current public pass')
    act(dict(action='submit', expected_candidate_id=final.candidate_id),
        'The actual completed public execution passes on this unchanged current successor. Submit that candidate; historical failures remain historical and exact.')
    if not session.submitted or session.requests_used != 10 or session.calls_used != 10:
        raise ValueError('the declared ten-decision evaluator journey did not close exactly')
    return dict(status='qualified_no_model_inference', classification=CLASSIFICATION,
        completion_requests=0, submitted=True, checks_executed=len(checks),
        scripted_requests=session.requests_used, scripted_operations=session.calls_used,
        starting_candidate_id=initial.candidate_id, single_repair_candidate_id=first_repair.candidate_id,
        final_candidate_id=final.candidate_id, actual_check_verdicts=[r['passed'] for r in checks],
        named_source_deliveries=deliveries, original_primary_diagnostic=first_diagnostic,
        single_repair_primary_diagnostic=second_diagnostic, untouched_file_bodies=23,
        declaration_signatures_preserved=True, optional_account_not_required=True,
        maximum_input_tokens=max([row['input_tokens'] for row in rows] + [row['next_input_tokens'] for row in rows]),
        snapshots=rows, initial_view=initial_view)


def _qualify(module, loop, adapter, store, folder):
    """Root-owned native preparation; independent of the prospective entry."""
    label = 'two_boundary_correction'
    branch = Path(folder) / 'scripted' / label
    initial = module.initial_session()
    initial_bytes = canonical_json_bytes(module.snapshot(initial))
    initial_candidate = module.candidate_bytes(initial.candidate)
    session = module.initial_session()
    module.attach_observations(session, branch, loop.log)
    adapter.preceding_feedback.clear()
    trials = []

    def snapshot(current, stem):
        state_bytes = canonical_json_bytes(module.snapshot(current))
        candidate_bytes = module.candidate_bytes(current.candidate)
        artifacts = [store.put(stem + '-state.json', state_bytes),
            store.put(stem + '-candidate.json', candidate_bytes),
            store.put(stem + '-preceding-feedback.json', canonical_json_bytes(adapter.preceding_feedback))]
        artifacts.extend(store.put(stem + f'-diffs/EVT-{sequence:04d}.patch', text.encode('utf-8'))
            for sequence, text in current.diffs.items())
        loop.log.append('scripted_state_saved', dict(stem=stem,
            candidate_id=current.candidate.candidate_id, completion_sent=False,
            independent_history_namespace=True), artifacts)
        restored = module.restore(load_json_strict(state_bytes), current.candidate, branch, replay=True)
        if (canonical_json_bytes(module.snapshot(restored)) != state_bytes
                or restored.view() != current.view()
                or module.candidate_bytes(restored.candidate) != candidate_bytes
                or restored.pairs != current.pairs
                or restored.working_account() != current.working_account()):
            raise ValueError('the actual scripted checkpoint did not reconstruct exactly')
        for sequence in range(1, len(current.pairs) + 1):
            for kind in ('EVT', 'RES'):
                handle = f'{kind}-{sequence:04d}'
                if restored.payload(handle) != current.payload(handle):
                    raise ValueError('restored archive payload differs: ' + handle)
        return state_bytes, candidate_bytes

    snapshot(session, f'scripted/{label}/starting')
    store.put(f'scripted/{label}/INFORMATION_PATH.md', (
        '# E19 evaluator information-path qualification\n\n'
        'This is a root-executed engineering route with no model completion. It begins at '
        'the exact empty E19 original candidate and performs four complete task-named reads. '
        'Those complete extents are an evaluator feasibility choice, not an additional actor gate.\n\n'
        'The real original public failure and displayed extraction/_make_unit discrepancy '
        'justify the inclusive endpoint repair. The real one-repair failure and displayed '
        '>= comparison plus the task strictness contract justify the second repair. '
        'Both actual failure diagnostics must reach the next view, and all snapshots/raw '
        'observations are preserved. No donor, hidden verdict, prior private model draft '
        'or checker expected-answer value supplies an edit premise.\n\n'
        'All 23 other file bodies and function signatures remain exact. The only modified '
        'lines are extraction endpoint and truncation comparison, preserving the shown '
        'inline branch, hash-mismatch block, identifiers and API construction. A public '
        'pass is scoped acceptance; post-seal hidden evaluation and direct artifact review '
        'remain separate. Scripted feasibility does not establish autonomous selection.\n'
    ).encode('utf-8'))

    def record(row, current):
        stem = f'scripted/{label}/steps/{len(trials) + 1:02d}'
        artifact = store.put(stem + '.json', canonical_json_bytes(row))
        loop.log.append('scripted_information_path_step', dict(route=label,
            step=len(trials) + 1, input_tokens=row['input_tokens'],
            next_input_tokens=row['next_input_tokens'], completion_sent=False), [artifact])
        state_bytes, candidate_bytes = snapshot(current, stem)
        actual_checks = []
        for operation in row['outcome']['operations']:
            result = operation['result']
            if not result.get('executed'):
                continue
            observed = current.observations.read(result['observation'])
            if (not observed['capture_complete'] or observed['candidate_id'] != result['checked_candidate_id']
                    or observed['streams'] != result['streams']):
                raise ValueError('executed check is not bound to the exact preserved observation')
            for name in ('stdout', 'stderr'):
                raw = (current.observations.directory(result['observation']) / (name + '.bin')).read_bytes()
                if (len(raw) != observed['streams'][name]['captured_bytes']
                        or sha256_bytes(raw) != observed['streams'][name]['sha256']):
                    raise ValueError('preserved exact check stream differs')
            actual_checks.append(dict(observation=result['observation'], scope=result['check_id'],
                candidate_id=result['checked_candidate_id'], passed=result['passed'], capture_complete=True))
        trials.append(dict(route=label, step=len(trials) + 1,
            action=row['reply']['operation']['action'], input_tokens=row['input_tokens'],
            next_input_tokens=row['next_input_tokens'], requests_used=current.requests_used,
            operations_used=current.calls_used, candidate_id=current.candidate.candidate_id,
            actual_checks=actual_checks, snapshot_sha256=sha256_bytes(state_bytes),
            candidate_sha256=sha256_bytes(candidate_bytes),
            information_path_justification=row['information_path_justification']))

    value = qualify_contribution(module, session, loop.measure, adapter.preceding_feedback,
        record=record, request_for=adapter.request_for)
    summary = {key: item for key, item in value.items() if key not in ('snapshots', 'initial_view')}
    store.put(f'scripted/{label}/RESULTS.json', canonical_json_bytes(summary))
    if (canonical_json_bytes(module.snapshot(initial)) != initial_bytes
            or module.candidate_bytes(initial.candidate) != initial_candidate
            or [check['passed'] for row in trials for check in row['actual_checks']] != [False, False, True]):
        raise ValueError('qualification altered the prospective entry or omitted the real failure sequence')
    return dict(trials=trials, classification=CLASSIFICATION, submitted=session.submitted,
        checks_executed=value['checks_executed'], completion_requests=0,
        model_starting_state_untouched=True, named_source_deliveries=value['named_source_deliveries'],
        final_candidate_id=value['final_candidate_id'], checks=dict(original_failure_preserved=True,
            single_repair_failure_preserved=True, current_public_pass=True,
            exact_checkpoint_restore=True, untouched_files_preserved=True,
            no_automatic_check_or_hidden_feedback=True, checked_submission=True))


def qualify(module, loop, adapter, store, folder):
    """Restore prospective receipts even after an unsuccessful preparation."""
    previous = copy.deepcopy(adapter.preceding_feedback)
    try:
        return _qualify(module, loop, adapter, store, folder)
    finally:
        adapter.preceding_feedback[:] = previous
