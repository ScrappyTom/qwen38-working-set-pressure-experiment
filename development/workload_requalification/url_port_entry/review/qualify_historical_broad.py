"""Native sizing supplement from the exact original crowded URL stopped state.

Run only by root under exclusive runtime ownership after main preparation closes.
This is migration to the current host, not replay, a model entry, or a contribution.
The script preserves the original candidate, three archived acquisitions and four
consumed requests. New choices are evaluator-selected. No checker, edit, account,
submission or completion request is executed; every output folder is single-use.
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
import url_task as study
import run_url as execution
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ORIGINAL = study.ORIGINAL / 'run-001'
ORIGINAL_SEAL_SHA = 'eb3ecab7768f7b3269f104c6e43856728a1e486370b615b5f18ca67ba1ecc402'
CLASSIFICATION = 'evaluator-selected native control transition from migrated original URL stopped state; no model inference'
INPUT_LIMIT = 23808
EXPECTED_EXTENTS = {study.TARGET: (1, 648), study.TEST: (1, 800), study.DOC: (1, 39)}


class MigratedSession(study.Session):
    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = (
            'Evaluator migration of the original URL contribution checkpoint: four requests were consumed and '
            'three acquisitions were archived before this qualification. Their candidate and designated extents '
            'are preserved. Subsequent transitions are researcher scripted, not model actions or a fresh task entry. '
            'No earlier private thinking or reference contribution is supplied.')
        return value


def original_material():
    seal_path = ORIGINAL / 'RESPONSE_SEAL.json'
    assert sha256_file(seal_path) == ORIGINAL_SEAL_SHA, 'Original response seal changed'
    seal = study.read(seal_path)
    rows = {row['path']: row for row in seal['files']}
    assert len(rows) == len(seal['files'])
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    bindings = {seal_path.relative_to(study.ROOT).as_posix(): ORIGINAL_SEAL_SHA}
    for row in seal['files']:
        path = (ORIGINAL / row['path']).resolve()
        assert path.is_relative_to(ORIGINAL.resolve())
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
        bindings[path.relative_to(study.ROOT).as_posix()] = row['sha256']
    names = ('stopped-state.json', 'stopped-candidate.json', 'stopped-preceding-feedback.json',
             'calls/C04-wire-request.json', 'calls/C04-reply.json')
    material = {name: (ORIGINAL / name).read_bytes() for name in names}
    assert all(sha256_bytes(raw) == rows[name]['sha256'] for name, raw in material.items())
    state = load_json_strict(material['stopped-state.json'])
    candidate = study.candidate_from_snapshot(load_json_strict(material['stopped-candidate.json']))
    assert candidate.candidate_id == state['candidate_id'] == study.STARTING_ID
    assert study.candidate_bytes(candidate) == study.candidate_bytes(study.starting_candidate())
    assert (state['requests_used'], len(state['pairs']), state['request_limit'], state['call_limit']) == (4, 3, 20, 60)
    assert state['starting_archive_length'] == 0 and not state['submitted'] and not state['delivery_blocked']
    assert state['saved'] == state['diffs'] == {} and load_json_strict(material['stopped-preceding-feedback.json']) == []
    assert all(pair['result']['accepted'] is True and pair['response']['action'] in ('read', 'work_on')
               for pair in state['pairs'])
    assert {row['path']: (row['start_line'], row['end_line']) for row in state['ranges']} == EXPECTED_EXTENTS
    wire = load_json_strict(material['calls/C04-wire-request.json'])
    old_view = load_json_strict(wire['messages'][1]['content'].encode())['workspace']
    old_sources = list(old_view['working_set']['sources']) + [old_view['latest_feedback']['result']['source']]
    assert {row['path']: (row['returned_start_line'], row['returned_end_line']) for row in old_sources} == EXPECTED_EXTENTS
    for row in old_sources:
        first, last = EXPECTED_EXTENTS[row['path']]
        body = ''.join(candidate.file_map[row['path']].decode().splitlines(keepends=True)[first-1:last]).encode()
        assert row['content'].encode() == body and row['file_sha256'] == candidate.file_sha256(row['path'])
    assert old_view['working_account'] is None and old_view['task'] == study.task_text()
    attempted = load_json_strict(material['calls/C04-reply.json'])['operation']
    assert attempted == dict(action='read', path=study.TEST, start_line=801, end_line=900)
    return state, candidate, material, bindings


def migrate(module, state, candidate, output):
    session = module.initial_session()
    session.__class__ = MigratedSession
    for key, value in state.items():
        if key != 'candidate_id':
            setattr(session, key, copy.deepcopy(value))
    session.candidate, session.versions = candidate, {candidate.candidate_id: candidate}
    # There were no account updates, checks or stored observations in this prefix.
    # Current account/control state stays at its explicit initial defaults.
    session.observations = study.ObservationStore(output / 'observations')
    assert session.working_account() is None and session.check_state() is None
    assert session.calls_used == 3 and session.requests_used == 4
    for key, value in state.items():
        assert key == 'candidate_id' or getattr(session, key) == value, key
    view = session.view()
    assert {row['path']: (row['returned_start_line'], row['returned_end_line'])
            for row in view['working_set']['sources']} == EXPECTED_EXTENTS
    return session


def work_identity(session):
    return canonical_json_bytes(dict(candidate=study.candidate_bytes(session.candidate).decode(),
        ranges=session.ranges, saved=session.saved, account=session.working_account(),
        check=session.check_state(), diffs=session.diffs))


def qualify(output, version='002'):
    module = study.Task(version)
    manifest = execution.runner.verify_package(module)
    main_seal = module.PACKAGE / 'SEAL.json'
    main_hash = sha256_file(main_seal)
    state, candidate, material, original_bindings = original_material()
    script = Path(__file__).resolve()
    note = script.parent / 'HISTORICAL_SUPPLEMENT_NOTE.md'
    script_key = script.relative_to(study.ROOT).as_posix()
    assert script_key not in manifest['source_sha256'], 'Supplement must remain outside frozen main closure'
    bound = {**manifest['source_sha256'], **original_bindings, script_key: sha256_file(script),
        note.relative_to(study.ROOT).as_posix(): sha256_file(note),
        main_seal.relative_to(study.ROOT).as_posix(): main_hash,
        module.MANIFEST.relative_to(study.ROOT).as_posix(): sha256_file(module.MANIFEST)}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(output)
    log = execution.legacy.QualificationLog(output / 'records.jsonl', 'url-original-crowded-state', task_module=module)
    session = migrate(module, state, candidate, output)
    original_pairs = copy.deepcopy(session.pairs)
    baseline = work_identity(session)
    log.append('original_checkpoint_migrated', dict(classification=CLASSIFICATION,
        original_seal_sha256=ORIGINAL_SEAL_SHA, main_preparation_seal_sha256=main_hash,
        original_requests_used=4, original_archived_operations=3, allowance_reset=False,
        migration_not_replay=True, checker_executions=0, completion_sent=False),
        [store.put('QUALIFICATION_SCRIPT.py', script.read_bytes()),
         store.put('QUALIFICATION_NOTE.md', note.read_bytes()),
         store.put('ORIGINAL_RESPONSE_SEAL.json', (ORIGINAL / 'RESPONSE_SEAL.json').read_bytes()),
         store.put('MAIN_PREPARATION_SEAL.json', main_seal.read_bytes()),
         store.put('MAIN_EXECUTION_MANIFEST.json', module.MANIFEST.read_bytes()),
         *[store.put('original/' + name, raw) for name, raw in material.items()]])
    adapter = execution.runner.Adapter(module)
    rows, loop, result, error = [], None, None, None
    try:
        server, model, _ = module.runtime_paths()
        with execution.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=output), store, log) as url:
            loop = execution.runner.Loop(output, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(bound))
            loop.snapshot(session, 'migrated-before-admission')
            ordinary_view = copy.deepcopy(session.view())
            ordinary_tokens = loop.measure(ordinary_view)
            store.put('migrated-ordinary-view.json', canonical_json_bytes(ordinary_view))
            # Qualify the host's actual fallback, rather than assume the old view
            # fits with a changed permanent reference and presentation layout.
            fitted = session._fits_feedback(loop.measure)
            assert fitted and not session.delivery_blocked, 'Migrated state has no admitted control presentation'
            assert work_identity(session) == baseline and session.pairs == original_pairs
            admitted_view = copy.deepcopy(session.view())
            admitted_tokens = loop.measure(admitted_view)
            assert admitted_tokens <= INPUT_LIMIT and session.requests_used == 4 and session.calls_used == 3
            log.append('migration_presentation_admitted', dict(ordinary_input_tokens=ordinary_tokens,
                admitted_input_tokens=admitted_tokens, recovered_view=session.recovery,
                candidate_selection_account_unchanged=True, completion_sent=False),
                [store.put('migrated-admitted-view.json', canonical_json_bytes(admitted_view))])
            loop.snapshot(session, 'migrated-admitted')

            def act(action, basis):
                assert action['action'] in {'read', 'work_on_exact', 'search'}
                before = copy.deepcopy(session.view())
                count = loop.measure(before)
                assert count <= INPUT_LIMIT and session.requests_used < session.request_limit
                session.mark_delivered(before)
                session.begin_request()
                reply = dict(discussion=basis, operation=action)
                host = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
                assert len(host['operations']) == 1 and host['executed'] is True
                receipt = host['operations'][0]['result']
                after = copy.deepcopy(session.view())
                following = loop.measure(after)
                row = dict(before_view=before, reply=reply, outcome=host, after_view=after,
                    input_tokens=count, next_input_tokens=following, basis=basis, classification=CLASSIFICATION)
                rows.append(row)
                log.append('scripted_transition', dict(number=len(rows), action=action['action'],
                    input_tokens=count, next_input_tokens=following, accepted=receipt.get('accepted'),
                    requests_used=session.requests_used, archived_operations=len(session.pairs), completion_sent=False),
                    [store.put(f'steps/{len(rows):02d}.json', canonical_json_bytes(row))])
                loop.snapshot(session, f'after/{len(rows):02d}')
                assert following <= INPUT_LIMIT and not session.delivery_blocked
                assert session.pairs[:3] == original_pairs
                assert study.candidate_bytes(session.candidate) == study.candidate_bytes(candidate)
                assert session.working_account() is None and session.check_state() is None and not session.diffs
                assert adapter.preceding_feedback == []
                return receipt

            # References must be in the actual admitted input. Do not obtain
            # regrouping coordinates secretly from the legacy snapshot.
            source_rows = list(admitted_view['working_set']['sources'])
            source_rows += admitted_view['visibility']['retained_inventory']['entries']
            doc_ref = next(row['region_ref'] for row in source_rows if row.get('path') == study.DOC)
            before_attempt = work_identity(session)
            original_attempt = load_json_strict(material['calls/C04-reply.json'])['operation']
            attempted = act(original_attempt,
                'Execute the exact original C04 request for test lines801–900 under the corrected host. Preserve its actual bounded result or complete rejection; do not force the historical failure to recur.')
            capacity_rejection = attempted.get('accepted') is False
            if capacity_rejection:
                assert work_identity(session) == before_attempt and session.recovery
                assert any(word in attempted.get('error', '').lower() for word in ('fit', 'capacity', 'placed beside'))
                shown = session.view()['latest_feedback']['result']
                assert shown.get('accepted') is False and shown.get('error') == attempted.get('error')
                assert session.view()['presentation']['selected_bodies_omitted'] is True
            else:
                assert attempted.get('accepted') is True
                returned = attempted['source']
                assert returned['path'] == study.TEST and returned['returned_start_line'] == 801
                assert 801 <= returned['returned_end_line'] <= 900
                body = ''.join(candidate.file_map[study.TEST].decode().splitlines(keepends=True)[
                    returned['returned_start_line']-1:returned['returned_end_line']]).encode()
                assert returned['content'].encode() == body
                shown = session.view()['working_set']['sources']
                assert any(row['path'] == study.TEST and row['returned_start_line'] <= 801
                    and row['returned_end_line'] >= returned['returned_end_line'] for row in shown)

            port = act(dict(action='search', path=study.TARGET, query='def port', offset=0, limit=16),
                'The unchanged task requires port behavior and names the implementation authority. Search for its accessor and use returned exact coordinates, without guessing an expected value.')
            assert port['accepted']
            port_ref = next(row['region_ref'] for row in port['regions'] if row.get('name') == 'port')
            narrowed = act(dict(action='work_on_exact', regions=[port_ref, doc_ref], results=[]),
                'Select the accessor region actually returned by search together with the original documentation-header reference shown by the admitted input. This small group is evaluator-selected; it does not establish full task adequacy.')
            assert narrowed['accepted'] and not session.recovery
            final = session.view()
            sources = final['working_set']['sources']
            assert {row['path'] for row in sources} == {study.TARGET, study.DOC}
            assert any(row['path'] == study.TARGET and 'def port' in row['content'] for row in sources)
            assert any(row['path'] == study.DOC and (row['returned_start_line'], row['returned_end_line']) == EXPECTED_EXTENTS[study.DOC] for row in sources)
            restored = module.restore(module.snapshot(session), session.candidate, output, replay=True)
            restored.__class__ = MigratedSession
            assert canonical_json_bytes(module.snapshot(restored)) == canonical_json_bytes(module.snapshot(session))
            assert restored.view() == final
            assert session.requests_used == 7 and session.calls_used == len(session.pairs) == 6
            assert session.starting_archive_length == 0 and session.request_limit == 20 and session.call_limit == 60
            assert loop.sent == 0
            module.verify_sources(bound)
            loop.health()
            result = dict(completed=True, classification=CLASSIFICATION, migration_not_replay=True,
                original_group_extents=EXPECTED_EXTENTS, original_requests_used=4, original_archived_operations=3,
                ordinary_input_tokens=ordinary_tokens, admitted_migration_input_tokens=admitted_tokens,
                complete_capacity_rejection_reproduced=capacity_rejection,
                original_attempted_read_accepted=attempted['accepted'],
                rejection_not_manufactured=True, exact_candidate_archive_prefix_account_unchanged=True,
                final_ordinary_source_co_presence=True, source_group_selection_is_evaluator_directed=True,
                new_checks=0, new_edits=0, new_account_updates=0, new_submissions=0,
                completion_requests=0, new_scripted_requests=len(rows), native_inputs=len(loop.cache),
                final_requests_used=session.requests_used, final_archived_operations=len(session.pairs),
                checkpoint_roundtrip=True,
                peak_measured_proposal_tokens=max(row['prompt_tokens'] for row in loop.cache.values()),
                peak_admitted_transition_tokens=max(max(row['input_tokens'], row['next_input_tokens']) for row in rows),
                limitation='This qualifies a migrated control and selection path. It is not Qwen selection, contribution completion, replay of the old host, or evidence that this small group is sufficient for the full task.')
    except BaseException as problem:
        error = problem
        log.append('supplement_failed', dict(type=type(problem).__name__, message=str(problem), completion_sent=False),
            [store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))])
        if loop is not None:
            loop.snapshot(session, 'stopped')
    finally:
        assert sha256_file(main_seal) == main_hash and sha256_file(ORIGINAL / 'RESPONSE_SEAL.json') == ORIGINAL_SEAL_SHA
        module.verify_sources(bound)
        records = verify_records(output / 'records.jsonl', output)
        assert not any(row['record_type'] in {'invocation_started', 'response_received'} for row in records)
        store.put('RESULTS.json', canonical_json_bytes(dict(status='failed_preserved' if error else 'qualified_no_model_inference',
            result=result, completed_scripted_decisions=len(rows), completion_requests=0, checker_executions=0,
            main_preparation_seal_sha256=main_hash, original_response_seal_sha256=ORIGINAL_SEAL_SHA,
            memory=execution.RUNTIME.memory_stats(output / 'memory.csv'),
            port_free=execution.RUNTIME.port_free(execution.RUNTIME.PORT), record_count=len(records))))
        execution.legacy.seal(output, 'failed_preserved' if error else 'qualified_no_model_inference', bound,
            completion_requests=0, checker_executions=0, main_preparation_seal_sha256=main_hash,
            original_response_seal_sha256=ORIGINAL_SEAL_SHA, classification=CLASSIFICATION)
    if error:
        raise error
    print(json.dumps(result, sort_keys=True), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='002')
    parser.add_argument('--output', type=Path, default=AREA / 'review/historical-capacity-qualification-001')
    args = parser.parse_args()
    qualify(args.output, args.version)
