"""Separate sealed E20 evaluation; no actor feedback, model or native calls.

Actor mode requires a closed run, saved-data replay and exact final restoration.
Reference mode requires the qualified zero-completion preparation and its actual
step-13 checkpoint; it executes only the unchanged supplemental boundary probe.
This file is deliberately outside the frozen task source closure. Parent execution
authorization is still required; implementing this helper does not launch it.
"""
import argparse
import ast
import copy
import difflib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import ecological_task as study
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

REPLAY = AREA / 'review/verify_run.py'
PROBE = study.ROOT / 'maintenance/resume_after_020/import_boundary_probe.py'
PROBE_SHA = 'b5a2ac3f21015dd15212a7fda5c99329cac3199a736d491e9d2c02be54a7c8b6'
TARGETS = (study.TARGET, study.SAVED_RUNS)
REFERENCE_STEM = 'scripted/import_boundaries/steps/13'


def _within(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('noncanonical sealed artifact address')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path.relative_to(root.resolve()).as_posix() != relative:
        raise ValueError('sealed artifact address escapes or aliases its root')
    return path


def verify_inventory(folder, seal, *, actor):
    rows, names = seal['files'], set()
    if sha256_bytes(canonical_json_bytes(rows)) != seal['aggregate_sha256']:
        raise ValueError('seal inventory differs')
    for row in rows:
        if row['path'] in names:
            raise ValueError('duplicate sealed artifact address')
        names.add(row['path'])
        path = _within(folder, row['path'])
        if path.stat().st_size != row['size_bytes'] or sha256_file(path) != row['sha256']:
            raise ValueError('sealed artifact differs: ' + row['path'])
    for name, digest in seal['private_runtime_files_local_only'].items():
        if sha256_file(_within(folder / 'private-runtime', name)) != digest:
            raise ValueError('sealed private runtime artifact differs: ' + name)
    study.verify_sources(seal['source_sha256'])
    if seal['source_sha256'] != study.source_identities():
        raise ValueError('sealed implementation closure differs from the current exact task')
    records = verify_records(folder / 'records.jsonl', folder)
    if actor and len(records) != seal['record_count']:
        raise ValueError('actor custody record count differs')
    closed = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    if (len(closed) != 1 or not closed[0]['owned_server_shutdown_verified']
            or not closed[0]['dedicated_port_free'] or (actor and not seal['port_free'])):
        raise ValueError('owned runtime closure is not established')
    if not actor:
        if seal['status'] != 'qualified_no_model_inference' or seal['completion_requests'] != 0:
            raise ValueError('reference preparation is not qualified with zero completions')
        if any(row['record_type'] in ('invocation_started', 'response_received', 'invocation_completed')
               for row in records):
            raise ValueError('reference preparation contains model invocation records')
    return dict(sealed_files=len(names), source_files=len(seal['source_sha256']),
        custody_records=len(records), records_sha256=sha256_file(folder / 'records.jsonl'),
        source_inventory_sha256=sha256_bytes(canonical_json_bytes(seal['source_sha256'])),
        owned_runtime_closed=True), records


def _load_replay():
    spec = importlib.util.spec_from_file_location('e20_post_seal_saved_replay', REPLAY)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def declarations(body):
    """Static public declarations plus every existing callable interface."""
    result = {}
    def visit(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[prefix + node.name] = dict(kind=type(node).__name__,
                    public=not node.name.startswith('_'), args=ast.dump(node.args, include_attributes=False),
                    returns=ast.dump(node.returns, include_attributes=False) if node.returns else None,
                    decorators=[ast.dump(v, include_attributes=False) for v in node.decorator_list])
            elif isinstance(node, ast.ClassDef):
                result[prefix + node.name] = dict(kind='ClassDef', public=not node.name.startswith('_'),
                    bases=[ast.dump(v, include_attributes=False) for v in node.bases],
                    keywords=[ast.dump(v, include_attributes=False) for v in node.keywords],
                    decorators=[ast.dump(v, include_attributes=False) for v in node.decorator_list],
                    annotated_fields=[ast.dump(v, include_attributes=False) for v in node.body
                        if isinstance(v, ast.AnnAssign)])
                visit(node.body, prefix + node.name + '.')
            elif not prefix and isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and (not target.id.startswith('_') or target.id == '__all__'):
                        result[target.id] = dict(kind=type(node).__name__, public=True,
                            declaration=ast.dump(node, include_attributes=False))
    visit(ast.parse(body.decode('utf-8')).body)
    return result


def artifact_assessment(before, candidate):
    original, final = before.file_map, candidate.file_map
    if set(original) != set(final) or len(original) != 25:
        raise ValueError('actual artifact file inventory differs')
    changed = sorted(path for path in original if original[path] != final[path])
    api, diffs = {}, {}
    for path in sorted(original):
        if path in changed:
            diffs[path] = ''.join(difflib.unified_diff(original[path].decode().splitlines(keepends=True),
                final[path].decode().splitlines(keepends=True), fromfile=path, tofile=path))
        if not path.endswith('.py'):
            continue
        try:
            prior, current = declarations(original[path]), declarations(final[path])
            missing = sorted(set(prior) - set(current))
            differing = sorted(k for k in prior.keys() & current.keys() if prior[k] != current[k])
            public_changes = sorted(k for k in set(missing + differing) if prior[k]['public'])
            api[path] = dict(existing_public_declarations_preserved=not public_changes,
                all_existing_callable_interfaces_and_public_constants_preserved=not missing and not differing,
                missing=missing, differing=differing, public_changes=public_changes,
                added=sorted(set(current)-set(prior)))
        except (SyntaxError, UnicodeDecodeError) as problem:
            api[path] = dict(existing_public_declarations_preserved=False,
                all_existing_callable_interfaces_and_public_constants_preserved=False, parse_error=str(problem))
    others = sorted(set(original)-set(TARGETS))
    return dict(original_files=len(original), final_files=len(final), changed_paths=changed,
        repair_target_paths=list(TARGETS), non_target_file_count=len(others),
        all_23_other_files_byte_identical=(len(others) == 23 and all(original[p] == final[p] for p in others)),
        changed_non_target_paths=[p for p in changed if p not in TARGETS],
        existing_public_declarations_preserved=all(r['existing_public_declarations_preserved'] for r in api.values()),
        all_existing_callable_interfaces_and_public_constants_preserved=all(
            r['all_existing_callable_interfaces_and_public_constants_preserved'] for r in api.values()),
        api_comparisons=api, diffs=diffs, reference_patch_identity_required=False,
        interpretation_limits=[
            'Static interface equality and unchanged bytes do not prove semantic preservation.',
            'No particular source spelling or reference-patch identity is required.',
            'Ordering, schema, identity, artifact materialization and exclusions need direct source review beyond executed cases.',
            'The supplemental twelve cases examine directory byte and count boundaries; they do not replace the original hidden grade.'])


def _restore(folder, candidate_path, state_path):
    raw_candidate, raw_state = candidate_path.read_bytes(), state_path.read_bytes()
    candidate, state = study.candidate_from_snapshot(study.read(candidate_path)), study.read(state_path)
    if study.candidate_bytes(candidate) != raw_candidate or candidate.candidate_id != state['candidate_id']:
        raise ValueError('actual candidate bytes or state identity differ')
    session = study.restore(state, candidate, folder, replay=True)
    if canonical_json_bytes(study.snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('actual continuous-coverage checkpoint reconstruction differs')
    return candidate, state, session, raw_candidate, raw_state


def _reference(folder, seal, records):
    proof = study.read(folder / 'QUALIFICATION.json')
    if (proof['status'] != 'qualified' or proof['completion_requests'] != 0
            or not proof['entry_unchanged_after_qualification'] or not proof['route']['submitted']
            or proof['route']['completion_requests'] != 0 or not proof['native_forms']['status'] == 'passed'):
        raise ValueError('reference qualification does not establish the unchanged-entry route')
    trials = proof['route']['trials']
    if len(trials) != 13 or trials[-1]['step'] != 13 or trials[-1]['action'] != 'submit':
        raise ValueError('reference is not the actual thirteen-decision route')
    candidate_path, state_path = folder / (REFERENCE_STEM+'-candidate.json'), folder / (REFERENCE_STEM+'-state.json')
    branch = folder / 'scripted/import_boundaries'
    candidate, state, session, raw_candidate, raw_state = _restore(branch, candidate_path, state_path)
    if (state['requests_used'] != 13 or len(state['pairs']) != 13 or not state['submitted']
            or candidate.candidate_id != proof['route']['final_candidate_id']
            or sha256_bytes(raw_state) != trials[-1]['snapshot_sha256']
            or sha256_bytes(raw_candidate) != trials[-1]['candidate_sha256']):
        raise ValueError('reference final checkpoint does not bind the qualified route')
    selected = [r for r in records if r['record_type'] == 'scripted_state_saved'
        and r['payload']['stem'] == REFERENCE_STEM]
    if len(selected) != 1 or selected[0]['payload']['candidate_id'] != candidate.candidate_id:
        raise ValueError('reference final checkpoint lacks its exact custody record')
    step = study.read(folder / (REFERENCE_STEM+'.json'))
    if (step['reply']['operation']['action'] != 'submit'
            or not step['outcome']['operations'][0]['result']['accepted']
            or step['outcome']['operations'][0]['result'] != state['pairs'][-1]['result']
            or step['after_view'] != session.view()):
        raise ValueError('reference saved submission effects differ')
    check = state['pairs'][-2]
    if (check['response']['action'] != 'check' or check['response']['check_id'] != 'public'
            or not check['result']['executed'] or not check['result']['passed']
            or check['result']['checked_candidate_id'] != candidate.candidate_id
            or check['result']['check_definition_sha256'] != study.PUBLIC_SHA):
        raise ValueError('reference lacks the actual current unchanged public pass')
    ObservationStore(branch / 'observations', replay=True).execute(candidate, study.public_checker(),
        'public', check['result']['observation'])
    authenticated = []
    for path, row in state['source_prerequisites']['coverage'].items():
        for witness in row['witnesses']:
            number = witness['request_number']
            actual = study.read(folder / f'scripted/import_boundaries/steps/{number:02d}.json')['before_view']
            if (sha256_bytes(canonical_json_bytes(actual)) != witness['presentation_sha256']
                    or actual['candidate_id'] != witness['candidate_id']
                    or actual['allowance']['requests_used'] != number-1
                    or actual['archive']['action_count'] != witness['archive_actions_before_request']):
                raise ValueError('reference coverage witness differs from its actual dispatch view')
            probe = session.clone()
            probe.candidate = session.versions[witness['candidate_id']]
            probe.pairs = copy.deepcopy(session.pairs[:witness['archive_actions_before_request']])
            spans = probe._verified_source_ranges(actual['working_set']['sources']
                + probe.feedback_sources(actual['latest_feedback']))
            if not any(s['path'] == path and s['start_line'] <= witness['start_line']
                    <= witness['end_line'] <= s['end_line'] for s in spans):
                raise ValueError('reference exact coverage bytes were not in the recorded dispatch')
            authenticated.append(dict(path=path, request=number,
                start_line=witness['start_line'], end_line=witness['end_line'],
                source_result_handle=witness['source_result_handle']))
    return candidate, state, session, candidate_path, state_path, raw_candidate, raw_state, dict(
        qualification_sha256=sha256_file(folder / 'QUALIFICATION.json'),
        actual_checkpoint=REFERENCE_STEM, restored_without_execution=True,
        reference_selection_is_evaluator_assisted=True, requests_used=13, operations_used=13,
        saved_dispatch_witnesses_authenticated=authenticated, model_inference_requests=0)


def probe_assessment(store, observation):
    assessment = dict(scope='supplemental_original_import_boundary_probe', frozen_original_grade_replaced=False,
        planned_cases=12, actual_rows_available=False, passed_cases=None, failed_cases=None,
        failed_case_inputs=None, observation=observation['observation'], capture_complete=observation['capture_complete'])
    if not observation['capture_complete']:
        return {**assessment, 'assessment_error': 'observation capture was incomplete'}
    try:
        rows = load_json_strict((store.directory(observation['observation']) / 'stdout.bin').read_bytes())
        keys = {'max_files', 'max_file_bytes', 'expected', 'actual', 'passed'}
        cells = [(b, n) for b in (0, 1, 5) for n in (0, 1, 2, 10)]
        eligible = {0: ['a.txt'], 1: ['a.txt', 'b.txt'], 5: ['a.txt', 'b.txt', 'c.txt']}
        if not isinstance(rows, list) or len(rows) != 12:
            raise ValueError('probe did not return exactly twelve cases')
        for row, (byte_limit, file_limit) in zip(rows, cells):
            expected = [{'path': p} for p in eligible[byte_limit][:file_limit]]
            if (not isinstance(row, dict) or set(row) != keys or type(row['max_files']) is not int
                    or type(row['max_file_bytes']) is not int or type(row['passed']) is not bool
                    or (row['max_file_bytes'], row['max_files']) != (byte_limit, file_limit)
                    or row['expected'] != expected or not isinstance(row['actual'], list)
                    or row['passed'] != (row['actual'] == expected)):
                raise ValueError('probe row shape, stated contract or verdict differs')
        passed = sum(row['passed'] for row in rows)
        if observation['returncode'] != (0 if passed == 12 else 1) or observation['passed'] != (passed == 12):
            raise ValueError('probe exit status and complete twelve-case assessment disagree')
        return {**assessment, 'actual_rows_available': True, 'passed_cases': passed,
            'failed_cases': 12-passed, 'failed_case_inputs': [
                {k: row[k] for k in ('max_files', 'max_file_bytes')} for row in rows if not row['passed']],
            'all_twelve_passed': passed == 12, 'rows': rows,
            'scope_limits': 'No negative-count requirement or complete package correctness is inferred.'}
    except (ValueError, KeyError, TypeError, UnicodeError) as problem:
        return {**assessment, 'assessment_error': str(problem)}


def evaluate(version='001', *, reference=False):
    if version != '001':
        raise ValueError('this declared evaluator supports version 001 only')
    folder = AREA / (('preparation-' if reference else 'run-') + version)
    seal_path = folder / ('SEAL.json' if reference else 'RESPONSE_SEAL.json')
    seal_raw, seal = seal_path.read_bytes(), study.read(seal_path)
    # Establish closure before creating output or starting evaluator execution.
    custody, records = verify_inventory(folder, seal, actor=not reference)
    out = AREA / 'review' / (('reference-evaluation-' if reference else 'evaluation-') + version)
    out.mkdir(exist_ok=False)
    source_files = {Path(__file__).resolve(): Path(__file__).read_bytes(), REPLAY: REPLAY.read_bytes(),
        PROBE: PROBE.read_bytes()}
    immutable = {seal_path: seal_raw}
    result = dict(status='evaluation_started', classification=('post_preparation_seal_reference_probe_only'
        if reference else 'post_response_seal_artifact_evaluation'), actor_feedback=False,
        additional_model_or_native_calls=False, hidden_execution_attempted=False,
        supplemental_execution_attempted=False, source_seal_sha256=sha256_bytes(seal_raw), custody=custody,
        evaluator_source_sha256=sha256_bytes(source_files[Path(__file__).resolve()]),
        saved_replay_helper_sha256=sha256_bytes(source_files[REPLAY]), original_probe_sha256=PROBE_SHA,
        evaluation_source_sha256={path.relative_to(study.ROOT).as_posix(): sha256_bytes(raw)
            for path, raw in source_files.items()},
        original_hidden_checker_sha256=study.HIDDEN_SHA, actor_grade_replaced=False)
    error = None
    try:
        if sha256_bytes(source_files[PROBE]) != PROBE_SHA:
            raise ValueError('original supplemental probe bytes changed')
        for path, label in ((Path(__file__).resolve(), 'EVALUATOR_SOURCE.py.txt'),
                           (REPLAY, 'REPLAY_HELPER.py.txt'), (PROBE, 'BOUNDARY_PROBE_ORIGINAL.py')):
            (out / label).write_bytes(source_files[path])
        (out / 'IMPLEMENTATION_SOURCES.json').write_bytes(canonical_json_bytes(seal['source_sha256']))
        if reference:
            candidate, state, session, candidate_path, state_path, raw_candidate, raw_state, proof = _reference(
                folder, seal, records)
            result['reference_checkpoint_verification'] = proof
        else:
            proof = _load_replay().verify(version)
            if proof['response_seal_sha256'] != sha256_bytes(seal_raw):
                raise ValueError('saved replay verified another response seal')
            (out / 'SAVED_RUN_VERIFICATION.json').write_bytes(canonical_json_bytes(proof))
            stem = 'final' if (folder / 'final-candidate.json').is_file() else 'stopped'
            candidate_path, state_path = folder / (stem+'-candidate.json'), folder / (stem+'-state.json')
            candidate, state, session, raw_candidate, raw_state = _restore(folder, candidate_path, state_path)
            result.update(actor_disposition=seal['disposition'], source_coverage=proof['source_coverage'])
        immutable.update({candidate_path: raw_candidate, state_path: raw_state})
        (out / 'EVALUATED_CANDIDATE.json').write_bytes(raw_candidate)
        (out / 'EVALUATED_STATE.json').write_bytes(raw_state)
        assessment = artifact_assessment(study.starting_candidate(), candidate)
        (out / 'ARTIFACT_ASSESSMENT.json').write_bytes(canonical_json_bytes(assessment))
        for index, diff in enumerate(assessment['diffs'].values(), 1):
            (out / f'diff-{index:02d}.patch').write_bytes(diff.encode())
        result.update(original_candidate_id=study.STARTING_ID, candidate_id=candidate.candidate_id,
            candidate_record=candidate_path.relative_to(folder).as_posix(),
            candidate_record_sha256=sha256_bytes(raw_candidate), state_record_sha256=sha256_bytes(raw_state),
            evaluated_submitted=state['submitted'], evaluated_requests_used=state['requests_used'],
            evaluated_operations_used=len(state['pairs']), coverage_checkpoint_restored=True,
            original_task_sha256=study.TASK_SHA, original_fixture_sha256=study.FIXTURE_SHA,
            original_public_checker_sha256=study.PUBLIC_SHA,
            evaluated_public_verification=session.verification_view(), artifact_assessment=assessment,
            limits=['Post-seal evaluator observations never enter actor input or replace the original grade.',
                'Complete source exposure proves delivery, not comprehension or semantic inspection.',
                'Twelve boundary cases and static API preservation are not a complete correctness proof.'])
        if not reference:
            hidden = study.hidden_checker()
            (out / 'HIDDEN_ORIGINAL.py').write_bytes(hidden)
            hidden_store = ObservationStore(out / 'hidden-observations')
            result['hidden_execution_attempted'] = True
            hidden_observation = hidden_store.execute(candidate, hidden, 'hidden', 'CHK-0001')
            result['hidden_observation'] = hidden_observation
            if hidden_observation.get('executed') is not True:
                raise ValueError('original hidden was not executed')
            if hidden_store.read('CHK-0001') != hidden_observation:
                raise ValueError('hidden exact observation readback differs')
            result['original_hidden_passed'] = hidden_observation['passed']
        boundary_store = ObservationStore(out / 'boundary-observations')
        result['supplemental_execution_attempted'] = True
        boundary = boundary_store.execute(candidate, source_files[PROBE], 'supplemental_import_boundaries', 'CHK-0001')
        result['supplemental_observation'] = boundary
        if boundary.get('executed') is not True:
            raise ValueError('original supplemental probe was not executed')
        if boundary_store.read('CHK-0001') != boundary:
            raise ValueError('supplemental exact observation readback differs')
        supplemental = probe_assessment(boundary_store, boundary)
        result['supplemental_assessment'] = supplemental
        (out / 'BOUNDARY_ASSESSMENT.json').write_bytes(canonical_json_bytes(supplemental))
        all_passed = supplemental.get('all_twelve_passed') is True
        preservation = (assessment['all_23_other_files_byte_identical']
            and assessment['all_existing_callable_interfaces_and_public_constants_preserved'])
        result.update(status=('reference_probe_12_of_12' if all_passed else 'reference_probe_contract_open')
            if reference else ('post_seal_checks_and_static_preservation_passed'
                if all_passed and result['original_hidden_passed'] and preservation
                else 'post_seal_contract_open'), supplemental_passed=all_passed,
            artifact_preservation_passed=preservation, direct_semantic_artifact_review_required=True)
    except BaseException as problem:
        error = problem
        result.update(status='evaluation_failed_preserved', error_type=type(problem).__name__,
            error=str(problem), traceback=traceback.format_exc())
    finally:
        try:
            if any(path.read_bytes() != raw for path, raw in immutable.items()):
                raise ValueError('sealed records changed during evaluation')
            if any(path.read_bytes() != raw for path, raw in source_files.items()):
                raise ValueError('evaluator, replay or original probe source changed')
            verify_inventory(folder, seal, actor=not reference)
            result['immutable_sealed_records_unchanged'] = True
        except BaseException as problem:
            result['immutable_sealed_records_unchanged'] = False
            result['preservation_error'] = str(problem)
            if error is None:
                error = problem
                result.update(status='evaluation_failed_preserved', error_type=type(problem).__name__,
                    error=str(problem), traceback=traceback.format_exc())
        if error is not None:
            (out / 'FAILED.json').write_bytes(canonical_json_bytes(result))
        (out / 'RESULT.json').write_bytes(canonical_json_bytes(result))
        inventory = [dict(path=p.relative_to(out).as_posix(), size_bytes=p.stat().st_size,
            sha256=sha256_file(p)) for p in sorted(out.rglob('*')) if p.is_file()]
        (out / 'SEAL.json').write_bytes(canonical_json_bytes(dict(classification=result['classification'],
            source_seal_sha256=sha256_bytes(seal_raw), evaluator_source_sha256=result['evaluator_source_sha256'],
            saved_replay_helper_sha256=result['saved_replay_helper_sha256'], original_probe_sha256=PROBE_SHA,
            evaluation_source_sha256=result['evaluation_source_sha256'],
            implementation_source_sha256=seal['source_sha256'], artifacts=inventory,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(inventory)))))
    if error is not None:
        raise error
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--version', choices=('001',))
    modes.add_argument('--reference-version', choices=('001',))
    args = parser.parse_args()
    print(json.dumps(evaluate(args.reference_version or args.version,
        reference=args.reference_version is not None), ensure_ascii=False, indent=2))
