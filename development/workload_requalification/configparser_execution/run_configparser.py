"""Guarded initial-input preparation or finite run; no implicit execution on import."""
import argparse
import json
from types import SimpleNamespace

import execution_task as study
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def prepare(module):
    # Native information-path/decoder qualification precedes even this initial
    # render. No old small-repair qualification can satisfy this task-specific gate.
    bound=module.source_identities()
    folder=module.PACKAGE;folder.mkdir(exist_ok=False)
    store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','configparser-original-preparation',task_module=module)
    session,adapter=module.initial_session(),runner.Adapter(module)
    initial=None;error=None
    try:
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,
                source_check=lambda:study.verify_sources(bound))
            view=session.view();assert loop.measure(view)<=23808
            selected=next(iter(loop.cache.values()))
            initial={k:selected[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json',completion_request_bytes(adapter.request_for(view)))
            assert session.candidate.candidate_id==study.original.STARTING_ID and not session.pairs
            assert not session.ranges and not session.saved and session.working_account() is None
    except BaseException as exc:
        error=exc;study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,completion_requests=0,
            checks_executed=0,native_information_path_prerequisite=str(study.NATIVE_QUALIFIED.relative_to(study.ROOT)),
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,
        maximum_requests=module.MAX_REQUESTS,maximum_operations=module.MAX_OPERATIONS,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),
        preparation_package=folder.name,initial=initial,owner_direction=study.OWNER_DIRECTION,
        starting_candidate=study.original.STARTING_ID,inherited_operations=0,
        no_live_coaching=True,automatic_retry=False,subsequent_declared_attempts_authorized=True))
    runner.verify_package(module)
    print(json.dumps(dict(case=module.case,initial=initial,completion_requests=0)),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--version',default='001')
    args=parser.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:
        module.source_identities()  # Fail before runtime if prerequisites changed.
        runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)),module)


if __name__=='__main__':main()
