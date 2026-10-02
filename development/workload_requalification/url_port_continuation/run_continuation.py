"""Qualify and execute one explicitly extended URL-port continuation."""
import argparse
import json
from types import SimpleNamespace

import bootstrap
import continuation_task as study
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT

controller = load_helper('url_failed_check_continuation_controller',
                         'development/workload_requalification/action_lifecycle/run_continuation.py')
controller.INHERITED_REQUESTS, controller.INHERITED_OPERATIONS = 20, 30
runner = controller.runner
OriginalAdapter = runner.Adapter
INITIAL_KEYS = controller.INITIAL_KEYS


class Adapter(OriginalAdapter):
    def __init__(self, module):
        super().__init__(module)
        self.preceding_feedback = module.initial_preceding_feedback()


runner.Adapter = Adapter


def verify_preparation(module):
    manifest = runner.verify_package(module)
    expected = dict(inherited_requests=20, inherited_operations=30,
                    maximum_new_requests=16, maximum_new_operations=30,
                    no_live_coaching=True, automatic_retry=False)
    assert all(manifest.get(k) == v for k, v in expected.items()), 'continuation accounting differs'
    proof = module.read(module.PACKAGE / 'QUALIFICATION.json')
    reuse = module.read(module.PACKAGE / 'decoder-reuse.json')
    session = module.initial_session()
    request = Adapter(module).request_for(session.view())
    assert proof['status'] == 'qualified' and proof['completion_requests'] == 0
    assert proof['initial'] == manifest['initial'] and proof['route']['submitted']
    assert proof['route']['checks_executed'] == 2 and proof['entry_unchanged_after_qualification']
    assert reuse['cases'] == 31 and reuse['grammar_sha256'] == sha256_bytes(request['grammar'].encode())
    assert reuse['bound_original_native_forms'] and reuse['same_grammar']
    assert manifest['inherited_run_seal_sha256'] == study.OLD_SEAL
    return manifest


def prepare(module):
    folder = module.PACKAGE
    folder.mkdir(parents=True, exist_ok=False)
    store, bound, log = ArtifactStore(folder), {}, None
    initial, route, error, session = None, None, None, None
    entry_unchanged = False
    try:
        log = legacy.QualificationLog(folder / 'records.jsonl', 'url-failed-check-preparation', task_module=module)
        log.append('preparation_initialized', dict(completion_requests=0,
                   inherited_requests=20, inherited_operations=30), [])
        bound = module.source_identities()
        session, adapter = module.initial_session(), Adapter(module)
        module.attach_observations(session, folder, log)
        entry = canonical_json_bytes(module.snapshot(session))
        request = adapter.request_for(session.view())
        old = module.read(study.OLD / 'admission/I0094-endpoint-request.json')
        assert request['messages'][0] == old['messages'][0]
        assert {k: v for k, v in request.items() if k != 'messages'} == {
            k: v for k, v in old.items() if k != 'messages'}
        old_user, new_user = (json.loads(value['messages'][-1]['content']) for value in (old, request))
        assert old_user['preceding_operation_feedback'] == new_user['preceding_operation_feedback']
        adjusted = json.loads(json.dumps(old_user))
        adjusted['workspace']['allowance'].update(request_limit=36, requests_remaining=16)
        assert adjusted == new_user, 'more than the explicit opportunity changed'
        decoder = study.previous.read(study.previous.AREA / 'preparation-002/native-forms/RESULTS.json')
        original_request = study.previous.read(study.previous.AREA / 'preparation-002/initial-wire-request.json')
        assert decoder['status'] == 'passed' and decoder['completion_requests'] == 0
        assert decoder['model_inference_calls'] == decoder['checker_executions'] == 0
        assert len(decoder['cases']) == 31 and request['grammar'] == original_request['grammar']
        assert all(row['accepted_including_eos'] == row['expected'] for row in decoder['cases'])
        store.put('decoder-reuse.json', canonical_json_bytes(dict(cases=31,
            same_grammar=True, grammar_sha256=sha256_bytes(request['grammar'].encode()),
            bound_original_native_forms=module.decoder_reuse_bindings(), completion_requests=0)))
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter,
                               source_check=lambda: module.verify_sources(bound))
            count = loop.measure(session.view())
            assert count <= INPUT_LIMIT
            selected = loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial = {key: selected[key] for key in INITIAL_KEYS}
            loop.snapshot(session, 'starting')
            store.put('initial-wire-request.json', completion_request_bytes(request))
            assessment = session.view()['verification']['checks']['tests']
            assert assessment['applies_to_current'] and not assessment['passed']
            assert assessment['assessment']['failed_criteria'] == ['detect.error_class']
            assert session.view()['verification']['checks']['public'] is None
            route = qualification_route.qualify(module, loop, adapter, store, folder)
            entry_unchanged = canonical_json_bytes(module.snapshot(session)) == entry
            assert adapter.request_for(session.view()) == request, 'scripted feedback leaked into the prospective entry'
            assert entry_unchanged and (session.requests_used, session.calls_used) == (20, 30)
            module.verify_sources(bound)
    except BaseException as problem:
        error = problem
        failure = store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))
        if log is not None:
            log.append('preparation_failed', dict(type=type(problem).__name__, message=str(problem)), [failure])
    finally:
        store.put('QUALIFICATION.json', canonical_json_bytes(dict(status='failed' if error else 'qualified',
            initial=initial, route=route, completion_requests=0,
            inherited_requests=20, inherited_operations=30, maximum_new_requests=16,
            maximum_new_operations=30, entry_unchanged_after_qualification=entry_unchanged,
            memory=RUNTIME.memory_stats(folder / 'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT))))
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound,
                    completion_requests=0)
    if error:
        raise error
    manifest = dict(actor=module.ACTOR, seed=module.SEED, maximum_requests=36, maximum_operations=60,
        source_sha256=bound, initial=initial, preparation_seal_sha256=sha256_file(folder / 'SEAL.json'),
        inherited_run_seal_sha256=study.OLD_SEAL, owner_direction=module.OWNER_DIRECTION,
        inherited_requests=20, inherited_operations=30, maximum_new_requests=16, maximum_new_operations=30,
        starting_candidate_id=session.candidate.candidate_id, starting_archive_operations=30,
        original_starting_archive_length=0, no_live_coaching=True, automatic_retry=False,
        selection_assistance='none; exact saved final selection/recovery state',
        literal_source_reply=True, checker_contracts=study.previous.checkers.contracts(),
        automatic_edit_checks={module.TEST: 'tests', module.DOC: 'public'})
    with module.MANIFEST.open('xb') as stream:
        stream.write(canonical_json_bytes(manifest))
    verify_preparation(module)
    print(json.dumps(dict(status='qualified', initial=initial, completion_requests=0)), flush=True)


def run_once(module):
    manifest = verify_preparation(module)
    assert not module.RUN.exists(), 'attempt exists; no retry'
    module.RUN.mkdir()
    store = ArtifactStore(module.RUN)
    log = runner.RunLog(module.RUN / 'records.jsonl', 'url-failed-check-continuation', task_module=module)
    log.append('attempt_reserved', dict(owner_direction=module.OWNER_DIRECTION,
        manifest_sha256=sha256_file(module.MANIFEST)), [store.put('EXECUTION_MANIFEST.json', module.MANIFEST.read_bytes()),
        store.put('SPEC.md', (module.AREA / 'SPEC.md').read_bytes())])
    session, adapter, error, outcome = None, None, None, None
    try:
        session, adapter = module.initial_session(), Adapter(module)
        module.attach_observations(session, module.RUN, log)
        server, model, _ = module.runtime_paths()
        args = SimpleNamespace(server=server, model=model, output=module.RUN)
        with RUNTIME.owned_runtime(args, store, log) as url:
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
        records = verify_records(module.RUN / 'records.jsonl', module.RUN)
        files = RUNTIME.file_inventory(module.RUN)
        operations = session.calls_used if session is not None else 30
        store.put('RESPONSE_SEAL.json', canonical_json_bytes(dict(
            disposition='stopped_without_retry' if error else outcome['disposition'], actor=module.ACTOR,
            source_sha256=manifest['source_sha256'], files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), record_count=len(records),
            sent_requests=sum(r['record_type'] == 'invocation_started' for r in records),
            returned_responses=sum(r['record_type'] == 'response_received' for r in records),
            processed_invocations=sum(r['record_type'] == 'invocation_completed' for r in records),
            inherited_requests=20, inherited_operations=30, actual_operations=operations,
            new_operations=operations-30, cumulative_requests_used=session.requests_used if session else 20,
            memory=RUNTIME.memory_stats(module.RUN / 'memory.csv'),
            runtime=RUNTIME.runtime_evidence(module.RUN / 'private-runtime/server.stderr.log'),
            port_free=RUNTIME.port_free(RUNTIME.PORT),
            private_runtime_files_local_only={p.name: sha256_file(p) for p in (module.RUN / 'private-runtime').glob('*') if p.is_file()})))
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
