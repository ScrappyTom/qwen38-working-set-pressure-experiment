"""Replay the native-qualified recovery transition without inference or checks."""
import json

import qualify_detail as study
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def verify():
    folder = study.AREA / 'qualification-001'
    seal = study.prior.read(folder / 'SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    study.prior.verify_sources(seal['source_sha256'])
    for row in seal['files']:
        path = folder / row['path']
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
    for name, digest in seal['private_runtime_files_local_only'].items():
        assert sha256_file(folder / 'private-runtime' / name) == digest
    records = verify_records(folder / 'records.jsonl', folder)
    assert not any(row['record_type'] in ('invocation_started', 'check_observation_preserved') for row in records)

    module = study.prior.Task()
    adapter = study.runner.Adapter(module)
    adapter.preceding_feedback = study.prior.read(module.RUN / 'after/C04-O02-preceding-feedback.json')
    session = study.prior.restore(module.RUN, 'after/C04-O02')
    session.__class__ = study.RecoveryDetailSession
    counts = {}
    for record in records:
        if record['record_type'] != 'native_input_prepared':
            continue
        row = record['payload']
        stem = row['stem']
        request = study.prior.read(folder / (stem + '-endpoint-request.json'))
        native = (folder / (stem + '-native.txt')).read_bytes()
        assert native == adapter.expected_native(request) == study.prior.read(folder / (stem + '-template.json'))['prompt'].encode()
        assert row['prompt_tokens'] == len(study.prior.read(folder / (stem + '-tokens.json'))['tokens'])
        assert (folder / (stem + '-wire-request.json')).read_bytes() == completion_request_bytes(request)
        counts[sha256_bytes(canonical_json_bytes(request))] = row['prompt_tokens']

    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]

    assert completion_request_bytes(adapter.request_for(session.view())) == (module.RUN / 'calls/C05-wire-request.json').read_bytes()
    assert measure(session.view()) == 23798
    session.mark_delivered(session.view())
    session.begin_request()
    reply = study.prior.read(module.RUN / 'calls/C05-reply.json')
    outcome = adapter.process_reply(session, reply, measure, adapter.preceding_feedback)
    assert outcome == study.prior.read(folder / 'unchanged-operation-outcomes.json')
    assert canonical_json_bytes(study.snapshot(session)) == (folder / 'corrected-state.json').read_bytes()
    view = session.view()
    assert canonical_json_bytes(view) == (folder / 'corrected-view.json').read_bytes()
    assert measure(view) == 6757
    regions = view['latest_feedback']['result']['match_regions']
    for region in regions:
        assert session.resolve_region(region['region_ref']) == {key: region[key] for key in ('path', 'start_line', 'end_line')}
    assert session.clone().view() == view

    session.mark_delivered(view)
    session.begin_request()
    outcome = adapter.process_reply(session, dict(
        discussion='Researcher selection of the first returned address.',
        operation=dict(action='work_on_exact', regions=[regions[0]['region_ref']], results=[])),
        measure, adapter.preceding_feedback)
    assert outcome == study.prior.read(folder / 'researcher-selection-result.json')
    view = session.view()
    assert measure(view) == 6504
    session.mark_delivered(view)
    assert canonical_json_bytes(view) == (folder / 'selected-view.json').read_bytes()
    assert canonical_json_bytes(study.snapshot(session)) == (folder / 'selected-state.json').read_bytes()
    assert session.candidate.candidate_id == study.prior.read(module.RUN / 'starting-state.json')['candidate_id']

    closed = [row['payload'] for row in records if row['record_type'] == 'runtime_closed']
    assert len(closed) == 1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    return dict(status='replayed_exactly', native_inputs=len(counts), custody_records=len(records),
        source_files=len(seal['source_sha256']), both_addresses_resolve=True,
        candidate_unchanged=True, corrected_feedback_tokens=6757, selected_tokens=6504,
        researcher_selected=True, no_additional_model_inference=True, checks_executed=0,
        owned_runtime_closed=True)


if __name__ == '__main__':
    result = verify()
    study.prior.save(study.AREA, 'VERIFICATION.json', result)
    print(json.dumps(result, indent=2))
