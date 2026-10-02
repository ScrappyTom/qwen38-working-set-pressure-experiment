"""Separate post-seal E19 artifact evaluation; never actor feedback.

This helper is deliberately outside the frozen actor/preparation source closure.
It first verifies the sealed run by saved-data replay, restores the actual final
candidate through the prerequisite-aware task, and then executes only the exact
original hidden checker. Run only after the parent explicitly authorizes it.
"""
import argparse
import ast
import copy
import difflib
import importlib.util
import json
from pathlib import Path
import re
import sys
import traceback

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import ecological_task as study
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

REPLAY = AREA / 'review/verify_run.py'


def _within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('sealed path escapes its artifact root')
    return path


def verify_inventory(run, seal):
    if sha256_bytes(canonical_json_bytes(seal['files'])) != seal['aggregate_sha256']:
        raise ValueError('response seal inventory differs')
    names = set()
    for row in seal['files']:
        if row['path'] in names:
            raise ValueError('duplicate sealed artifact address')
        names.add(row['path'])
        path = _within(run, row['path'])
        if path.stat().st_size != row['size_bytes'] or sha256_file(path) != row['sha256']:
            raise ValueError('sealed actor artifact differs: ' + row['path'])
    for name, digest in seal['private_runtime_files_local_only'].items():
        if sha256_file(_within(run / 'private-runtime', name)) != digest:
            raise ValueError('sealed private runtime artifact differs: ' + name)
    study.verify_sources(seal['source_sha256'])
    records = verify_records(run / 'records.jsonl', run)
    if len(records) != seal['record_count']:
        raise ValueError('custody record count differs')
    closure = [record['payload'] for record in records if record['record_type'] == 'runtime_closed']
    if (len(closure) != 1 or not closure[0]['owned_server_shutdown_verified']
            or not closure[0]['dedicated_port_free'] or not seal['port_free']):
        raise ValueError('owned runtime closure is not established')
    return dict(sealed_files=len(names), source_files=len(seal['source_sha256']),
        custody_records=len(records), records_sha256=sha256_file(run / 'records.jsonl'),
        source_inventory_sha256=sha256_bytes(canonical_json_bytes(seal['source_sha256'])),
        owned_runtime_closed=True)


def declared_api(body):
    """Public declarations and class fields; no candidate code execution."""
    declarations = {}
    def visit(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('_'):
                declarations[prefix + node.name] = dict(kind=type(node).__name__,
                    args=ast.dump(node.args, include_attributes=False),
                    returns=ast.dump(node.returns, include_attributes=False) if node.returns else None,
                    decorators=[ast.dump(value, include_attributes=False) for value in node.decorator_list])
            elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                declarations[prefix + node.name] = dict(kind='ClassDef',
                    bases=[ast.dump(value, include_attributes=False) for value in node.bases],
                    keywords=[ast.dump(value, include_attributes=False) for value in node.keywords],
                    decorators=[ast.dump(value, include_attributes=False) for value in node.decorator_list],
                    annotated_fields=[ast.dump(value, include_attributes=False)
                        for value in node.body if isinstance(value, ast.AnnAssign)])
                visit(node.body, prefix + node.name + '.')
    visit(ast.parse(body.decode('utf-8')).body)
    return declarations


def _statement(tree, name):
    function = next(node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'summary_graph_status')
    return next(node for node in function.body if isinstance(node, ast.Assign)
        and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == name)


def target_structure(before, after):
    """Report the narrow known repair shape, without making it the oracle."""
    try:
        original, current = ast.parse(before.decode()), ast.parse(after.decode())
        initial = _statement(current, 'collection_stale')
        missing = _statement(current, 'missing_artifact_ids')
        expected_or = ast.parse(
            'bool(stale_artifact_summary_ids) or current_summary_ids != graph_summary_ids',
            mode='eval').body
        expected_missing = ast.parse(
            'sorted(artifact_id for artifact_id in summaries if artifact_id not in address_maps)',
            mode='eval').body
        modified = copy.deepcopy(original)
        _statement(modified, 'collection_stale').value = copy.deepcopy(initial.value)
        _statement(modified, 'missing_artifact_ids').value = copy.deepcopy(missing.value)
        removed = added = 0
        for opcode, a, b, c, d in difflib.SequenceMatcher(None,
                before.decode().splitlines(), after.decode().splitlines()).get_opcodes():
            if opcode != 'equal':
                removed += b-a
                added += d-c
        return dict(first_collection_assignment=ast.unparse(initial),
            missing_id_assignment=ast.unparse(missing),
            first_assignment_matches_inclusive_or_expression=(
                ast.dump(initial.value, include_attributes=False) == ast.dump(expected_or, include_attributes=False)),
            missing_ids_match_sorted_summary_without_map_expression=(
                ast.dump(missing.value, include_attributes=False) == ast.dump(expected_missing, include_attributes=False)),
            only_these_two_statement_values_changed_in_ast=(
                ast.dump(modified, include_attributes=False) == ast.dump(current, include_attributes=False)),
            source_lines_removed=removed, source_lines_added=added,
            interpretation='Syntactic observations for direct review, not a required reference-patch identity or a complete semantic proof.')
    except (SyntaxError, UnicodeDecodeError, StopIteration) as problem:
        return dict(structure_available=False, error=str(problem))


def artifact_assessment(before, candidate):
    original, final = before.file_map, candidate.file_map
    changed = sorted(path for path in original if original[path] != final[path])
    api, diffs = {}, {}
    for path in changed:
        diffs[path] = ''.join(difflib.unified_diff(
            original[path].decode().splitlines(keepends=True), final[path].decode().splitlines(keepends=True),
            fromfile=path, tofile=path))
        if path.endswith('.py'):
            try:
                previous, current = declared_api(original[path]), declared_api(final[path])
                missing = sorted(set(previous) - set(current))
                differing = sorted(name for name in previous.keys() & current.keys()
                    if previous[name] != current[name])
                api[path] = dict(existing_public_declarations_preserved=not missing and not differing,
                    missing=missing, differing=differing, added=sorted(set(current)-set(previous)))
            except (SyntaxError, UnicodeDecodeError) as problem:
                api[path] = dict(existing_public_declarations_preserved=False, parse_error=str(problem))
    others = sorted(path for path in original if path != study.TARGET)
    return dict(original_files=len(original), final_files=len(final), changed_paths=changed,
        untouched_files=len(original)-len(changed), target_changed=study.TARGET in changed,
        non_target_file_count=len(others),
        all_24_non_target_files_byte_identical=(len(others) == 24 and all(original[p] == final[p] for p in others)),
        changed_non_target_paths=[path for path in changed if path != study.TARGET],
        existing_public_declarations_preserved=all(row['existing_public_declarations_preserved'] for row in api.values()),
        api_comparisons=api, diffs=diffs,
        summary_graph_status_structure=target_structure(original[study.TARGET], final[study.TARGET]),
        interpretation_limits=[
            'Static declarations are not a semantic equivalence proof; added declarations are reported, not prohibited.',
            'A syntactic two-statement match is descriptive; another substantively correct repair is not excluded.',
            'Collection-input handling, deterministic ordering and status representation still require direct source review.',
            'Unchanged bytes establish preservation, not correct use of those sources.'])


def _replay(version):
    spec = importlib.util.spec_from_file_location('prerequisite_post_seal_saved_replay', REPLAY)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    # This bound helper uses saved native counts and replay observations; it
    # prohibits subprocess execution and makes no model/native/tokenizer calls.
    return helper.verify(version)


def evaluate(version='001'):
    if not re.fullmatch(r'[0-9]{3}', version):
        raise ValueError('version must be exactly three decimal digits')
    run = AREA / ('run-' + version)
    seal_path = run / 'RESPONSE_SEAL.json'
    seal_bytes = seal_path.read_bytes()  # An open run fails before any execution.
    seal = study.read(seal_path)
    out = AREA / 'review' / ('evaluation-' + version)
    out.mkdir(exist_ok=False)  # Preserve every earlier evaluation/failure.
    helper_bytes, replay_bytes = Path(__file__).read_bytes(), REPLAY.read_bytes()
    result = dict(status='evaluation_started', evaluator_execution_attempted=False,
        evaluator_executed=None, actor_feedback=False, additional_model_or_native_calls=False,
        response_seal_sha256=sha256_bytes(seal_bytes), evaluator_source_sha256=sha256_bytes(helper_bytes),
        saved_replay_helper_sha256=sha256_bytes(replay_bytes),
        evaluator_check_id='hidden', actor_disposition=seal['disposition'])
    immutable = {seal_path: seal_bytes}
    error = None
    try:
        (out / 'EVALUATOR_SOURCE.py.txt').write_bytes(helper_bytes)
        (out / 'REPLAY_HELPER.py.txt').write_bytes(replay_bytes)
        result['custody'] = verify_inventory(run, seal)
        verification = _replay(version)
        if verification['response_seal_sha256'] != result['response_seal_sha256']:
            raise ValueError('saved replay verified a different response seal')
        (out / 'SAVED_RUN_VERIFICATION.json').write_bytes(canonical_json_bytes(verification))
        stem = 'final' if (run / 'final-candidate.json').is_file() else 'stopped'
        candidate_path, state_path = run / (stem+'-candidate.json'), run / (stem+'-state.json')
        candidate_bytes, state_bytes = candidate_path.read_bytes(), state_path.read_bytes()
        immutable.update({candidate_path: candidate_bytes, state_path: state_bytes})
        candidate = study.candidate_from_snapshot(study.read(candidate_path))
        state = study.read(state_path)
        if study.candidate_bytes(candidate) != candidate_bytes or state['candidate_id'] != candidate.candidate_id:
            raise ValueError('actual final candidate identity or state differs')
        restored = study.restore(state, candidate, run, replay=True)
        # The task's decoder restores canonical numeric addresses as integers;
        # compare its typed normalization, not JSON string-key sort order.
        normalized_state = {**state, 'diffs': restored.diffs}
        if (canonical_json_bytes(study.snapshot(restored)) != canonical_json_bytes(normalized_state)
                or state['original_observation_state'] != study.original_observation_state()):
            raise ValueError('final restoration or original observation provenance differs')
        (out / 'ACTOR_CANDIDATE.json').write_bytes(candidate_bytes)
        (out / 'ACTOR_STATE.json').write_bytes(state_bytes)
        before = study.starting_candidate()
        assessment = artifact_assessment(before, candidate)
        hidden = study.hidden_checker()  # Accessor checks the unchanged original hash.
        result.update(original_candidate_id=before.candidate_id, candidate_id=candidate.candidate_id,
            candidate_record=stem+'-candidate.json', candidate_record_sha256=sha256_bytes(candidate_bytes),
            state_record_sha256=sha256_bytes(state_bytes), actor_submitted=state['submitted'],
            actor_requests_used=state['requests_used'], actor_operations_used=len(state['pairs']),
            original_hidden_checker_sha256=sha256_bytes(hidden), original_task_sha256=study.TASK_SHA,
            original_public_checker_sha256=study.PUBLIC_SHA, original_observation_provenance_preserved=True,
            prerequisite_checkpoint_restored=True, source_exposure=verification['source_exposure'],
            actor_verification=restored.verification_view(), artifact_assessment=assessment,
            limits=[
                'The original hidden script checks missing-map, fresh graph and differing graph IDs, not every collection-input, sorting or API case.',
                'Hidden execution is post-seal evaluator evidence, never actor feedback or an actor public check.',
                'Matching the historical OBS-0001 candidate does not transfer its legacy serializer assurance to this check.',
                'Verified exposure is not comprehension or substantive inspection; interpretation requires direct transcript review.'])
        (out / 'hidden-original.py').write_bytes(hidden)
        (out / 'ARTIFACT_ASSESSMENT.json').write_bytes(canonical_json_bytes(assessment))
        for index, (_, diff) in enumerate(assessment['diffs'].items(), 1):
            (out / ('diff-'+str(index).zfill(2)+'.patch')).write_bytes(diff.encode())
        store = ObservationStore(out / 'observations')
        result['evaluator_execution_attempted'] = True
        observation = store.execute(candidate, hidden, 'hidden', 'CHK-0001')
        result.update(evaluator_executed=observation.get('executed'), observation=observation)
        if observation.get('executed') is not True:
            raise ValueError('original hidden checker was not executed: ' + str(observation.get('error')))
        if store.read('CHK-0001') != observation:
            raise ValueError('evaluator observation readback differs')
        result.update(status='post_seal_hidden_pass' if observation['passed'] else 'post_seal_hidden_did_not_pass',
            evaluator_executed=observation['executed'], hidden_passed=observation['passed'], observation=observation)
    except BaseException as problem:
        error = problem
        result.update(status='post_seal_evaluation_failed', error_type=type(problem).__name__,
            error=str(problem), traceback=traceback.format_exc())
    finally:
        try:
            if any(path.read_bytes() != raw for path, raw in immutable.items()):
                raise ValueError('sealed actor records changed during evaluation')
            if Path(__file__).read_bytes() != helper_bytes or REPLAY.read_bytes() != replay_bytes:
                raise ValueError('evaluation helper source changed during evaluation')
            verify_inventory(run, seal)
            result['immutable_actor_records_unchanged'] = True
        except BaseException as problem:
            result['immutable_actor_records_unchanged'] = False
            result['preservation_error'] = str(problem)
            if error is None:
                error = problem
                result.update(status='post_seal_evaluation_failed', error_type=type(problem).__name__,
                    error=str(problem), traceback=traceback.format_exc())
        if error is not None:
            (out / 'FAILED.json').write_bytes(canonical_json_bytes(result))
        (out / 'RESULT.json').write_bytes(canonical_json_bytes(result))
        inventory = [dict(path=p.relative_to(out).as_posix(), size_bytes=p.stat().st_size,
            sha256=sha256_file(p)) for p in sorted(out.rglob('*')) if p.is_file()]
        (out / 'SEAL.json').write_bytes(canonical_json_bytes(dict(
            classification='post_response_seal_evaluator_only', response_seal_sha256=sha256_bytes(seal_bytes),
            evaluator_source_sha256=sha256_bytes(helper_bytes), saved_replay_helper_sha256=sha256_bytes(replay_bytes),
            artifacts=inventory, aggregate_sha256=sha256_bytes(canonical_json_bytes(inventory)))))
    if error is not None:
        raise error
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    print(json.dumps(evaluate(args.version), ensure_ascii=False, indent=2))
