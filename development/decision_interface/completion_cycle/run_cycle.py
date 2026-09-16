"""Qualify, freeze and execute one finite attempt under standing authorization."""
import argparse
import json
from types import SimpleNamespace

import cycle_task as study
from manage import RUNTIME, legacy
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def prepare(module):
    study.verify_sources(study.read(study.QUALIFIED/'SEAL.json')['source_sha256'])
    folder = module.PACKAGE
    folder.mkdir(parents=True, exist_ok=False)
    bound, store = module.source_identities(), ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl', 'completion-cycle-preparation', task_module=module)
    session, adapter = module.initial_session(), runner.Adapter(module)
    view = session.view()
    assert view['latest_feedback']['result']['match_count'] == 2
    assert len(view['latest_feedback']['result']['match_regions']) == 2
    assert view['working_account']['text_complete'] and not view['working_set']['sources']
    for region in view['latest_feedback']['result']['match_regions']:
        assert session.resolve_region(region['region_ref']) == {k: region[k] for k in ('path','start_line','end_line')}
    assert session.requests_used == 0 and session.calls_used == 0
    assert session.clone().view() == view
    server, model, _ = module.runtime_paths()
    error, initial = None, None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter,
                               source_check=lambda: study.verify_sources(bound))
            count = loop.measure(view)
            assert count <= 23808
            selected = next(iter(loop.cache.values()))
            initial = {k: selected[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session, 'starting')
            request = adapter.request_for(view)
            store.put('initial-wire-request.json', completion_request_bytes(request))
            store.put('initial-view.json', canonical_json_bytes(view))
            old = study.read(study.OLD/'calls/C05-wire-request.json')
            assert {k:v for k,v in request.items() if k!='messages'} == {k:v for k,v in old.items() if k!='messages'}
            assert request['messages'][0] == old['messages'][0]
            assert not any(r['record_type']=='invocation_started' for r in verify_records(folder/'records.jsonl', folder))
    except BaseException as problem:
        error = problem
        study.save(folder, 'FAILED.json', dict(type=type(problem).__name__, message=str(problem)))
    finally:
        study.save(folder, 'QUALIFICATION.json', dict(initial=initial, completion_requests=0,
            memory=RUNTIME.memory_stats(folder/'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound, completion_requests=0)
    if error:
        raise error
    study.save(study.AREA, module.MANIFEST.name, dict(actor=study.ACTOR, seed=study.SEED,
        maximum_requests=study.MAX_REQUESTS, maximum_operations=study.MAX_OPERATIONS,
        source_sha256=bound, preparation_seal_sha256=sha256_file(folder/'SEAL.json'),
        preparation_package=folder.name, initial=initial,
        qualification_seal_sha256=sha256_file(study.QUALIFIED/'SEAL.json'),
        owner_direction=study.OWNER_DIRECTION, starting_candidate=session.candidate.candidate_id,
        inherited_operations=len(session.pairs), no_live_coaching=True, automatic_retry=False,
        subsequent_declared_attempts_authorized=True))
    runner.verify_package(module)
    print(json.dumps(initial), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare','run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = study.Task(args.version)
    if args.mode == 'prepare':
        prepare(module)
    else:
        manifest = study.read(module.MANIFEST)
        module.PACKAGE = study.AREA/manifest['preparation_package']
        runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)), module)
