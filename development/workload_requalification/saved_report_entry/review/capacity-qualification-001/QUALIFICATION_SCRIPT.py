"""Supplemental native sizing only, from an exact sealed saved-report checkpoint.

The three decisions are evaluator-selected transition tests, not model behavior.
No setup, check, edit, submission, or model-completion request is sent. The main
preparation and its source closure remain unchanged. Run only under the parent's
exclusive runtime ownership after review; each output folder is single-use.
"""
import argparse
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import bootstrap
import saved_report_task as study
import run_saved_report as execution
import qualification_route
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

INPUT_LIMIT = 23808
CHECKPOINT = 'scripted/malformed_then_corrected/states/04.json'
REPLAY_BRANCH = 'scripted/malformed_then_corrected'
CLASSIFICATION = 'evaluator-selected supplemental capacity transition; no model inference'


def frozen_selection(session):
    """The rejection must preserve these work designations and actual work."""
    return canonical_json_bytes(dict(candidate=study.candidate_bytes(session.candidate).decode(),
        ranges=session.ranges, saved=session.saved, account=session.working_account(),
        check=session.check_state(), diffs=session.diffs))


def observation_files(session):
    return {path.relative_to(session.observations.root).as_posix(): sha256_file(path)
            for path in session.observations.root.rglob('*') if path.is_file()}


def qualify(output, version='001'):
    module = study.Task(version)
    manifest = execution.verify_package(module)
    main_seal = module.PACKAGE/'SEAL.json'
    original_seal_sha = sha256_file(main_seal)
    sealed_files = {row['path']: row for row in study.read(main_seal)['files']}
    assert CHECKPOINT in sealed_files, 'checkpoint must be in the sealed main preparation'
    checkpoint_path = module.PACKAGE/CHECKPOINT
    raw_state = checkpoint_path.read_bytes()
    assert sha256_bytes(raw_state) == sealed_files[CHECKPOINT]['sha256']
    state = load_json_strict(raw_state)
    candidate = next(row for row in state['source_versions']
                     if row['candidate_id'] == state['candidate_id'])
    session = module.restore(state, candidate, module.PACKAGE/REPLAY_BRANCH, replay=True)
    assert canonical_json_bytes(module.snapshot(session)) == canonical_json_bytes(state)
    assert session.phase_counters()['phase'] == 2 and session.requests_used == 4
    assert len(session.pairs) == 17 and session.phase_counters()['phase_requests_used'] == 2
    assert session.observations.replay is True and not session.recovery
    before_observations = observation_files(session)
    before_pairs = copy.deepcopy(session.pairs)
    before_account = copy.deepcopy(session.working_account())
    before_candidate = study.candidate_bytes(session.candidate)
    before_report = session.candidate.file_map['reports/incident.json']
    before_counters = copy.deepcopy(session.phase_counters())
    before_check = copy.deepcopy(session.check_state())
    assert before_check['passed'] is False and before_check['applies_to_current'] is True
    try:
        json.loads(before_report)
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError('sealed checkpoint must preserve the malformed partial report')

    reader = qualification_route.capture_reader
    initial_view = session.view()
    initial_bodies = reader.delivered_capture_bodies(initial_view)
    assert initial_bodies == {h: session.imported_record(h)[1]
                             for h in ('OBS-0001','OBS-0002','OBS-0003')}
    assert all(n == 1 for n in reader.displayed_capture_counts(initial_view).values())
    sources = reader.delivered_sources(initial_view)
    assert set(sources) == {'README.md','reports/incident.json'}
    assert all(row['content'].encode() == session.candidate.file_map[path]
               for path, row in sources.items())
    # These are real complete archived acquisition receipts, not invented text
    # padding. The five-address group intentionally retains duplicate original
    # and BUILD-A acquisitions. It tests capacity, not their semantic necessity.
    all_capture_handles = [f'RES-{number:04d}' for number, pair in enumerate(session.pairs,1)
        if pair['response'].get('action') == 'reopen_observation'
        and session._capture_identity(pair['result']) is not None]
    assert all_capture_handles == ['RES-0006','RES-0007','RES-0014','RES-0015','RES-0017']
    selected_capture_handles = {handle for handle, page in session.saved.items()
        if page['offset'] == 0 and page['next_offset'] is None
        and page['exact_utf8'].encode() == session.payload(handle)
        and session._capture_identity(load_json_strict(session.payload(handle))) is not None}
    assert selected_capture_handles == {'RES-0014','RES-0015','RES-0017'}
    requested_sources = [dict(path=path,start_line=row['returned_start_line'],end_line=row['returned_end_line'])
                         for path,row in sources.items()]

    script = Path(__file__).resolve()
    script_key = script.relative_to(study.ROOT).as_posix()
    assert script_key not in manifest['source_sha256'], 'supplement must remain outside frozen Task closure'
    bound = {**manifest['source_sha256'], script_key: sha256_file(script),
             main_seal.relative_to(study.ROOT).as_posix(): original_seal_sha}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(output)
    log = execution.legacy.QualificationLog(output/'records.jsonl',
        'saved-report-supplemental-capacity',task_module=module)
    log.append('sealed_checkpoint_restored',dict(classification=CLASSIFICATION,
        main_preparation_seal_sha256=original_seal_sha, checkpoint=CHECKPOINT,
        checkpoint_sha256=sha256_bytes(raw_state), phase_counters=before_counters,
        source_files=len(manifest['source_sha256']), completion_sent=False),
        [store.put('QUALIFICATION_SCRIPT.py',script.read_bytes()),
         store.put('MAIN_PREPARATION_SEAL.json',main_seal.read_bytes()),
         store.put('checkpoint.json',raw_state),
         store.put('checkpoint-candidate.json',before_candidate),
         store.put('checkpoint-observation-files.json',canonical_json_bytes(before_observations))])
    adapter = execution.runner.Adapter(module)
    rows, loop, outcome, error = [], None, None, None
    try:
        server,model,_ = module.runtime_paths()
        runtime = execution.RUNTIME
        with runtime.owned_runtime(SimpleNamespace(server=server,model=model,output=output),store,log) as url:
            loop = execution.PhaseLoop(output,store,log,url=url,task_module=adapter,
                source_check=lambda: module.verify_sources(bound))
            loop.snapshot(session,'before')

            def act(action,basis,accepted):
                assert action['action'] in {'work_on','selection_page','work_on_exact'}
                before = copy.deepcopy(session.view())
                count = loop.measure(before)
                assert count <= INPUT_LIMIT and session.phase_budget_available()
                session.mark_delivered(before)
                session.begin_request()
                reply = dict(discussion=basis,operation=action)
                host = module.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
                assert len(host['operations']) == 1 and host['executed'] is True
                result = host['operations'][0]['result']
                after = copy.deepcopy(session.view())
                following = loop.measure(after)
                row = dict(before_view=before,reply=reply,outcome=host,after_view=after,
                    input_tokens=count,next_input_tokens=following,
                    phase_counters=session.phase_counters(),classification=CLASSIFICATION,basis=basis)
                rows.append(row)
                log.append('scripted_transition',dict(number=len(rows),completion_sent=False,
                    input_tokens=count,next_input_tokens=following,phase_counters=session.phase_counters()),
                    [store.put(f'steps/{len(rows):02d}.json',canonical_json_bytes(row))])
                loop.snapshot(session,f'after/{len(rows):02d}')
                assert result.get('accepted') is accepted, result
                assert following <= INPUT_LIMIT and not session.delivery_blocked
                assert session.pairs[:len(before_pairs)] == before_pairs
                assert study.candidate_bytes(session.candidate) == before_candidate
                assert session.candidate.file_map['reports/incident.json'] == before_report
                assert session.working_account() == before_account
                assert session.setup_sequences == tuple(state['saved_report_state']['setup_sequences'])
                assert adapter.preceding_feedback == []
                return result

            preserved = frozen_selection(session)
            rejected = act(dict(action='work_on',sources=requested_sources,results=all_capture_handles),
                'Capacity regression using five actual archived capture acquisitions and the already displayed README/report extents; duplicate receipts are intentional evaluator-selected load.',False)
            assert session.recovery and frozen_selection(session) == preserved
            assert 'cannot be placed beside' in rejected.get('error',''), 'must be capacity rejection, not invalid references'
            assert not reader.delivered_capture_bodies(session.view())
            inventory = act(dict(action='selection_page',offset=0),
                'The delivered recovery view identifies a preserved selection. Request its mechanical source references and saved-record addresses without treating inventory as source.',True)
            assert inventory['inventory_is_not_source_content'] is True and inventory['next_offset'] is None
            entries = inventory['entries']
            regions = [row['region_ref'] for row in entries if row['kind']=='source']
            assert {row['path'] for row in entries if row['kind']=='source'} == set(sources)
            results = [row['handle'] for row in entries if row['kind']=='saved_record'
                       and row['handle'] in selected_capture_handles]
            assert set(results) == selected_capture_handles and len(regions) == 2
            assert session.recovery and frozen_selection(session) == preserved
            act(dict(action='work_on_exact',regions=regions,results=results),
                'Use only SRC references returned by selection_page and the three complete capture RES addresses shown before rejection; replace the overbroad attempted group while preserving saved work.',True)
            assert not session.recovery
            final_view = session.view()
            assert reader.delivered_capture_bodies(final_view) == initial_bodies
            assert all(n==1 for n in reader.displayed_capture_counts(final_view).values())
            final_sources = reader.delivered_sources(final_view)
            assert set(final_sources) == set(sources)
            assert all(row['content'].encode()==session.candidate.file_map[path]
                       for path,row in final_sources.items())
            assert set(session.saved) == selected_capture_handles
            assert session.check_state() == before_check
            assert observation_files(session) == before_observations
            assert session.requests_used == 7 and len(session.pairs) == 20
            assert session.phase_counters()['phase_requests_used'] == 5
            assert session.phase_counters()['phase_actor_operations_used'] == 5
            assert session.phase_counters()['assisted_operations_new'] == 9
            assert loop.sent == 0
            restored = module.restore(module.snapshot(session),session.candidate,module.PACKAGE/REPLAY_BRANCH,replay=True)
            assert canonical_json_bytes(module.snapshot(restored)) == canonical_json_bytes(module.snapshot(session))
            module.verify_sources(bound)
            loop.health()
            outcome = dict(completed=True,scripted_decisions=3,model_completion_requests=0,
                new_checks=0,new_setup_operations=0,candidate_and_report_unchanged=True,
                account_unchanged=True,initial_archive_prefix_unchanged=True,
                complete_capture_co_presence=True,selection_inventory_is_not_source=True,
                checkpoint_roundtrip=True,before_counters=before_counters,
                after_counters=session.phase_counters(),native_inputs=len(loop.cache),
                maximum_measured_proposal_input_tokens=max(row['prompt_tokens'] for row in loop.cache.values()),
                peak_admitted_input_tokens=max(max(row['input_tokens'],row['next_input_tokens']) for row in rows),
                classification=CLASSIFICATION,
                information_path_limit='The inventory supplies addresses/extents; capture identity is supported by the full initial input. The narrowing is evaluator-selected, not demonstrated Qwen selection.')
    except BaseException as exc:
        error = exc
        log.append('supplement_failed',dict(type=type(exc).__name__,message=str(exc),completion_sent=False),[])
        if loop is not None:
            loop.snapshot(session,'stopped')
    finally:
        assert sha256_file(main_seal) == original_seal_sha
        module.verify_sources(bound)
        records = verify_records(output/'records.jsonl',output)
        assert not any(row['record_type'] in {'invocation_started','response_received'} for row in records)
        study.save(output,'RESULTS.json',dict(status='failed_preserved' if error else 'qualified_no_model_inference',
            result=outcome,scripted_decisions_completed=len(rows),completion_requests=0,
            main_preparation_seal_sha256=original_seal_sha,checkpoint_sha256=sha256_bytes(raw_state),
            memory=execution.RUNTIME.memory_stats(output/'memory.csv'),
            port_free=execution.RUNTIME.port_free(execution.RUNTIME.PORT),record_count=len(records)))
        execution.legacy.seal(output,'failed_preserved' if error else 'qualified_no_model_inference',
            bound,completion_requests=0,main_preparation_seal_sha256=original_seal_sha,
            checkpoint_sha256=sha256_bytes(raw_state),classification=CLASSIFICATION)
    if error:
        raise error
    print(json.dumps(outcome,sort_keys=True),flush=True)
    return outcome


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='001')
    parser.add_argument('--output',type=Path,default=AREA/'review/capacity-qualification-001')
    args = parser.parse_args()
    qualify(args.output,args.version)
