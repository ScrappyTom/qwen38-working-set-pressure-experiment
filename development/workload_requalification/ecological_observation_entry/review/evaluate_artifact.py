"""Separate post-response-seal E19 evaluator; no actor/model/native calls.

This prospective review helper is outside the actor/preparation source closure.
It executes only the exact original hidden script, preserves its observation and
records static artifact comparisons separately from that executable verdict.
"""
import argparse
import ast
import difflib
import json
from pathlib import Path
import re
import sys
import traceback

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import ecological_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def declared_api(body):
    """Public declarations and class fields, without executing candidate code."""
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


def artifact_assessment(before, candidate):
    original, final = before.file_map, candidate.file_map
    changed = sorted(path for path in original if original[path] != final[path])
    api, diffs = {}, {}
    for path in changed:
        diffs[path] = ''.join(difflib.unified_diff(
            original[path].decode('utf-8').splitlines(keepends=True),
            final[path].decode('utf-8').splitlines(keepends=True), fromfile=path, tofile=path))
        if path.endswith('.py'):
            try:
                previous, current = declared_api(original[path]), declared_api(final[path])
                missing = sorted(set(previous) - set(current))
                differing = sorted(name for name in previous.keys() & current.keys()
                                   if previous[name] != current[name])
                api[path] = dict(existing_public_declarations_preserved=not missing and not differing,
                    missing=missing, differing=differing,
                    added=sorted(set(current) - set(previous)))
            except (SyntaxError, UnicodeDecodeError) as problem:
                api[path] = dict(existing_public_declarations_preserved=False,
                                 parse_error=str(problem))
    others = sorted(path for path in original if path != study.TARGET)
    return dict(original_files=len(original), final_files=len(final), changed_paths=changed,
        untouched_files=len(original) - len(changed),
        target_changed=study.TARGET in changed,
        non_target_file_count=len(others),
        all_24_non_target_files_byte_identical=len(others) == 24 and all(original[p] == final[p] for p in others),
        changed_non_target_paths=[path for path in changed if path != study.TARGET],
        existing_public_declarations_preserved=all(row['existing_public_declarations_preserved'] for row in api.values()),
        api_comparisons=api, diffs=diffs,
        interpretation_limits=[
            'Static declaration comparison is not a semantic equivalence proof; added declarations are reported, not prohibited.',
            'Unchanged bytes establish preservation for those files, not correct use of their contents.',
            'Collection-stale conditions, the existing collection-input comparison, deterministic missing-ID direction, identifiers and status representation require direct source review.',
            'The task permits a valid repair rather than a single reference patch; changed paths are assessed, not prescribed.'])


def evaluate(version='002'):
    if not re.fullmatch(r'[0-9]{3}', version):
        raise ValueError('version must be exactly three decimal digits')
    run = AREA / ('run-' + version)
    seal_path = run / 'RESPONSE_SEAL.json'
    seal_bytes = seal_path.read_bytes()  # Required before any evaluator execution.
    seal = study.read(seal_path)
    if sha256_bytes(canonical_json_bytes(seal['files'])) != seal['aggregate_sha256']:
        raise ValueError('response seal inventory differs')
    for row in seal['files']:
        path = (run / row['path']).resolve()
        if (not path.is_relative_to(run.resolve()) or path.stat().st_size != row['size_bytes']
                or sha256_file(path) != row['sha256']):
            raise ValueError('sealed actor artifact differs: ' + row['path'])
    study.verify_sources(seal['source_sha256'])
    stem = 'final' if (run / 'final-candidate.json').is_file() else 'stopped'
    candidate_path, state_path = run / (stem + '-candidate.json'), run / (stem + '-state.json')
    candidate_bytes, state_bytes = candidate_path.read_bytes(), state_path.read_bytes()
    candidate = study.candidate_from_snapshot(study.read(candidate_path))
    state = study.read(state_path)
    if study.candidate_bytes(candidate) != candidate_bytes or state['candidate_id'] != candidate.candidate_id:
        raise ValueError('actual final candidate identity or state differs')
    if state['original_observation_state'] != study.original_observation_state():
        raise ValueError('final imported observation provenance differs')
    before = study.starting_candidate()
    assessment = artifact_assessment(before, candidate)
    hidden = study.hidden_checker()  # Exact original hash is checked by this accessor.
    out = AREA / 'review' / ('evaluation-' + version)
    out.mkdir(exist_ok=False)  # Never overwrite an earlier evaluation or failure.
    result = dict(status='evaluation_started', evaluator_execution_attempted=False,
        evaluator_executed=None, actor_feedback=False,
        additional_model_or_native_calls=False, response_seal_sha256=sha256_bytes(seal_bytes),
        evaluator_source_sha256=sha256_file(Path(__file__)),
        original_candidate_id=before.candidate_id, candidate_id=candidate.candidate_id,
        candidate_record=stem + '-candidate.json', candidate_record_sha256=sha256_bytes(candidate_bytes),
        state_record_sha256=sha256_bytes(state_bytes),
        actor_disposition=seal['disposition'], actor_submitted=state['submitted'],
        actor_requests_used=state['requests_used'], actor_operations_used=len(state['pairs']),
        evaluator_check_id='hidden', original_hidden_checker_sha256=sha256_bytes(hidden),
        original_task_sha256=study.TASK_SHA, original_public_checker_sha256=study.PUBLIC_SHA,
        original_observation_provenance_preserved=True, artifact_assessment=assessment,
        limits=[
            'Original hidden repeats the public missing-map case, checks the fresh graph and differing graph IDs; it does not exhaust every collection-input, sorting or API preservation case.',
            'An evaluator hidden pass is separate from the actor public check and never supplied as actor feedback.',
            'A final candidate matching the historical OBS-0001 candidate does not make the new hidden execution a legacy serializer check; target and exact checker definition remain distinct.',
            'Inspection order, acquisition choice, interpretation and current public applicability require saved-run replay and direct transcript review.'])
    error = None
    try:
        (out / 'hidden-original.py').write_bytes(hidden)
        (out / 'ARTIFACT_ASSESSMENT.json').write_bytes(canonical_json_bytes(assessment))
        for index, (path, diff) in enumerate(assessment['diffs'].items(), 1):
            (out / ('diff-' + str(index).zfill(2) + '.patch')).write_bytes(diff.encode('utf-8'))
        store = ObservationStore(out / 'observations')
        result['evaluator_execution_attempted'] = True
        observation = store.execute(candidate, hidden, 'hidden', 'CHK-0001')
        if store.read('CHK-0001') != observation:
            raise ValueError('evaluator observation readback differs')
        result.update(status='post_seal_hidden_pass' if observation['passed'] else 'post_seal_hidden_did_not_pass',
                      evaluator_executed=observation['executed'],
                      hidden_passed=observation['passed'], observation=observation)
    except BaseException as problem:
        error = problem
        result.update(status='post_seal_evaluation_failed', error_type=type(problem).__name__,
                      error=str(problem), traceback=traceback.format_exc())
        (out / 'FAILED.json').write_bytes(canonical_json_bytes(result))
    finally:
        if (seal_path.read_bytes() != seal_bytes or candidate_path.read_bytes() != candidate_bytes
                or state_path.read_bytes() != state_bytes):
            result.update(status='post_seal_evaluation_failed', immutable_actor_records_unchanged=False)
            if error is None:
                error = ValueError('sealed actor records changed during evaluation')
        else:
            result['immutable_actor_records_unchanged'] = True
        (out / 'RESULT.json').write_bytes(canonical_json_bytes(result))
        inventory = [dict(path=p.relative_to(out).as_posix(), size_bytes=p.stat().st_size,
            sha256=sha256_bytes(p.read_bytes())) for p in sorted(out.rglob('*')) if p.is_file()]
        (out / 'SEAL.json').write_bytes(canonical_json_bytes(dict(
            classification='post_response_seal_evaluator_only', response_seal_sha256=sha256_bytes(seal_bytes),
            evaluator_source_sha256=sha256_file(Path(__file__)), artifacts=inventory,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(inventory)))))
    if error is not None:
        raise error
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='002')
    args = parser.parse_args()
    print(json.dumps(evaluate(args.version), ensure_ascii=False, indent=2))
