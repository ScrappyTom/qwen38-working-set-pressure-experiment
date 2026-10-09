"""Frozen preparation and one uncoached E18 continuation; no automatic retry."""
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

controller = load_helper('evolving_saved_work_controller',
    'development/workload_requalification/action_lifecycle/run_continuation.py')
controller.INHERITED_REQUESTS, controller.INHERITED_OPERATIONS = 24, 37
runner = controller.runner
OrdinaryAdapter = runner.Adapter


class Adapter(OrdinaryAdapter):
    def __init__(self, module):
        super().__init__(module)
        self.preceding_feedback = module.initial_preceding_feedback()


runner.Adapter = Adapter
native_forms = load_helper('evolving_saved_native_forms',
    'development/workload_requalification/action_lifecycle/native_forms.py')
INITIAL_KEYS = ('prompt_tokens', 'request_sha256', 'native_sha256', 'wire_request_sha256')


def declared_entry(session):
    assert session.candidate.candidate_id == study.SAVED_ID
    assert (session.requests_used, session.calls_used, session.starting_archive_length) == (24, 37, 0)
    assert not session.submitted and not session.delivery_blocked and session.check_state() is None
    assert session.request_limit == 36 and session.call_limit == 73 and session.edit_checks == {}
    expected = {**study.inherited_state(), 'request_limit': 36, 'call_limit': 73}
    assert canonical_json_bytes(study.snapshot(session)) == canonical_json_bytes(expected)
    assert session.task == study.previous.task_text()


def verify_preparation(module):
    manifest = runner.verify_package(module)
    proof = module.read(module.PACKAGE / 'QUALIFICATION.json')
    assert proof['status'] == 'qualified' and proof['completion_requests'] == 0
    assert proof['entry_unchanged_after_qualification'] and proof['route']['submitted']
    assert proof['route']['audit']['temporal_contract_met'] and proof['initial'] == manifest['initial']
    assert proof['native_forms']['status'] == 'passed'
    assert (manifest['inherited_requests'], manifest['inherited_operations']) == (24, 37)
    assert (manifest['maximum_new_requests'], manifest['maximum_new_operations']) == (12, 36)
    assert (manifest['maximum_requests'], manifest['maximum_operations']) == (36, 73)
    assert manifest['inherited_run_seal_sha256'] == study.OLD_SEAL
    assert manifest['no_live_coaching'] and not manifest['automatic_retry']
    assert manifest['automatic_edit_checks'] == {} and not manifest['original_entry']
    assert manifest['starting_candidate_id'] == study.SAVED_ID
    declared_entry(module.initial_session())
    return manifest


def prepare(module):
    folder = module.PACKAGE
    folder.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder / 'records.jsonl', 'evolving-source-continuation-preparation', task_module=module)
    bound, initial, forms, route, error, unchanged = module.source_identities(), None, None, None, None, False
    try:
        session, adapter = module.initial_session(), Adapter(module)
        module.attach_observations(session, folder, log)
        declared_entry(session)
        before = canonical_json_bytes(module.snapshot(session))
        request = adapter.request_for(session.view())
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(bound))
            assert loop.measure(session.view()) <= 23808
            initial = {key: loop.cache[sha256_bytes(canonical_json_bytes(request))][key] for key in INITIAL_KEYS}
            loop.snapshot(session, 'starting')
            store.put('initial-wire-request.json', completion_request_bytes(request))
            forms = native_forms.qualify(folder / 'native-forms', task=module, request=request,
                source_identities=module.implementation_identities)
            route = qualification_route.qualify(module, loop, adapter, store, folder)
            adapter.preceding_feedback[:] = module.initial_preceding_feedback()
            unchanged = canonical_json_bytes(module.snapshot(session)) == before
            assert unchanged and adapter.request_for(session.view()) == request
            declared_entry(session)
            module.verify_sources(bound)
    except BaseException as problem:
        error = problem
        log.append('preparation_failed', dict(type=type(problem).__name__, message=str(problem)),
            [store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))])
    finally:
        store.put('QUALIFICATION.json', canonical_json_bytes(dict(status='failed' if error else 'qualified',
            initial=initial, native_forms=forms, route=route, completion_requests=0,
            entry_unchanged_after_qualification=unchanged, actor=module.ACTOR,
            maximum_requests=36, maximum_operations=73,
            memory=RUNTIME.memory_stats(folder / 'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT))))
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound, completion_requests=0)
    if error:
        raise error
    manifest = dict(actor=module.ACTOR, seed=module.SEED, maximum_requests=36, maximum_operations=73,
        source_sha256=bound, initial=initial, preparation_seal_sha256=sha256_file(folder / 'SEAL.json'),
        original_entry=False, starting_candidate_id=study.SAVED_ID, starting_archive_operations=37,
        original_starting_archive_length=0, inherited_requests=24, inherited_operations=37,
        maximum_new_requests=12, maximum_new_operations=36, inherited_run_seal_sha256=study.OLD_SEAL,
        task_sha256=study.previous.TASK_SHA, task_and_checker_unchanged=True,
        owner_direction=study.OWNER_DIRECTION, no_live_coaching=True, automatic_retry=False,
        automatic_edit_checks={}, checker_contracts={'public': {'checker_sha256': study.PUBLIC_SHA}},
        literal_source_reply=True, hidden_evaluation='after_response_seal_only',
        selection_assistance='none; exact saved actor selection',
        acquisition_qualification_seal_sha256=sha256_file(study.ROOT / 'development/workload_requalification/acquisition_feedback/qualification-002/SEAL.json'))
    with module.MANIFEST.open('xb') as stream:
        stream.write(canonical_json_bytes(manifest))
    verify_preparation(module)
    print(json.dumps(dict(status='qualified', initial=initial, route=route, completion_requests=0)), flush=True)


def run_once(module):
    manifest = verify_preparation(module)
    assert not module.RUN.exists(), 'attempt exists; no retry'
    module.RUN.mkdir()
    store = ArtifactStore(module.RUN)
    log = runner.RunLog(module.RUN / 'records.jsonl', 'evolving-source-continuation', task_module=module)
    log.append('attempt_reserved', dict(owner_direction=module.OWNER_DIRECTION,
        manifest_sha256=sha256_file(module.MANIFEST)),
        [store.put('EXECUTION_MANIFEST.json', module.MANIFEST.read_bytes()),
         store.put('SPEC.md', (module.AREA / 'SPEC.md').read_bytes())])
    session = adapter = error = outcome = None
    try:
        session, adapter = module.initial_session(), Adapter(module)
        module.attach_observations(session, module.RUN, log)
        declared_entry(session)
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=module.RUN), store, log) as url:
            loop = runner.Loop(module.RUN, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(manifest['source_sha256']), initial=manifest['initial'])
            outcome = loop.execute(session)
            module.base.pilot.health(module.RUN)
    except BaseException as problem:
        error = problem
        log.append('attempt_stopped', dict(error_type=type(problem).__name__, error=str(problem)),
            [store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))])
        if session is not None:
            for name, raw in (('stopped-state.json', canonical_json_bytes(module.snapshot(session))),
                ('stopped-candidate.json', module.candidate_bytes(session.candidate)),
                ('stopped-preceding-feedback.json', canonical_json_bytes(adapter.preceding_feedback))):
                store.put(name, raw)
    finally:
        records, files = verify_records(module.RUN / 'records.jsonl', module.RUN), RUNTIME.file_inventory(module.RUN)
        store.put('RESPONSE_SEAL.json', canonical_json_bytes(dict(
            disposition='stopped_without_retry' if error else outcome['disposition'], actor=module.ACTOR,
            source_sha256=manifest['source_sha256'], files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), record_count=len(records),
            sent_requests=sum(row['record_type'] == 'invocation_started' for row in records),
            returned_responses=sum(row['record_type'] == 'response_received' for row in records),
            processed_invocations=sum(row['record_type'] == 'invocation_completed' for row in records),
            inherited_requests=24, inherited_operations=37,
            actual_operations=session.calls_used if session else 37,
            new_operations=session.calls_used - 37 if session else 0,
            cumulative_requests_used=session.requests_used if session else 24,
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
