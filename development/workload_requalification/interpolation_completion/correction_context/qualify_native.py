"""Actual saved-state and oversized-region admission; zero model completions."""
import copy
from pathlib import Path
from types import SimpleNamespace

import study
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

execution = study.execution.execution
RUNTIME = execution.RUNTIME


def identities():
    task = study.qualified_task.Task()
    paths = [*study.AREA.glob('*.py'), study.AREA / 'PLAN.md', task.RUN / 'RESPONSE_SEAL.json']
    return {**task.source_identities(),
            **{p.relative_to(study.original.ROOT).as_posix():sha256_file(p) for p in paths}}


def main():
    folder = study.AREA / 'native-001'
    folder.mkdir(exist_ok=False)
    task, session, feedback = study.restored()
    store = ArtifactStore(folder)
    log = execution.legacy.QualificationLog(folder/'records.jsonl', 'correction-context-native', task_module=task)
    bound = identities()
    results, failure = {}, None
    adapter = execution.runner.Adapter(task)
    adapter.preceding_feedback = copy.deepcopy(feedback)
    before = copy.deepcopy(task.snapshot(session))
    try:
        server, model, _ = task.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop = execution.OriginalLoop(folder,store,log,url=url,task_module=adapter,
                                          source_check=lambda:task.verify_sources(bound))
            original_wire = (task.RUN/'calls/C64-wire-request.json').read_bytes()
            assert completion_request_bytes(adapter.request_for(session.view())) == original_wire
            results['baseline_tokens'] = loop.measure(session.view())
            assert results['baseline_tokens'] == 12536
            store.put('baseline-view.json', canonical_json_bytes(session.view()))
            assert session._fits_feedback(loop.measure)
            results['revised_tokens'] = loop.measure(session.view())
            source, = session.view()['working_set']['sources']
            assert (source['returned_start_line'],source['returned_end_line']) == (2204,2356)
            report = session.view()['latest_feedback']['result']['report']
            assert 'UnboundLocalError' in str(report) and not session.pairs[-1]['result']['passed']
            for key in ('candidate_id','pairs','ranges','saved','diffs','source_versions','delivered_sources'):
                assert task.snapshot(session)[key] == before[key], key
            store.put('revised-view.json', canonical_json_bytes(session.view()))
            store.put('revised-state.json', canonical_json_bytes(task.snapshot(session)))
            results['shown_region'] = {k:v for k,v in source.items() if k!='content'}
            results['real_check_observation'] = session.observations.read('CHK-0150')
            # Check current authority without solving the faulty tests. This
            # engineering-only comment change is not an actor contribution.
            session.mark_delivered(session.view())
            result = session.execute(dict(action='patch',path=source['path'],
                old='class InterpolationMissingOptionErrorTransportTestCase(unittest.TestCase):',
                new='class InterpolationMissingOptionErrorTransportTestCase(unittest.TestCase): # admission probe',
                expected_candidate_id=session.candidate.candidate_id,
                expected_file_sha256=source['file_sha256']), loop.measure)
            assert result['accepted']
            results['visible_successor_edit_accepted'] = True
            store.put('engineering-edit-result.json', canonical_json_bytes(result))

            _, stress, preceding = study.restored('after/C63-O01')
            adapter.preceding_feedback = preceding
            original_action = task.read(task.RUN/'calls/C63-host-result.json')['operations'][1]['action']
            replacement = ''.join('# ' + '\\"' * 175 + str(i) + '\n' for i in range(175)) + original_action['old']
            assert len(replacement.encode()) <= 65536
            action = dict(original_action, new=replacement)
            assert stress.execute(action, lambda view:0)['accepted']
            stress.enter_recovery('declared synthetic oversized-source qualification')
            start = len(stress.admissions)
            assert stress._fits_feedback(loop.measure)
            trials = stress.admissions[start:]
            assert any(r['prompt_tokens'] > 23808 for r in trials)
            assert stress.view()['working_set']['sources'] == []
            results['oversized'] = dict(replacement_bytes=len(replacement.encode()),
                largest_trial=max(r['prompt_tokens'] for r in trials),
                final_tokens=loop.measure(stress.view()),
                source_omitted=True, classification='synthetic admission probe, not task material or actor work')
            store.put('oversized-proposal.json',canonical_json_bytes(action))
            store.put('oversized-control-view.json',canonical_json_bytes(stress.view()))
            task.verify_sources(bound)
    except BaseException as error:
        failure = error
        store.put('FAILED.json',canonical_json_bytes(dict(type=type(error).__name__,message=str(error))))
    finally:
        results.update(completion_requests=0, source_sha256=bound,
                       port_free=RUNTIME.port_free(RUNTIME.PORT))
        store.put('RESULTS.json',canonical_json_bytes(results))
        execution.legacy.seal(folder,'failed_preserved' if failure else 'qualified_no_model_inference',
                              bound,completion_requests=0)
    if failure: raise failure
    print({k:v for k,v in results.items() if k not in ('source_sha256','real_check_observation')},flush=True)


if __name__=='__main__': main()
