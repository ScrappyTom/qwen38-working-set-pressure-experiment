"""Exact closed E19 replay through existing saved-data cores; no execution."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap
import ecological_task as study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

REFERENCE_CORE = study.ROOT / 'development/decision_interface/reference_repair/verify_reference.py'
STRONG_CORE = study.ROOT / 'development/workload_requalification/url_port_entry/review/verify_run.py'
CAPTURE_CORE = study.ROOT / 'development/workload_requalification/compiler_entry/review/verify_run.py'


def _load(name, path, alias):
    # The reused files import a task name at module scope. Supply this exact
    # ecological task without constructing any other task or changing a file.
    spec = importlib.util.spec_from_file_location(name, path)
    core = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {alias: study}):
        spec.loader.exec_module(core)
    return core


def _preparation(module, seal, inventory):
    run, preparation = module.RUN, module.PACKAGE
    manifest = study.read(run / 'EXECUTION_MANIFEST.json')
    assert manifest['source_sha256'] == seal['source_sha256'] == module.source_identities()
    module.verify_sources(manifest['source_sha256'])
    assert manifest['actor'] == seal['actor'] == module.ACTOR and manifest['seed'] == module.SEED
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (24, 72)
    assert manifest['starting_candidate_id'] == module.STARTING_ID and manifest['starting_archive_operations'] == 0
    assert manifest['original_entry'] and manifest['selection_assistance'] == 'none; fresh empty selected group'
    assert manifest['literal_source_reply'] and manifest['no_live_coaching'] and not manifest['automatic_retry']
    assert manifest['automatic_edit_checks'] == {}
    assert manifest['source_exposure_policy'] == study.exposure_policy()
    assert manifest['checker_contracts'] == {'public': {'checker_sha256': study.PUBLIC_SHA}}
    assert manifest['hidden_evaluation'] == 'after_response_seal_only'
    assert manifest['imported_observation_bindings'] == study.original_observation_state()
    assert manifest['imported_capture_retention'] == 'retain-requested-immutable-captures-v1'
    assert module.MANIFEST.read_bytes() == (run / 'EXECUTION_MANIFEST.json').read_bytes()
    assert sha256_file(preparation / 'SEAL.json') == manifest['preparation_seal_sha256']
    proof = study.read(preparation / 'SEAL.json')
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    assert proof['source_sha256'] == manifest['source_sha256']
    inventory(preparation, proof)
    qualification = study.read(preparation / 'QUALIFICATION.json')
    assert qualification['status'] == 'qualified' and qualification['completion_requests'] == 0
    assert qualification['entry_unchanged_after_qualification'] and qualification['route']['submitted']
    assert qualification['initial'] == manifest['initial'] and qualification['native_forms']['status'] == 'passed'
    first = run / 'calls/C01-wire-request.json'
    if first.exists():
        assert first.read_bytes() == (preparation / 'initial-wire-request.json').read_bytes()
        assert sha256_file(first) == manifest['initial']['wire_request_sha256']
    return manifest


def _reference_shape_supported(run):
    """The older core has no malformed-endpoint-shape branch; never normalize it."""
    for path in (run / 'calls').glob('*-endpoint-response.json'):
        try:
            value = study.read(path)
            choices = value['choices']
            if not isinstance(choices, list) or len(choices) != 1:
                return False
            choice = choices[0]
            if not isinstance(choice, dict) or not isinstance(choice.get('message'), dict):
                return False
            if 'finish_reason' not in choice:
                return False
            tag = path.name.removesuffix('-endpoint-response.json')
            if not all((run / 'calls' / (tag + '-assistant-' + suffix + '.txt')).is_file()
                       for suffix in ('content', 'reasoning')):
                return False
            if any(choice['message'].get(k) is not None and not isinstance(choice['message'][k], str)
                   for k in ('content', 'reasoning_content')):
                return False
        except (ValueError, TypeError, KeyError):
            return False
    return True


def _exposure_wires(module, ending):
    """Authenticate ledger witnesses with dispatched wires, not stored status."""
    session = module.restore(ending, module.candidate_from_snapshot(study.read(module.RUN /
            ('final-candidate.json' if (module.RUN / 'final-candidate.json').exists()
             else 'stopped-candidate.json'))), module.RUN, replay=True)
    state = ending['source_prerequisites']
    witnesses = []
    for path, witness in state['exposures'].items():
        tag = f"C{witness['request_number']:02d}"
        wire = study.read(module.RUN / f'calls/{tag}-wire-request.json')
        shown = load_json_strict(wire['messages'][1]['content'])['workspace']
        assert sha256_bytes(canonical_json_bytes(shown)) == witness['presentation_sha256']
        assert shown['candidate_id'] == witness['candidate_id']
        assert shown['allowance']['requests_used'] == witness['request_number'] - 1
        assert shown['archive']['action_count'] == witness['archive_actions_before_request']
        probe = session.clone()
        probe.candidate = session.versions[witness['candidate_id']]
        probe.pairs = copy.deepcopy(session.pairs[:witness['archive_actions_before_request']])
        sources = copy.deepcopy(shown['working_set']['sources'])
        pages = list(shown['working_set']['saved_results'])
        feedback = shown['latest_feedback']
        if feedback:
            receipt = feedback['result']
            pages.extend(receipt.get('saved_results', []))
            if receipt.get('kind') == 'saved_bytes':
                pages.append(receipt)
        for page in pages:
            sources.extend(probe._archived_sources_visible(page))
        spans = probe._verified_source_ranges(sources)
        assert any(span['path'] == path and span['start_line'] <= witness['start_line']
                   and span['end_line'] >= witness['end_line'] for span in spans)
        content = probe.source(dict(path=path, start_line=witness['start_line'],
                                    end_line=witness['end_line']))['content'].encode()
        assert content and len(content) == witness['size_bytes']
        assert sha256_bytes(content) == witness['content_sha256']
        assert study.policy._origin(probe, path, witness['file_sha256'],
            witness['start_line'], witness['end_line'], content.decode()) == witness['source_result_handle']
        witnesses.append(dict(path=path, request=tag, start_line=witness['start_line'],
            end_line=witness['end_line'], bytes=witness['size_bytes'],
            actual_wire_sha256=sha256_file(module.RUN / f'calls/{tag}-wire-request.json'),
            source_result_handle=witness['source_result_handle']))
    boundary = state['first_mutation']
    if boundary is not None:
        assert len(witnesses) == len(study.REQUIRED_INSPECTION_PATHS)
        tag = f"C{boundary['request_number']:02d}"
        reply = study.read(module.RUN / f'calls/{tag}-reply.json')
        assert reply['operation']['action'] in session.mutation_actions
        operations = study.read(module.RUN / f'calls/{tag}-host-result.json')['operations']
        assert any(row['result'].get('source_prerequisite_boundary') == boundary for row in operations)
    return dict(dispatched_source_witnesses=witnesses, first_mutation=boundary,
        exposure_is_not_comprehension=True, all_saved_witnesses_authenticated_against_actual_wires=True)


def verify(version='001'):
    module = study.Task(version)
    if not (module.RUN / 'RESPONSE_SEAL.json').is_file():
        raise ValueError('Do not replay an open model run')
    strong = _load('ecological_closed_strong_replay', STRONG_CORE, 'url_task')
    strong.study = study
    strong._preparation = lambda current, seal: _preparation(current, seal, strong._inventory)
    # The reused strong core supplies exact wire/native request binding, public
    # final validation, actual receipt replay, typed restore of every checkpoint,
    # version/check/raw-observation binding, counters and runtime closure.
    with patch('working_set_exp.observations.subprocess.Popen',
               side_effect=AssertionError('checker execution is prohibited during replay')):
        result = strong.verify(version)
        reference_used = _reference_shape_supported(module.RUN)
        if reference_used:
            core = _load('ecological_closed_reference_replay', REFERENCE_CORE, 'reference_task')
            class Shim:
                def Task(self, replay_folder=None):
                    return study.Task(version, replay_folder=replay_folder)
                def __getattr__(self, name):
                    return getattr(study, name)
            core.study, core.runner = Shim(), strong._runner()
            original = core.verify(module.RUN)
            for key in ('completed_replies', 'requests_used', 'actual_operations', 'native_inputs',
                        'custody_records', 'submitted', 'source_files', 'observations_replayed_without_execution'):
                assert original[key] == result[key], 'reused replay cores disagree: ' + key
    result.update(response_seal_sha256=sha256_file(module.RUN / 'RESPONSE_SEAL.json'),
        records_sha256=sha256_file(module.RUN / 'records.jsonl'),
        verification_source_sha256=sha256_file(Path(__file__)),
        strong_replay_core_sha256=sha256_file(STRONG_CORE),
        reference_replay_core_sha256=sha256_file(REFERENCE_CORE),
        reference_core_replayed=reference_used,
        reference_core_scope='Unchanged reference core on supported endpoint shapes with both actually saved extracted files; other stopped response shapes are verified by the stronger existing core without normalizing recorded evidence.',
        entry='fresh_original_E19_OBS_SUMMARY_GRAPH_declared_source_exposure_policy',
        hidden_evaluator_not_executed=True,
        named_source_inspection_and_semantic_artifact_review_required=True)
    # Reuse the per-record capture byte inspectors, not the compiler outer
    # verifier's three-record/equal-candidate assumptions. The legacy passing
    # distractor is legitimately bound to a different candidate here.
    capture = _load('ecological_observation_byte_inspectors', CAPTURE_CORE, 'compiler_task')
    session = module.initial_session()
    expected = study.original_observation_state()
    ending = study.read(module.RUN / ('final-state.json' if (module.RUN / 'final-state.json').exists()
                                     else 'stopped-state.json'))
    result.update(source_exposure=_exposure_wires(module, ending))
    assert ending['original_observation_state'] == expected
    assert ending['imported_capture_state'] == study.snapshot(session)['imported_capture_state']
    _, inventory, bodies = study.imports()
    assert (module.RUN / 'imported-captures/original-fixture.json').read_bytes() == study.exact(
        study.EXECUTION_ONLY / 'FIXTURE.json', study.FIXTURE_SHA)
    assert (module.RUN / 'imported-captures/original-verifier-rows.json').read_bytes() == canonical_json_bytes(expected['rows'])
    assert (module.RUN / 'imported-captures/transport-normalization.json').read_bytes() == canonical_json_bytes(expected['transport_normalization'])
    assert (module.RUN / 'imported-captures/transport-inventory.json').read_bytes() == canonical_json_bytes(inventory)
    for handle, body in bodies.items():
        assert (module.RUN / ('imported-captures/' + handle + '.json')).read_bytes() == body
    acquisitions, presentations = [], []
    for index, pair in enumerate(ending['pairs'], 1):
        if pair['response'].get('action') == 'reopen_observation':
            handle = capture._check_capture_receipt(pair['result'], inventory, bodies) if pair['result'].get('accepted') else None
            acquisitions.append(dict(sequence=index, handle=pair['response']['handle'],
                accepted=pair['result'].get('accepted'), bound_capture_verified=handle is not None))
    for path in sorted((module.RUN / 'calls').glob('*-wire-request.json')):
        request = study.read(path)
        envelope = load_json_strict(request['messages'][1]['content'])
        shown = capture._sent_capture_bytes(envelope, ending['pairs'], inventory, bodies)
        presentations.append(dict(request_file=path.relative_to(module.RUN).as_posix(),
                                  actual_capture_bytes_shown=shown))
    result.update(imported_observation_bindings_unchanged=True,
        capture_inspection_source_sha256=sha256_file(CAPTURE_CORE),
        imported_acquisitions=acquisitions, capture_presentations=presentations,
        capture_delivery_does_not_establish_interpretation=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or Path(__file__).with_name('VERIFICATION-' + args.version + '.json')
    try:
        value = verify(args.version)
    except BaseException as error:
        failure = output.with_name(output.stem + '-FAILED.json')
        raw = canonical_json_bytes(dict(status='verification_failed', type=type(error).__name__,
            message=str(error), traceback=traceback.format_exc(),
            verification_source_sha256=sha256_file(Path(__file__))))
        if failure.exists():
            assert failure.read_bytes() == raw, 'Preserve differing verification failures separately'
        else:
            failure.parent.mkdir(parents=True, exist_ok=True)
            failure.write_bytes(raw)
        raise
    raw = canonical_json_bytes(value)
    if output.exists():
        assert output.read_bytes() == raw, 'Existing verification differs; preserve it'
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
    print(json.dumps(value, indent=2))
