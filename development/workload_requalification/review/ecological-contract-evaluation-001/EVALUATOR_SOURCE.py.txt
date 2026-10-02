"""Separate post-seal evaluation of the E20 contract-completion continuation.

Requires the closed response seal and exact saved-data verification proof before
creating evaluation output or executing either evaluator program. This helper is
outside the frozen task closure. Execution still requires parent authorization.
No results enter actor feedback; neither old grades nor live checks are replaced.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
AREA = ROOT / 'development/workload_requalification/ecological_contract_continuation'
sys.path.insert(0, str(AREA))
import continuation_task as study
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

REPLAY = AREA / 'review/verify_run.py'
ORIGINAL_EVALUATOR = ROOT / 'development/workload_requalification/ecological_import_entry/review/evaluate_artifact.py'
PROBE = ROOT / 'maintenance/resume_after_020/import_boundary_probe.py'
PROBE_SHA = 'b5a2ac3f21015dd15212a7fda5c99329cac3199a736d491e9d2c02be54a7c8b6'
HIDDEN_SHA = '1ca34b6fc7b4c89bd42310a577fa176eab40f1ad30268984acd5b57f1b8ffe9d'
TARGETS = (study.previous.TARGET, study.previous.SAVED_RUNS)


def _within(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('noncanonical sealed artifact address')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path.relative_to(root.resolve()).as_posix() != relative:
        raise ValueError('sealed artifact address escapes or aliases its root')
    return path


def _inventory(folder, seal, *, current):
    rows, names = seal['files'], set()
    if sha256_bytes(canonical_json_bytes(rows)) != seal['aggregate_sha256']:
        raise ValueError('response seal inventory differs')
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
    if current and seal['source_sha256'] != study.source_identities():
        raise ValueError('sealed continuation source closure differs')
    records = verify_records(folder / 'records.jsonl', folder)
    closed = [record['payload'] for record in records if record['record_type'] == 'runtime_closed']
    if (len(records) != seal['record_count'] or len(closed) != 1
            or not closed[0]['owned_server_shutdown_verified']
            or not closed[0]['dedicated_port_free'] or not seal['port_free']):
        raise ValueError('sealed custody or owned runtime closure differs')
    return dict(sealed_files=len(names), source_files=len(seal['source_sha256']),
        custody_records=len(records), records_sha256=sha256_file(folder / 'records.jsonl'),
        owned_runtime_closed=True)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _original_evaluator():
    # The existing evaluator's artifact/probe functions use the original E20
    # Task and exact original 25-file entry; no evaluation entrypoint is invoked.
    with patch.dict(sys.modules, {'ecological_task': study.previous}):
        return _load(ORIGINAL_EVALUATOR, 'original_e20_artifact_functions_for_contract_evaluation')


def _proof(folder, seal_raw, seal, version):
    path = AREA / 'review' / ('VERIFICATION-' + version + '.json')
    if not path.is_file():
        raise ValueError('Exact continuation VERIFICATION proof is required before evaluation')
    raw = path.read_bytes()
    proof = load_json_strict(raw)
    if (proof.get('status') != 'replayed_exactly' or not proof.get('every_saved_checkpoint_restored')
            or not proof.get('source_closure_and_preparation_verified')
            or not proof.get('owned_runtime_closed')
            or not all(proof.get(key) is True for key in ('no_additional_checker_execution',
                'no_additional_model_inference', 'no_additional_tokenization'))
            or proof.get('response_seal_sha256') != sha256_bytes(seal_raw)
            or proof.get('records_sha256') != sha256_file(folder / 'records.jsonl')
            or proof.get('executed_manifest_sha256') != sha256_file(folder / 'EXECUTION_MANIFEST.json')
            or proof.get('verification_source_sha256') != sha256_file(REPLAY)
            or proof.get('original_run_seal_sha256') != study.OLD_SEAL
            or proof.get('inherited_requests') != 19 or proof.get('inherited_operations') != 28
            or proof.get('cumulative_requests') != seal['cumulative_requests_used']
            or proof.get('cumulative_operations') != seal['actual_operations']):
        raise ValueError('Continuation verification proof does not bind this closed attempt')
    helper = _load(REPLAY, 'closed_ecological_contract_replay_for_evaluation')
    # Exact replay consumes only saved native counts and observations. Prohibit
    # process execution even if an incorrectly configured replay attempted it.
    with patch('working_set_exp.observations.subprocess.Popen',
               side_effect=AssertionError('Checker execution is forbidden during saved replay')):
        replayed = helper.verify(version)
    if canonical_json_bytes(replayed) != raw:
        raise ValueError('Stored continuation verification proof differs from exact replay')
    return path, raw, proof


def _ending(folder, proof):
    stem = 'final' if (folder / 'final-state.json').is_file() else 'stopped'
    candidate_path, state_path = folder / (stem + '-candidate.json'), folder / (stem + '-state.json')
    candidate_raw, state_raw = candidate_path.read_bytes(), state_path.read_bytes()
    candidate = study.previous.candidate_from_snapshot(load_json_strict(candidate_raw))
    state = load_json_strict(state_raw)
    if (study.candidate_bytes(candidate) != candidate_raw
            or candidate.candidate_id != state['candidate_id']
            or candidate.candidate_id != proof['final_candidate_id']
            or state['requests_used'] != proof['cumulative_requests']
            or len(state['pairs']) != proof['cumulative_operations']
            or state['submitted'] is not proof['submitted']):
        raise ValueError('Evaluated ending candidate or checkpoint does not bind replay')
    session = study.restore(state, candidate, folder, replay=True)
    if canonical_json_bytes(study.snapshot(session)) != canonical_json_bytes({**state, 'diffs': session.diffs}):
        raise ValueError('Exact continuation and continuous-coverage reconstruction differs')
    return candidate, state, session, candidate_path, state_path, candidate_raw, state_raw


def evaluate(version='001'):
    if version != '001':
        raise ValueError('This declared evaluator supports continuation version001 only')
    folder = AREA / ('run-' + version)
    seal_path = folder / 'RESPONSE_SEAL.json'
    out = Path(__file__).resolve().parent / ('ecological-contract-evaluation-' + version)
    if not seal_path.is_file():
        raise ValueError('Do not evaluate an open continuation; RESPONSE_SEAL is required')
    if out.exists():
        raise ValueError('Existing evaluation is preserved; output folder already exists')
    seal_raw, seal = seal_path.read_bytes(), study.read(seal_path)
    # All gates precede directory creation and evaluator subprocess execution.
    custody = _inventory(folder, seal, current=True)
    old_seal_path = study.OLD / 'RESPONSE_SEAL.json'
    old_seal_raw = old_seal_path.read_bytes()
    if sha256_bytes(old_seal_raw) != study.OLD_SEAL:
        raise ValueError('Inherited original response seal changed')
    inherited_custody = _inventory(study.OLD, study.read(old_seal_path), current=False)
    proof_path, proof_raw, proof = _proof(folder, seal_raw, seal, version)
    candidate, state, session, candidate_path, state_path, candidate_raw, state_raw = _ending(folder, proof)
    original = _original_evaluator()
    probe, hidden = PROBE.read_bytes(), study.previous.hidden_checker()
    if sha256_bytes(probe) != PROBE_SHA or sha256_bytes(hidden) != HIDDEN_SHA:
        raise ValueError('Original evaluator program bytes changed')
    source_files = {Path(__file__).resolve(): Path(__file__).read_bytes(), REPLAY: REPLAY.read_bytes(),
        ORIGINAL_EVALUATOR: ORIGINAL_EVALUATOR.read_bytes(), PROBE: probe,
        study.previous.EVALUATOR_ONLY / 'hidden.py': hidden}
    immutable = {seal_path: seal_raw, old_seal_path: old_seal_raw, proof_path: proof_raw,
        candidate_path: candidate_raw, state_path: state_raw}
    out.mkdir(exist_ok=False)
    result = dict(status='evaluation_started', classification='independent_post_seal_contract_completion_evaluation',
        actor_feedback=False, actor_grade_replaced=False, original_grades_replaced=False,
        live_checker_results_replaced=False, additional_model_or_native_calls=False,
        hidden_execution_attempted=False, supplemental_execution_attempted=False,
        source_seal_sha256=sha256_bytes(seal_raw), inherited_response_seal_sha256=study.OLD_SEAL,
        custody=custody, inherited_custody=inherited_custody,
        evaluator_source_sha256=sha256_bytes(source_files[Path(__file__).resolve()]),
        saved_replay_helper_sha256=sha256_bytes(source_files[REPLAY]),
        verification_proof_sha256=sha256_bytes(proof_raw),
        evaluation_source_sha256={path.relative_to(ROOT).as_posix(): sha256_bytes(raw)
            for path, raw in source_files.items()}, original_hidden_checker_sha256=HIDDEN_SHA,
        original_probe_sha256=PROBE_SHA, registered_actor_checker_sha256=study.PUBLIC_SHA,
        registered_actor_scope=study.contract_checker.SCOPE)
    error = None
    try:
        for path, label in ((Path(__file__).resolve(), 'EVALUATOR_SOURCE.py.txt'),
                (REPLAY, 'REPLAY_HELPER.py.txt'), (ORIGINAL_EVALUATOR, 'ORIGINAL_EVALUATOR_HELPER.py.txt'),
                (PROBE, 'BOUNDARY_PROBE_ORIGINAL.py'),
                (study.previous.EVALUATOR_ONLY / 'hidden.py', 'HIDDEN_ORIGINAL.py')):
            (out / label).write_bytes(source_files[path])
        for label, raw in (('SOURCE_RESPONSE_SEAL.json', seal_raw),
                ('ORIGINAL_RESPONSE_SEAL.json', old_seal_raw), ('VERIFICATION_PROOF.json', proof_raw),
                ('EXECUTED_MANIFEST.json', (folder / 'EXECUTION_MANIFEST.json').read_bytes()),
                ('EVALUATED_CANDIDATE.json', candidate_raw), ('EVALUATED_STATE.json', state_raw)):
            (out / label).write_bytes(raw)
        (out / 'IMPLEMENTATION_SOURCES.json').write_bytes(canonical_json_bytes(seal['source_sha256']))
        assessment = original.artifact_assessment(study.previous.starting_candidate(), candidate)
        assessment['exactly_two_original_target_paths_changed'] = assessment['changed_paths'] == sorted(TARGETS)
        inherited = study.previous.candidate_from_snapshot(load_json_strict(study.inherited_bytes('final-candidate.json')))
        assessment['continuation_changed_paths'] = sorted(path for path in candidate.file_map
            if inherited.file_map[path] != candidate.file_map[path])
        (out / 'ARTIFACT_ASSESSMENT.json').write_bytes(canonical_json_bytes(assessment))
        for number, diff in enumerate(assessment['diffs'].values(), 1):
            (out / f'diff-{number:02d}.patch').write_bytes(diff.encode('utf-8'))
        verification = session.verification_view()
        scoped_submission = bool(state['submitted'] and verification['submission']['eligible']
            and session.check_state() and session.check_state()['passed']
            and session.check_state()['applies_to_current'])
        result.update(actor_disposition=seal['disposition'], candidate_id=candidate.candidate_id,
            original_candidate_id=study.previous.STARTING_ID, continuation_entry_candidate_id=study.SAVED_ID,
            candidate_record=candidate_path.relative_to(folder).as_posix(),
            candidate_record_sha256=sha256_bytes(candidate_raw), state_record_sha256=sha256_bytes(state_raw),
            evaluated_requests_used=state['requests_used'], evaluated_operations_used=len(state['pairs']),
            evaluated_submitted=state['submitted'], scoped_checked_submission=scoped_submission,
            evaluated_public_verification=verification, coverage_checkpoint_restored=True,
            source_coverage=proof['source_coverage'], artifact_assessment=assessment,
            limits=['Independent observations never enter actor input or replace original or live grades.',
                'A registered-scope submission and independent contract case results are separate outcomes.',
                'Static interfaces and unchanged bytes do not prove all semantic preservation.',
                'The original hidden and twelve boundary cases are finite checks, not a universal correctness proof.',
                'Historical dispatched coverage proves source delivery, not comprehension or current editing authority.'])
        hidden_store = ObservationStore(out / 'hidden-observations')
        result['hidden_execution_attempted'] = True
        hidden_observation = hidden_store.execute(candidate, hidden, 'original_hidden', 'CHK-0001')
        result['hidden_observation'] = hidden_observation
        if hidden_observation.get('executed') is not True or hidden_store.read('CHK-0001') != hidden_observation:
            raise ValueError('Original hidden exact execution or observation readback differs')
        result['original_hidden_passed'] = hidden_observation['passed']
        probe_store = ObservationStore(out / 'boundary-observations')
        result['supplemental_execution_attempted'] = True
        boundary = probe_store.execute(candidate, probe, 'independent_original_import_boundary_probe', 'CHK-0001')
        result['supplemental_observation'] = boundary
        if boundary.get('executed') is not True or probe_store.read('CHK-0001') != boundary:
            raise ValueError('Original boundary probe exact execution or observation readback differs')
        supplemental = original.probe_assessment(probe_store, boundary)
        result['supplemental_assessment'] = supplemental
        (out / 'BOUNDARY_ASSESSMENT.json').write_bytes(canonical_json_bytes(supplemental))
        preservation = (assessment['all_23_other_files_byte_identical']
            and assessment['exactly_two_original_target_paths_changed']
            and assessment['all_existing_callable_interfaces_and_public_constants_preserved'])
        passed = bool(hidden_observation['passed'] and supplemental.get('all_twelve_passed') is True and preservation)
        result.update(status='post_seal_checks_and_static_preservation_passed' if passed else 'post_seal_contract_open',
            independent_checked_cases_and_preservation_passed=passed,
            scoped_submission_and_independent_checks_passed=scoped_submission and passed,
            artifact_preservation_passed=preservation,
            direct_semantic_artifact_review_required=True)
    except BaseException as problem:
        error = problem
        result.update(status='evaluation_failed_preserved', error_type=type(problem).__name__,
            error=str(problem), traceback=traceback.format_exc())
    finally:
        try:
            if any(path.read_bytes() != raw for path, raw in immutable.items()):
                raise ValueError('Sealed run, checkpoint or verification changed during evaluation')
            if any(path.read_bytes() != raw for path, raw in source_files.items()):
                raise ValueError('Evaluator/helper/original program source changed during evaluation')
            _inventory(folder, seal, current=True)
            _inventory(study.OLD, study.read(old_seal_path), current=False)
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
        inventory = [dict(path=path.relative_to(out).as_posix(), size_bytes=path.stat().st_size,
            sha256=sha256_file(path)) for path in sorted(out.rglob('*')) if path.is_file()]
        (out / 'SEAL.json').write_bytes(canonical_json_bytes(dict(classification=result['classification'],
            source_seal_sha256=sha256_bytes(seal_raw), inherited_response_seal_sha256=study.OLD_SEAL,
            evaluator_source_sha256=result['evaluator_source_sha256'],
            saved_replay_helper_sha256=result['saved_replay_helper_sha256'],
            verification_proof_sha256=result['verification_proof_sha256'],
            evaluation_source_sha256=result['evaluation_source_sha256'],
            implementation_source_sha256=seal['source_sha256'], artifacts=inventory,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(inventory)))))
    if error is not None:
        raise error
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=('001',), required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.version), ensure_ascii=False, indent=2))
