"""Exact replay of a closed compiler entry; no inference or checker execution.

Reuse the established replay boundary and add the imported incident world checks.
Saved native renderings/token counts supply every admission measurement. This is
mechanical verification, not a substitute for reading the actual model inputs,
complete reasoning, final operations, observations and resulting artifacts.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap  # noqa: F401
import compiler_task as study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


REPLAY_PATH = study.ROOT / 'development/decision_interface/reference_repair/verify_reference.py'


def _check_capture_receipt(receipt, inventory, bodies):
    if receipt.get('kind') != 'imported_observation':
        return None
    handle = receipt['handle']
    expected = inventory[handle]
    assert receipt['accepted'] is True
    assert receipt['content_utf8'].encode() == bodies[handle]
    assert (receipt['observed_candidate_id'], receipt['size_bytes'], receipt['sha256'], receipt['target']) == (
        expected['candidate_id'], expected['size_bytes'], expected['sha256'], expected['target'])
    assert receipt['retrieval_only'] is True and receipt['source_edit_authority'] is False
    return handle


def _sent_capture_bytes(envelope, pairs, inventory, bodies):
    """Check actual sent bodies and byte pages, independently of visibility flags."""
    view = envelope['workspace']
    receipts = []
    latest = view.get('latest_feedback')
    if latest:
        receipts.append(('latest_feedback', latest['result']))
    receipts.extend(('preceding_operation_feedback', row['result'])
                    for row in envelope.get('preceding_operation_feedback', []))
    pages = [('working_set.saved_results', row) for row in view['working_set']['saved_results']]
    for origin, receipt in receipts:
        pages.extend((origin+'.saved_results', row) for row in receipt.get('saved_results', []))
        if receipt.get('kind') == 'saved_bytes':
            pages.append((origin, receipt))
    observations = []
    for origin, receipt in receipts:
        handle = _check_capture_receipt(receipt, inventory, bodies)
        if handle:
            observations.append(dict(origin=origin, handle=handle, representation='complete_capture_receipt',
                result_handle=receipt.get('exact_result_handle'),
                content_bytes=len(bodies[handle]), content_sha256=sha256_bytes(bodies[handle])))
    for origin, page in pages:
        if page.get('kind') != 'saved_bytes' or not page.get('handle', '').startswith('RES-'):
            continue
        sequence = int(page['handle'].split('-')[1])
        assert 1 <= sequence <= view['archive']['action_count'] <= len(pairs)
        receipt = pairs[sequence-1]['result']
        if receipt.get('kind') != 'imported_observation':
            continue
        handle = _check_capture_receipt(receipt, inventory, bodies)
        raw = canonical_json_bytes(receipt)
        first = page['offset']
        end = page['next_offset'] if page['next_offset'] is not None else len(raw)
        assert type(first) is int and type(end) is int and 0 <= first <= end <= len(raw)
        assert page['total_bytes'] == len(raw) and page['sha256'] == sha256_bytes(raw)
        assert page['exact_utf8'].encode() == raw[first:end]
        complete = first == 0 and page['next_offset'] is None
        if complete:
            assert load_json_strict(page['exact_utf8']) == receipt
        observations.append(dict(origin=origin, handle=handle, result_handle=page['handle'],
            representation='serialized_capture_receipt_page', offset=first, end_offset=end,
            shown_bytes=end-first, total_bytes=len(raw), complete_receipt_shown=complete,
            page_sha256=sha256_bytes(raw[first:end])))
    return observations


def _verify_preparation(module, seal):
    """Connect the executed manifest to its exact pre-inference qualification."""
    manifest = study.read(module.RUN/'EXECUTION_MANIFEST.json')
    assert manifest['source_sha256'] == seal['source_sha256']
    assert manifest['actor'] == seal['actor'] == module.ACTOR
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (
        module.MAX_REQUESTS, module.MAX_OPERATIONS)
    if module.retain_imported_captures:
        assert manifest['imported_capture_retention'] == 'retain-requested-immutable-captures-v1'
    preparation = module.PACKAGE
    assert sha256_file(preparation/'SEAL.json') == manifest['preparation_seal_sha256']
    proof = study.read(preparation/'SEAL.json')
    assert proof['status'] == 'qualified_no_model_inference' and proof['completion_requests'] == 0
    assert proof['source_sha256'] == manifest['source_sha256']
    assert sha256_bytes(canonical_json_bytes(proof['files'])) == proof['aggregate_sha256']
    for row in proof['files']:
        path = (preparation/row['path']).resolve()
        assert path.is_relative_to(preparation.resolve())
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256']
    for name, digest in proof['private_runtime_files_local_only'].items():
        assert sha256_file(preparation/'private-runtime'/name) == digest
    first = module.RUN/'calls/C01-wire-request.json'
    if first.exists():
        assert first.read_bytes() == (preparation/'initial-wire-request.json').read_bytes()
        assert sha256_bytes(first.read_bytes()) == manifest['initial']['wire_request_sha256']
    return manifest


def _closed_replayer(module):
    spec = importlib.util.spec_from_file_location('compiler_closed_exact_replay', REPLAY_PATH)
    replayer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replayer)
    replayer.study = SimpleNamespace(
        Task=lambda replay_folder: study.Task(module.RUN.name.removeprefix('run-'), replay_folder),
        read=study.read, verify_sources=module.verify_sources,
        decode_reply=module.decode_reply, candidate_bytes=module.candidate_bytes)
    return replayer


def verify(version='002'):
    module = study.Task(version)
    run = module.RUN
    if not (run/'RESPONSE_SEAL.json').is_file():
        raise ValueError('Do not replay or assess an open model run')
    seal = study.read(run/'RESPONSE_SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    assert len({row['path'] for row in seal['files']}) == len(seal['files'])
    # The existing verifier checks source closure, every sealed artifact, custody,
    # native text/counts, dispatched requests, exact decoded public replies,
    # executed effects, each checkpoint and the final candidate. Its measure
    # callback only looks up saved admission counts; it makes no native requests.
    result = _closed_replayer(module).verify(run)
    manifest = _verify_preparation(module, seal)
    imported_inventory, imported_bodies = study.original_material()[3:]
    assert (run/'imported-captures/inventory.json').read_bytes() == canonical_json_bytes(imported_inventory)
    for handle, raw in imported_bodies.items():
        assert (run/f'imported-captures/{handle}.json').read_bytes() == raw
    starting = study.read(run/'starting-state.json')
    assert starting['pairs'] == [] and starting['candidate_id'] == study.STARTING_ID
    assert starting['ranges'] == [] and starting['saved'] == {}
    assert starting['starting_archive_length'] == 0
    # Replay-only store: execute() resolves the recorded observation and returns
    # before the subprocess branch. Do not call attach_observations here: that
    # live/preparation hook deliberately installs an executing store.
    replay_session = study.Task(version, replay_folder=run).initial_session()
    assert replay_session.observations.replay is True
    assert starting['imported_capture_state'] == study.snapshot(replay_session)['imported_capture_state']
    ending = 'final' if (run/'final-state.json').is_file() else 'stopped'
    ending_state = study.read(run/f'{ending}-state.json')
    acquisitions, capture_presentations, checks, observed = [], [], [], {}
    for path in sorted((run/'calls').glob('*-operation-*.json')):
        value = study.read(path)
        action, receipt = value['action'], value['result']
        if action['action'] == 'reopen_observation':
            row = dict(operation_file=path.relative_to(run).as_posix(),
                       handle=action['handle'], accepted=receipt.get('accepted'))
            if receipt.get('accepted'):
                expected = imported_inventory[action['handle']]
                assert receipt['kind'] == 'imported_observation'
                assert receipt['content_utf8'].encode() == imported_bodies[action['handle']]
                assert receipt['observed_candidate_id'] == expected['candidate_id'] == study.STARTING_ID
                assert (receipt['sha256'], receipt['size_bytes']) == (expected['sha256'], expected['size_bytes'])
                assert receipt['retrieval_only'] is True and receipt['source_edit_authority'] is False
                row.update(exact_result_handle=receipt['exact_result_handle'],
                           original_candidate_id=receipt['observed_candidate_id'])
            acquisitions.append(row)
        if action['action'] == 'check':
            checks.append(dict(operation_file=path.relative_to(run).as_posix(),
                accepted=receipt.get('accepted'), executed=receipt.get('executed'),
                passed=receipt.get('passed'), observation=receipt.get('observation')))
            if receipt.get('executed') and receipt.get('observation'):
                handle = receipt['observation']
                record = replay_session.observations.read(handle)
                assert record['candidate_id'] == receipt['checked_candidate_id'] == action['expected_candidate_id']
                assert record['checker_sha256'] == receipt['check_definition_sha256']
                assert record['check_id'] == action['check_id']
                assert record['passed'] == receipt['passed']
                assert record['accepted'] == receipt['accepted'] is True
                assert record['executed'] == receipt['executed'] is True
                for key in ('returncode', 'termination', 'capture_complete', 'streams'):
                    if key in receipt:
                        assert receipt[key] == record[key]
                observed[handle] = dict(candidate_id=record['candidate_id'],
                    checker_sha256=record['checker_sha256'], check_id=record['check_id'],
                    passed=record['passed'], termination=record['termination'],
                    capture_complete=record['capture_complete'],
                    captured_stream_bytes=sum(row['captured_bytes'] for row in record['streams'].values()))
    for path in sorted((run/'calls').glob('*-wire-request.json')):
        request = study.read(path)
        envelope = load_json_strict(request['messages'][-1]['content'])
        view = envelope['workspace']
        inventory = view['imported_observations']
        assert inventory['total_entries'] == 3 and inventory['inventory_is_not_capture_content'] is True
        assert {row['handle'] for row in inventory['entries']} == set(imported_inventory)
        for row in inventory['entries']:
            expected = imported_inventory[row['handle']]
            assert (row['observed_candidate_id'], row['size_bytes'], row['sha256'], row['target']) == (
                expected['candidate_id'], expected['size_bytes'], expected['sha256'], expected['target'])
            assert row['historical_incident'] is True
        shown = replay_session._shown_acquisitions(view)
        assert shown == {row['handle'] for row in inventory['entries'] if row['shown_complete']}
        bytes_shown = _sent_capture_bytes(envelope, ending_state['pairs'], imported_inventory, imported_bodies)
        complete_counts = {handle: sum(row['handle'] == handle and (
            row['representation'] == 'complete_capture_receipt' or row.get('complete_receipt_shown'))
            for row in bytes_shown) for handle in imported_bodies}
        capture_presentations.append(dict(request_file=path.relative_to(run).as_posix(),
            candidate_id=view['candidate_id'], presentation_mode=view['presentation']['mode'],
            complete_capture_receipts_shown=sorted(shown), actual_capture_bytes_shown=bytes_shown,
            complete_capture_body_counts=complete_counts))
    by_request = {int(Path(row['request_file']).name.split('-')[0][1:]): row
                  for row in capture_presentations}
    for acquisition in acquisitions:
        number = int(Path(acquisition['operation_file']).name.split('-')[0][1:])
        following = by_request.get(number + 1)
        acquisition['following_model_input_exists'] = following is not None
        if following is not None and acquisition['accepted']:
            acquisition['exact_acquisition_receipt_delivered_next'] = any(
                row.get('result_handle') == acquisition['exact_result_handle'] and (
                    row['representation'] == 'complete_capture_receipt' or row.get('complete_receipt_shown'))
                for row in following['actual_capture_bytes_shown'])
            acquisition['complete_capture_identities_in_following_input'] = following['complete_capture_receipts_shown']
    assert ending_state['imported_capture_state'] == starting['imported_capture_state']
    # The common verifier counts only optional preservation-log callbacks. Count
    # actual replayed check operations separately, including stores without one.
    optional_records = result.pop('observations_replayed_without_execution')
    result.update(original_entry=True, inherited_actor_operations=0,
        imported_records=len(imported_bodies), imported_bytes=sum(map(len, imported_bodies.values())),
        imported_capture_bindings_unchanged=True, imported_acquisitions=acquisitions,
        imported_capture_retention=manifest.get('imported_capture_retention', 'latest-feedback-only'),
        capture_presentations=capture_presentations, check_operations=checks,
        observations=observed, observation_custody_callback_records=optional_records,
        observations_replayed_without_execution=len(observed),
        no_additional_checker_execution=True, no_additional_tokenization=True,
        executed_manifest_sha256=sha256_file(run/'EXECUTION_MANIFEST.json'),
        preparation_seal_sha256=manifest['preparation_seal_sha256'],
        preparation_source_and_initial_wire_bound=True,
        replay_source_sha256=sha256_file(REPLAY_PATH),
        verification_source_sha256=sha256_file(Path(__file__)),
        interpretation_review_required=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='002')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = verify(args.version)
    output = args.output or Path(__file__).with_name('VERIFICATION.json')
    raw = canonical_json_bytes(value)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        assert output.read_bytes() == raw, 'Existing verification differs; preserve it'
    else:
        output.write_bytes(raw)
    print(json.dumps(value, indent=2))
