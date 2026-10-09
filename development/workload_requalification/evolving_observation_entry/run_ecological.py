"""Qualify the exact fresh E18 entry, then execute one sealed uncoached attempt."""
import argparse
import json
from types import SimpleNamespace

import bootstrap
import observation_task as study
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT

runner = load_helper('ecological_observation_controller', 'scripts/run_uncoached_contribution.py')
native_forms = load_helper('ecological_observation_native_forms',
    'development/workload_requalification/compiler_entry/native_forms.py')
INITIAL_KEYS = ('prompt_tokens', 'request_sha256', 'native_sha256', 'wire_request_sha256')


def fresh_entry(session):
    assert session.candidate.candidate_id == study.STARTING_ID
    assert session.calls_used == session.requests_used == session.starting_archive_length == 0
    assert not session.pairs and not session.ranges and not session.saved
    assert not session.delivered_sources and session.working_account() is None
    assert session.request_limit == study.MAX_REQUESTS and session.call_limit == study.MAX_OPERATIONS
    assert session.edit_checks == {} and set(session.checkers) == {'public'}
    inventory = session.view()['imported_observations']
    assert inventory['total_entries'] == 2 and inventory['inventory_is_not_capture_content']
    assert not any(row['shown_complete'] or row['latest_acquisition_result']
                   for row in inventory['entries'])


def verify_preparation(module):
    manifest = runner.verify_package(module)
    proof = module.read(module.PACKAGE / 'QUALIFICATION.json')
    assert proof['status'] == 'qualified' and proof['completion_requests'] == 0
    assert proof['entry_unchanged_after_qualification'] and proof['route']['submitted']
    assert proof['initial'] == manifest['initial']
    assert proof['native_forms']['status'] == 'passed'
    assert manifest['seed'] == study.SEED and manifest['original_entry'] is True
    assert manifest['automatic_edit_checks'] == {}
    assert manifest['no_live_coaching'] and not manifest['automatic_retry']
    assert manifest['starting_candidate_id'] == study.STARTING_ID
    assert manifest['imported_observation_bindings'] == module.original_observation_state()
    assert manifest['imported_capture_retention'] == 'retain-requested-immutable-captures-v1'
    fresh_entry(module.initial_session())
    return manifest


def prepare(module):
    folder = module.PACKAGE
    folder.mkdir(parents=True, exist_ok=False)
    store, bound, log = ArtifactStore(folder), {}, None
    initial = forms = route = error = None
    entry_unchanged = False
    try:
        log = legacy.QualificationLog(folder / 'records.jsonl',
            'ecological-observation-preparation', task_module=module)
        log.append('preparation_initialized', dict(completion_requests=0, original_entry=True), [])
        bound = module.source_identities()
        session, adapter = module.initial_session(), runner.Adapter(module)
        module.attach_observations(session, folder, log)
        fresh_entry(session)
        entry = canonical_json_bytes(module.snapshot(session))
        request = adapter.request_for(session.view())
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(bound))
            count = loop.measure(session.view())
            assert count <= INPUT_LIMIT
            initial = {key: loop.cache[sha256_bytes(canonical_json_bytes(request))][key] for key in INITIAL_KEYS}
            loop.snapshot(session, 'starting')
            store.put('initial-wire-request.json', completion_request_bytes(request))
            forms = native_forms.qualify(module, folder / 'native-forms', url, store, log)
            route = qualification_route.qualify(module, loop, adapter, store, folder)
            entry_unchanged = canonical_json_bytes(module.snapshot(session)) == entry
            assert entry_unchanged and adapter.request_for(session.view()) == request
            fresh_entry(session)
            module.verify_sources(bound)
    except BaseException as problem:
        error = problem
        failure = store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))
        if log is not None:
            log.append('preparation_failed', dict(type=type(problem).__name__, message=str(problem)), [failure])
    finally:
        store.put('QUALIFICATION.json', canonical_json_bytes(dict(status='failed' if error else 'qualified',
            initial=initial, native_forms=forms, route=route, completion_requests=0,
            entry_unchanged_after_qualification=entry_unchanged, actor=module.ACTOR,
            maximum_requests=module.MAX_REQUESTS, maximum_operations=module.MAX_OPERATIONS,
            memory=RUNTIME.memory_stats(folder / 'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT))))
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound,
            completion_requests=0)
    if error:
        raise error
    manifest = dict(actor=module.ACTOR, seed=module.SEED, maximum_requests=module.MAX_REQUESTS,
        maximum_operations=module.MAX_OPERATIONS, source_sha256=bound, initial=initial,
        preparation_seal_sha256=sha256_file(folder / 'SEAL.json'), original_entry=True,
        starting_candidate_id=study.STARTING_ID, starting_archive_operations=0,
        owner_direction=study.OWNER_DIRECTION, no_live_coaching=True, automatic_retry=False,
        automatic_edit_checks={}, checker_contracts={'public': {'checker_sha256': study.PUBLIC_SHA}},
        literal_source_reply=True, hidden_evaluation='after_response_seal_only',
        selection_assistance='none; fresh empty selected group',
        named_source_inspection='actual sent current source; audit distinct from target edit guard',
        imported_observation_bindings=module.original_observation_state(),
        imported_capture_retention='retain-requested-immutable-captures-v1')
    with module.MANIFEST.open('xb') as stream:
        stream.write(canonical_json_bytes(manifest))
    verify_preparation(module)
    print(json.dumps(dict(status='qualified', initial=initial, route=route, completion_requests=0)), flush=True)


def run_once(module):
    manifest = verify_preparation(module)
    assert not module.RUN.exists(), 'attempt exists; no retry'
    module.RUN.mkdir()
    store = ArtifactStore(module.RUN)
    log = runner.RunLog(module.RUN / 'records.jsonl', 'ecological-observation-entry', task_module=module)
    log.append('attempt_reserved', dict(owner_direction=module.OWNER_DIRECTION,
        manifest_sha256=sha256_file(module.MANIFEST)),
        [store.put('EXECUTION_MANIFEST.json', module.MANIFEST.read_bytes()),
         store.put('SPEC.md', (module.AREA / 'SPEC.md').read_bytes())])
    session = adapter = error = outcome = None
    try:
        session, adapter = module.initial_session(), runner.Adapter(module)
        module.attach_observations(session, module.RUN, log)
        fresh_entry(session)
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=module.RUN), store, log) as url:
            loop = runner.Loop(module.RUN, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(manifest['source_sha256']), initial=manifest['initial'])
            outcome = loop.execute(session)
            module.base.pilot.health(module.RUN)
    except BaseException as problem:
        error = problem
        failure = store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))
        log.append('attempt_stopped', dict(error_type=type(problem).__name__, error=str(problem)), [failure])
        if session is not None:
            for name, value in (('stopped-state.json', canonical_json_bytes(module.snapshot(session))),
                ('stopped-candidate.json', module.candidate_bytes(session.candidate)),
                ('stopped-preceding-feedback.json', canonical_json_bytes(adapter.preceding_feedback))):
                store.put(name, value)
    finally:
        records, files = verify_records(module.RUN / 'records.jsonl', module.RUN), RUNTIME.file_inventory(module.RUN)
        store.put('RESPONSE_SEAL.json', canonical_json_bytes(dict(
            disposition='stopped_without_retry' if error else outcome['disposition'], actor=module.ACTOR,
            source_sha256=manifest['source_sha256'], files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), record_count=len(records),
            sent_requests=sum(r['record_type'] == 'invocation_started' for r in records),
            returned_responses=sum(r['record_type'] == 'response_received' for r in records),
            processed_invocations=sum(r['record_type'] == 'invocation_completed' for r in records),
            actual_operations=session.calls_used if session else 0,
            memory=RUNTIME.memory_stats(module.RUN / 'memory.csv'),
            runtime=RUNTIME.runtime_evidence(module.RUN / 'private-runtime/server.stderr.log'),
            port_free=RUNTIME.port_free(RUNTIME.PORT),
            private_runtime_files_local_only={p.name: sha256_file(p)
                for p in (module.RUN / 'private-runtime').glob('*') if p.is_file()})))
    if error:
        raise error
    print('Closed: ' + outcome['disposition'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = study.Task(args.version)
    prepare(module) if args.mode == 'prepare' else run_once(module)
