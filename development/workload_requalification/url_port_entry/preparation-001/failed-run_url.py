"""Prepare, then execute one separately published uncoached URL-port attempt."""
import argparse
import json
from types import SimpleNamespace

import bootstrap
import url_task as study
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT

runner = load_helper('url_entry_common_runner', 'scripts/run_uncoached_contribution.py')
native = load_helper('url_entry_native_forms', 'development/workload_requalification/action_lifecycle/native_forms.py')
INITIAL_KEYS = ('prompt_tokens', 'request_sha256', 'native_sha256', 'wire_request_sha256')


def prepare(module):
    folder = module.PACKAGE
    folder.mkdir(parents=True, exist_ok=False)
    bound = {}
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder / 'records.jsonl', task_module=module)
    session, adapter = None, None
    initial, forms, route, error, entry_verified = None, None, None, None, False
    try:
        bound = module.source_identities()
        session, adapter = module.initial_session(), runner.Adapter(module)
        module.attach_observations(session, folder, log)
        assert session.candidate.candidate_id == module.STARTING_ID
        assert not session.pairs and not session.ranges and not session.saved and session.working_account() is None
        assert session.requests_used == session.calls_used == session.starting_archive_length == 0
        assert (session.request_limit, session.call_limit) == (module.MAX_REQUESTS, module.MAX_OPERATIONS)
        entry_verified = True
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(bound))
            request = adapter.request_for(session.view())
            count = loop.measure(session.view())
            assert count <= INPUT_LIMIT
            selected = loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial = {key: selected[key] for key in INITIAL_KEYS}
            loop.snapshot(session, 'starting')
            store.put('initial-wire-request.json', completion_request_bytes(request))
            forms = native.qualify(folder / 'native-forms', task=module, request=request,
                source_identities=module.implementation_identities)
            assert forms['completion_requests'] == forms['model_inference_calls'] == forms['checker_executions'] == 0
            route = qualification_route.qualify(module, loop, adapter, store, folder)
            # Evaluator work takes place in independent sessions, not the prospective entry.
            assert session.candidate.candidate_id == module.STARTING_ID and not session.pairs
            assert not session.ranges and not session.saved and session.working_account() is None
            assert session.requests_used == session.calls_used == 0
            module.verify_sources(bound)
    except BaseException as problem:
        error = problem
        store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))
    finally:
        store.put('QUALIFICATION.json', canonical_json_bytes(dict(status='failed' if error else 'qualified',
            initial=initial, forms=forms, route=route, completion_requests=0,
            starting_candidate=module.STARTING_ID, actor=module.ACTOR, seed=module.SEED,
            maximum_requests=module.MAX_REQUESTS, maximum_operations=module.MAX_OPERATIONS,
            checker_contracts=study.checkers.contracts(),
            empty_initial_archive_selection_account=entry_verified,
            reference_material_in_initial_input=False,
            memory=RUNTIME.memory_stats(folder / 'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT))))
        legacy.seal(folder, log, 'failed_preserved' if error else 'qualified_no_model_inference', bound,
            completion_requests=0)
    if error:
        raise error
    manifest = dict(actor=module.ACTOR, seed=module.SEED, maximum_requests=module.MAX_REQUESTS,
        maximum_operations=module.MAX_OPERATIONS, source_sha256=bound, initial=initial,
        preparation_seal_sha256=sha256_file(folder / 'SEAL.json'), owner_direction=module.OWNER_DIRECTION,
        starting_candidate_id=module.STARTING_ID, starting_archive_operations=0,
        selection_assistance='none; empty selected source/result group and no account',
        literal_source_reply=True, automatic_edit_checks={module.TEST: 'tests', module.DOC: 'public'},
        checker_contracts=study.checkers.contracts(), no_coaching=True, no_retry=True)
    with module.MANIFEST.open('xb') as stream:
        stream.write(canonical_json_bytes(manifest))
    runner.verify_package(module)
    print(json.dumps(dict(status='qualified', package=str(folder), manifest=str(module.MANIFEST),
        initial=initial, completion_requests=0)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = study.Task(args.version)
    if args.mode == 'prepare':
        prepare(module)
    else:
        runner.run_once(SimpleNamespace(owner_direction=module.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)), module)
