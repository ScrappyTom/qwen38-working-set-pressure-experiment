"""Native qualification and separately frozen remaining-budget continuation."""
import argparse
import copy
import json
from types import SimpleNamespace

import interpolation_continuation as study
import run_uncoached_contribution as runner
from manage import RUNTIME, legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def verify_interruption():
    seal = study.read(study.AUDIT)
    assert seal['original_run_unmodified'] and seal['classification'] == 'retrospective inventory, not original execution closure'
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files'] + seal['private_runtime_files_local_only']:
        path = study.OLD/row['path']
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
    study.verify_sources(seal['source_sha256'])


def reconstruct(stem, tag):
    old = study.restore(stem)
    adapter = runner.Adapter(study.previous.Task('002'))
    adapter.preceding_feedback = study.read(study.OLD/(stem+'-preceding-feedback.json'))
    wire = completion_request_bytes(adapter.request_for(old.view()))
    assert wire == (study.OLD/f'calls/{tag}-wire-request.json').read_bytes(), tag
    return old, adapter.preceding_feedback


def prepare(module):
    verify_interruption()
    cpu = study.AREA/'cpu-qualification-001'
    qualified = study.read(cpu/'SEAL.json')
    assert qualified['status'] == 'qualified_cpu_only'
    study.verify_sources(qualified['source_identities'])
    for name, digest in qualified['files'].items():
        assert sha256_file(cpu/name) == digest, name
    reconstruct(study.ENTRY, 'C22')
    folder = module.PACKAGE
    folder.mkdir(parents=True, exist_ok=False)
    bound = module.source_identities()
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl', 'interpolation-report-continuation-preparation', task_module=module)
    session, adapter = module.initial_session(), runner.Adapter(module)
    error, initial, trials = None, None, []
    try:
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop = runner.Loop(folder,store,log,url=url,task_module=adapter,
                source_check=lambda: study.verify_sources(bound))
            view = session.view()
            assert loop.measure(view) <= 23808
            first = next(iter(loop.cache.values()))
            initial = {k:first[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json',completion_request_bytes(adapter.request_for(view)))
            trials.append(dict(stage='continuation-entry',tokens=first['prompt_tokens'],model_requests=0))

            # Actual crowded states; retain their selection/account and observations.
            for stem, tag in [('after/C01-O01','C02'),('after/C02-O02','C03'),
                              ('after/C03-O02','C04'),('after/C13-O02','C14')]:
                old, feedback = reconstruct(stem,tag)
                old.__class__ = study.Session
                adapter.preceding_feedback = copy.deepcopy(feedback)
                before_pairs = canonical_json_bytes(old.pairs)
                before_ranges = copy.deepcopy(old.ranges)
                original_count = loop.measure(old.view())
                assert old._fits_feedback(loop.measure), tag
                assert canonical_json_bytes(old.pairs) == before_pairs and old.ranges == before_ranges
                count = loop.measure(old.view())
                store.put('counterfactual-'+tag+'-view.json',canonical_json_bytes(old.view()))
                trials.append(dict(stage='saved-'+tag,unadjusted_tokens=original_count,tokens=count,
                    recovery=old.recovery,selection_unchanged=True,archive_unchanged=True))
            adapter.preceding_feedback.clear()

            # Reference work remains qualification only, outside the actor entry.
            study.attach_observations(session,folder,log)
            def action(tag, operation):
                session.mark_delivered(session.view())
                result = module.process_reply(session,dict(discussion='Offline engineering qualification.',operation=operation),
                    loop.measure,adapter.preceding_feedback)
                count = loop.measure(session.view())
                assert count <= 23808 and not session.delivery_blocked
                assert all(r['result']['accepted'] for r in result['operations']), result
                store.put(tag+'-view.json',canonical_json_bytes(session.view()))
                store.put(tag+'-outcome.json',canonical_json_bytes(result))
                trials.append(dict(stage=tag,tokens=count,operations=len(result['operations'])))
            for tag,path,addition in [('tests',study.TEST,study.previous.legacy.AREA/'REFERENCE_TEST.py'),
                                      ('documentation',study.DOC,study.previous.legacy.AREA/'REFERENCE_DOC.txt')]:
                text=session.candidate.file_map[path].decode(); lines=text.splitlines(keepends=True)
                action(tag+'-anchor',dict(action='work_on',sources=[dict(path=path,start_line=len(lines)-8,end_line=len(lines))],results=[]))
                anchor=''.join(lines[-5:]); assert text.count(anchor)==1
                action(tag+'-edit',dict(action='patch',path=path,old=anchor,new=anchor+'\n\n'+addition.read_text(encoding='utf-8'),
                    expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(path)))
                assert session.last['result']['passed']
            action('submit',dict(action='submit',expected_candidate_id=session.candidate.candidate_id))
            assert session.submitted
    except BaseException as exc:
        error=exc
        study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,trials=trials,completion_requests=0,
            original_C22_reconstructed_exactly=True,memory=RUNTIME.memory_stats(folder/'memory.csv'),
            port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:
        raise error
    entry=module.initial_session()
    study.save(study.AREA,module.MANIFEST.name,dict(actor=study.ACTOR,seed=study.SEED,
        maximum_requests=study.MAX_REQUESTS,maximum_operations=study.MAX_OPERATIONS,source_sha256=bound,
        preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,
        initial=initial,owner_direction=study.OWNER_DIRECTION,starting_candidate=entry.candidate.candidate_id,
        inherited_archive_operations=len(entry.pairs),inherited_contribution_operations=entry.calls_used,
        inherited_request_accounting=study.ACCOUNTING,no_live_coaching=True,automatic_retry=False,
        subsequent_declared_attempts_authorized=True))
    runner.verify_package(module)
    print(json.dumps(dict(initial=initial,trials=trials)),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('prepare','run'));p.add_argument('--version',default='001')
    args=p.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':
        prepare(module)
    else:
        runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)),module)
