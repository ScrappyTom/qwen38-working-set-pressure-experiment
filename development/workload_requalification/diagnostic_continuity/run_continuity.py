"""Qualified diagnostic continuation, with cumulative accounting and no coaching."""
import argparse
import copy
import json
from types import SimpleNamespace

import bootstrap
import continuity_task as study
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

controller=load_helper('diagnostic_continuation_controller','development/workload_requalification/action_lifecycle/run_continuation.py')
controller.INHERITED_REQUESTS,controller.INHERITED_OPERATIONS=40,60
runner=controller.runner
BaseAdapter=runner.Adapter


class Adapter(BaseAdapter):
    def __init__(self,module):
        super().__init__(module)
        self.preceding_feedback=copy.deepcopy(module.initial_preceding_feedback())


runner.Adapter=Adapter


def prepare(module):
    folder=module.PACKAGE
    folder.mkdir(exist_ok=False)
    bound=module.source_identities()
    store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','diagnostic-continuity-preparation',task_module=module)
    session,adapter=module.initial_session(),Adapter(module)
    initial,trials,error=None,[],None
    try:
        proof=study.previous.decoder_reuse_bindings()
        request=adapter.request_for(session.view())
        qualified=study.previous.read(study.previous.DECODER/'wire-request.json')
        assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in qualified.items() if k!='messages'}
        store.put('decoder-reuse.json',canonical_json_bytes(dict(cases=31,
            seal_sha256=study.previous.DECODER_SEAL_SHA,bindings=proof,
            grammar_sha256=sha256_bytes(request['grammar'].encode()),completion_requests=0)))
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,
                source_check=lambda:module.verify_sources(bound))
            assert loop.measure(session.view())<=23808
            selected=loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial={k:selected[k] for k in controller.INITIAL_KEYS}
            loop.snapshot(session,'starting')
            store.put('initial-wire-request.json',completion_request_bytes(request))

            # Actual known failed state and subsequent search; no checker is rerun.
            counter=study.restore('after/C36-O02')
            wire=study.previous.read(study.OLD/'calls/C37-wire-request.json')
            adapter.preceding_feedback=json.loads(wire['messages'][-1]['content'])['preceding_operation_feedback']
            before=counter.view()
            count=loop.measure(before)
            assert count<=23808 and before['verification']['checks']['public']['assessment']['diagnostics_shown']==3
            store.put('counterfactual-failure-view.json',canonical_json_bytes(before))
            trials.append(dict(stage='all-three-live-diagnostics',tokens=count,source='actual CHK-0054',model_requests=0))
            counter.mark_delivered(before)
            counter.execute(dict(action='search',path='Lib/configparser.py',query='MultilineContinuationError',offset=0,limit=16),loop.measure)
            adapter.preceding_feedback=[]
            after=counter.view()
            assert after['verification']==before['verification']
            count=loop.measure(after);assert count<=23808
            store.put('counterfactual-after-search-view.json',canonical_json_bytes(after))
            trials.append(dict(stage='standing-three-after-search',tokens=count))

            adapter.preceding_feedback=module.initial_preceding_feedback()
            module.attach_observations(session,folder,log)

            def action(tag,operation,justification):
                view=session.view()
                store.put(tag+'-input-view.json',canonical_json_bytes(view))
                store.put(tag+'-justification.txt',justification.encode())
                session.mark_delivered(view)
                result=module.process_reply(session,dict(operation=operation),loop.measure,adapter.preceding_feedback)
                assert all(r['result']['accepted'] for r in result['operations']),result
                count=loop.measure(session.view());assert count<=23808 and not session.delivery_blocked
                store.put(tag+'-outcome.json',canonical_json_bytes(result))
                store.put(tag+'-view.json',canonical_json_bytes(session.view()))
                trials.append(dict(stage=tag,tokens=count,operations=len(result['operations'])))
                return result

            def patch(tag,path,old,new,why):
                return action(tag,dict(action='patch',path=path,old=old,new=new,
                    expected_candidate_id=session.candidate.candidate_id,
                    expected_file_sha256=session.candidate.file_sha256(path)),why)

            action('current-failed-check',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
                'Current candidate differs from the only recorded check; the task requests a current public check.')
            assert not session.last['result']['passed']
            assessment=session.view()['verification']['checks']['public']['assessment']
            assert {r['criterion'] for r in assessment['diagnostics']}=={'contract.execution','candidate_tests.execution'}
            last=next(row for row in assessment['diagnostics'] if 'test_read_file_raises' in row['test']['text'])
            action('direct-error-detail',last['inspect'],
                'The presented error contains its direct structured inspection address; inspect that exact diagnostic.')
            patch('restore-raw-line','Lib/configparser.py',"fpname, lineno, line.rstrip('\\n'))",'fpname, lineno, line)',
                'Task requires the exact offending line; the independent contract shows the removed newline. The raise site is visible.')
            patch('correct-line-expectation','Lib/test/test_configparser.py',
                "self.assertEqual(cm.exception.line, '    continuation')", "self.assertEqual(cm.exception.line, '    continuation\\n')",
                'The task and actual contract failure require the raw newline; the complete authored assertion is visible.')
            patch('preserve-multiline-expectation','Lib/test/test_configparser.py',
                "self.assertEqual(parser.get('sec', 'key'), 'first line second line')", "self.assertEqual(parser.get('sec', 'key'), 'first line\\nsecond line')",
                'The task preserves existing multiline values; the actual candidate test diagnostic supplies the returned newline-separated value.')
            found=action('find-supported-file-helper',dict(action='search',path='Lib/test/test_configparser.py',query='os_helper.TESTFN',offset=0,limit=1),
                'Researcher-selected API alternative to the reported absent mkstemp; search existing tests for its actual usage before using it.')
            hit=found['operations'][-1]['result']['matches'][0]
            action('read-supported-file-helper',dict(action='read',path=hit['path'],start_line=max(1,hit['line']-3),end_line=hit['line']+8),
                'Read the real search location to verify how the existing suite names temporary files.')
            patch('correct-file-helper','Lib/test/test_configparser.py','fd, fname = os_helper.mkstemp()','fname = os_helper.TESTFN',
                'The old helper does not exist according to the real diagnostic. Existing test source demonstrates TESTFN; the changed method remains visible.')
            old=('   Exception raised when a continuation line (a line beginning with\n'
                 '   whitespace) follows an option that has no value.  This condition is\n'
                 '   only possible when :attr:`!allow_no_value` is ``True``.  Subclass of\n'
                 '   :exc:`ParsingError`.')
            new=('   Exception raised when a nonblank, non-comment continuation line is\n'
                 '   indented more deeply than the preceding valueless option. This\n'
                 '   applies when the *allow_no_value* constructor argument is ``True``.\n'
                 '   Subclass of :exc:`ParsingError`. The original offending line,\n'
                 '   including its line ending when present, is retained.')
            # Acquire the governing parser conditions, not merely the document anchor.
            action('read-continuation-conditions',dict(action='read',path='Lib/configparser.py',start_line=989,end_line=1070),
                'The prior actual search identifies _read and its extent; inspect the surrounding comment/blank and indentation conditions before revising prose.')
            patch('precise-documentation','Doc/library/configparser.rst',old,new,
                'The inspected _read conditions distinguish blank/comment handling and greater indentation; constructor wording is supported by the visible library header.')
            action('corrected-public-check',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
                'All repairs are saved; execute the unchanged acceptance on their actual successor.')
            assert session.last['result']['passed']
            action('checked-submission',dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
                'The current public check passed; submission names its exact unchanged candidate.')
            assert session.submitted
            loop.snapshot(session,'scripted-final')
            module.verify_sources(bound)
    except BaseException as exc:
        error=exc
        study.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        starts=list((folder/'observations').glob('*/started.json'))
        study.save(folder,'QUALIFICATION.json',dict(initial=initial,trials=trials,completion_requests=0,
            inherited_requests=40,inherited_operations=60,maximum_new_requests=16,maximum_new_operations=48,
            observed_check_directories=len(starts),inherited_observation_count=1,
            new_checks_executed=max(0,len(starts)-1),
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    study.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,
        maximum_requests=56,maximum_operations=108,source_sha256=bound,
        preparation_seal_sha256=sha256_file(folder/'SEAL.json'),preparation_package=folder.name,initial=initial,
        owner_direction=study.OWNER_DIRECTION,inherited_requests=40,inherited_operations=60,
        maximum_new_requests=16,maximum_new_operations=48,no_live_coaching=True,automatic_retry=False))
    runner.verify_package(module)
    print(json.dumps(dict(status='qualified',initial=initial,trials=len(trials),model_requests=0)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','run'));parser.add_argument('--version',default='001')
    args=parser.parse_args();module=study.Task(args.version)
    if args.mode=='prepare':prepare(module)
    else:runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,manifest_sha256=sha256_file(module.MANIFEST)),module)
