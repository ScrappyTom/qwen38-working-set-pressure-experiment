"""Read-only replay of the interrupted prefix; never supplies a missing closure."""
import collections
import json
from pathlib import Path

import interpolation_task as study
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA = Path(__file__).resolve().parent
RUN = AREA.parent / 'run-002'


def inventory():
    return [dict(path=p.relative_to(RUN).as_posix(), size_bytes=p.stat().st_size,
                 sha256=sha256_file(p)) for p in sorted(RUN.rglob('*')) if p.is_file()]


def main():
    before = inventory()
    manifest = study.read(RUN / 'EXECUTION_MANIFEST.json')
    study.verify_sources(manifest['source_sha256'])
    records = verify_records(RUN / 'records.jsonl', RUN)
    module = study.Task(version='002', replay_folder=RUN)
    adapter, session = runner.Adapter(module), module.initial_session()
    counts = {}
    native_count = 0
    for record in records:
        if record['record_type'] != 'native_input_prepared':
            continue
        row = record['payload']; stem = row['stem']
        request = study.read(RUN / (stem + '-endpoint-request.json'))
        native = (RUN / (stem + '-native.txt')).read_bytes()
        assert native == adapter.expected_native(request)
        assert native == study.read(RUN / (stem + '-template.json'))['prompt'].encode()
        assert row['prompt_tokens'] == len(study.read(RUN / (stem + '-tokens.json'))['tokens'])
        assert (RUN / (stem + '-wire-request.json')).read_bytes() == completion_request_bytes(request)
        counts[sha256_bytes(canonical_json_bytes(request))] = row['prompt_tokens']
        native_count += 1

    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view))) ]

    assert canonical_json_bytes(module.snapshot(session)) == (RUN / 'starting-state.json').read_bytes()
    completed, dispatches = [], []
    last_state = None
    for record in records:
        if record['record_type'] != 'invocation_started':
            continue
        row = record['payload']; tag = row['id']; dispatches.append(tag)
        assert (RUN / f'calls/{tag}-wire-request.json').read_bytes() == completion_request_bytes(adapter.request_for(session.view()))
        assert measure(session.view()) == row['prompt_tokens']
        response_path = RUN / f'calls/{tag}-endpoint-response.json'
        if not response_path.exists():
            # Verify the dispatched input, but do not pretend this request completed.
            assert tag == 'C22'
            break
        session.mark_delivered(session.view()); session.begin_request()
        choice = study.read(response_path)['choices'][0]
        for field, suffix in (('content', 'content'), ('reasoning_content', 'reasoning')):
            assert (choice['message'].get(field) or '').encode() == (RUN / f'calls/{tag}-assistant-{suffix}.txt').read_bytes()
        assert choice['finish_reason'] == 'stop' and choice['message'].get('content', '').strip()
        reply = study.decode_reply(choice['message']['content'])
        assert reply == study.read(RUN / f'calls/{tag}-reply.json')

        def intermediate(number, operation):
            nonlocal last_state
            assert operation == study.read(RUN / f'calls/{tag}-operation-{number:02d}.json')
            stem = f'after/{tag}-O{number:02d}'
            assert canonical_json_bytes(module.snapshot(session)) == (RUN / (stem + '-state.json')).read_bytes()
            assert study.candidate_bytes(session.candidate) == (RUN / (stem + '-candidate.json')).read_bytes()
            last_state = stem

        result = adapter.process_reply(session, reply, measure, adapter.preceding_feedback, intermediate)
        assert result == study.read(RUN / f'calls/{tag}-host-result.json')
        completed.append(tag)
    assert completed == [f'C{x:02d}' for x in range(1, 22)]
    assert last_state == 'after/C21-O01'
    assert canonical_json_bytes(module.snapshot(session)) == (RUN / (last_state + '-state.json')).read_bytes()
    assert study.candidate_bytes(session.candidate) == (RUN / 'starting-candidate.json').read_bytes()
    observations = [r for r in records if r['record_type'] == 'check_observation_preserved']
    for record in observations:
        saved = session.observations.read(record['payload']['observation'])
        assert {k:record['payload'][k] for k in saved} == saved
    absent = ['RESPONSE_SEAL.json', 'final-state.json', 'final-candidate.json',
              'stopped-state.json', 'stopped-candidate.json', 'calls/C22-endpoint-response.json']
    assert all(not (RUN / name).exists() for name in absent)
    assert not any(r['record_type'] == 'runtime_closed' for r in records)
    invocations = [r['payload'] for r in records if r['record_type'] == 'invocation_completed']
    operations = [r['payload'] for r in records if r['record_type'] == 'contribution_operation']
    native_presented = [r['payload'] for r in records if r['record_type'] == 'invocation_started']
    operation_files = [study.read(p) for p in sorted((RUN/'calls').glob('*-operation-*.json'))]
    action_counts = collections.Counter(x['action']['action'] for x in operation_files)
    assert not any(action_counts[a] for a in ('patch', 'replace_region', 'submit'))
    candidate = study.read(RUN/'starting-candidate.json')
    files = {x['path']:x['content_utf8'] for x in candidate['files']}
    shown_source_extents_verified = 0
    for dispatched in native_presented:
        wire = study.read(RUN/f"calls/{dispatched['id']}-wire-request.json")
        view = json.loads(wire['messages'][1]['content'])['workspace']
        for source in view['working_set']['sources']:
            content = files[source['path']]
            assert source['candidate_id'] == candidate['candidate_id']
            assert source['file_sha256'] == sha256_bytes(content.encode())
            assert source['content'] == ''.join(content.splitlines(keepends=True)[source['returned_start_line']-1:source['returned_end_line']])
            shown_source_extents_verified += 1
    result = dict(
        classification='externally interrupted; complete recorded prefix replayed exactly',
        run_relative_to_repository=RUN.relative_to(study.ROOT).as_posix(),
        completed_reply_ids=completed, dispatched_request_ids=dispatches,
        missing_response='C22', missing_response_outcome='unknown',
        source_files_verified=len(manifest['source_sha256']), custody_records_verified=len(records),
        custody_tail_sha256=records[-1]['record_sha256'],
        custody_last_record_time_utc=records[-1]['created_at_utc'],
        native_inputs_verified=native_count, distinct_native_inputs=len(counts),
        recorded_artifact_references_verified=sum(len(r['artifacts']) for r in records),
        recorded_distinct_artifact_paths=len({a['path'] for r in records for a in r['artifacts']}),
        recorded_operations=len(operations), session_operations_used=session.calls_used,
        operation_counts=dict(action_counts), rejected_operations=sum(not x['result']['accepted'] for x in operation_files),
        dispatched_current_source_extents_verified=shown_source_extents_verified,
        last_committed_state=last_state+'-state.json',
        last_committed_candidate=last_state+'-candidate.json',
        last_committed_state_sha256=sha256_file(RUN/(last_state+'-state.json')),
        last_committed_candidate_sha256=sha256_file(RUN/(last_state+'-candidate.json')),
        candidate_id=session.candidate.candidate_id, candidate_exactly_unchanged=True,
        new_artifact_edits=0, new_submission=session.submitted,
        completed_prefix_requests_used=session.requests_used,
        conservative_remaining_requests=manifest['maximum_requests']-len(dispatches),
        remaining_operations=manifest['maximum_operations']-session.calls_used,
        preserved_observations_replayed_without_execution=len(observations),
        completed_request_seconds=sum(x['elapsed_seconds'] for x in invocations),
        completed_request_minutes=sum(x['elapsed_seconds'] for x in invocations)/60,
        completed_prompt_tokens=sum(x['usage']['prompt_tokens'] for x in invocations),
        completed_generated_tokens=sum(x['usage']['completion_tokens'] for x in invocations),
        peak_completed_input_plus_generation=max(x['usage']['total_tokens'] for x in invocations),
        peak_dispatched_prompt_tokens=max(x['prompt_tokens'] for x in native_presented),
        sampled_min_free_gpu_mib=min(x['memory']['min_free_mib'] for x in native_presented),
        last_dispatch_prompt_tokens=native_presented[-1]['prompt_tokens'],
        full_attempt_cost_known=False, runtime_closure_verified=False,
        normal_closure_record_exists=False, absent_closure_artifacts=absent,
        no_additional_model_inference=True, no_additional_checker_execution=True,
        record_type_counts=dict(collections.Counter(r['record_type'] for r in records)),
        limitations=['No preserved C22 response, usage or end time; its disposition is unknown.',
                     'No original response seal or normal runtime closure; this is a later audit snapshot.',
                     'Native request bytes are regenerated from pinned code and compared with saved native responses; tokenization is not rerun.',
                     'Successful replay establishes recorded transitions, not semantic truth of model accounts.',
                     'The unchanged initial candidate contains previously assisted work, not a fresh backport.'])
    assert inventory() == before, 'Audit must not alter any original run byte or add a run artifact'
    public = [x for x in before if not x['path'].startswith('private-runtime/')]
    private = [x for x in before if x['path'].startswith('private-runtime/')]
    seal = dict(schema='interrupted-run-retrospective-snapshot-v1', run=RUN.relative_to(study.ROOT).as_posix(),
                classification='retrospective inventory, not original execution closure',
                files=public, private_runtime_files_local_only=private,
                aggregate_sha256=sha256_bytes(canonical_json_bytes(public)),
                private_runtime_aggregate_sha256=sha256_bytes(canonical_json_bytes(private)),
                source_sha256=manifest['source_sha256'],
                execution_manifest_sha256=sha256_file(RUN/'EXECUTION_MANIFEST.json'),
                audit_script_sha256=sha256_file(Path(__file__)),
                original_run_unmodified=True)
    study.save(AREA, 'INTERRUPTION_AUDIT.json', result)
    study.save(AREA, 'INTERRUPTION_SEAL.json', seal)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
