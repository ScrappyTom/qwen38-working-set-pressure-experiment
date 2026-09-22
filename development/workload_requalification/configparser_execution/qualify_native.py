"""Task-specific host rehearsal; default preflight forbids runtime/checker use.

Native mode is parent-scheduled: template/tokenizer calls and exactly two real
public checks, never model completions. Reference edits are evaluator proposals;
the initial actor input contains none of them. No automatic retry.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import execution_task as task
import run_uncoached_contribution as runner
from manage import RUNTIME,legacy
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore,verify_records
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict,sha256_bytes,sha256_file
from working_set_exp.observations import ObservationStore

LIMIT=23808
LIB='Lib/configparser.py'
TEST='Lib/test/test_configparser.py'
DOC='Doc/library/configparser.rst'
REFERENCE=task.original.ORIGINAL/'REFERENCE_EDITS.json'


def reference_rows():
    value=load_json_strict(REFERENCE.read_bytes())
    assert value['kind']=='offline_preparation_only_never_actor_input'
    assert len(value['rows'])==6
    return value['rows']


def preflight():
    """Verify custody, decoder reuse and proposals without executing them."""
    with (patch('subprocess.Popen',side_effect=AssertionError('Preflight forbids subprocesses')),
          patch.object(task.host.base.base,'post',side_effect=AssertionError('Preflight forbids endpoints'))):
        bound=task.qualification_sources()
        module=task.Task();session=module.initial_session();adapter=runner.Adapter(module)
        initial=adapter.request_for(session.view())
        assert session.candidate.candidate_id==task.original.STARTING_ID
        assert session.candidate.max_file_bytes==task.original.FILE_LIMIT
        assert not session.pairs and not session.ranges and not session.saved
        assert session.working_account() is None and session.edit_checks=={}
        assert load_json_strict(initial['messages'][1]['content'].encode())==dict(
            workspace=session.view(),preceding_operation_feedback=[])
        assert all('REFERENCE_EDITS' not in m['content'] and 'reference-candidate' not in m['content'] for m in initial['messages'])
        assert {k:v for k,v in initial.items() if k!='messages'}=={
            k:v for k,v in load_json_strict((task.host.AREA/'native-005/wire-request.json').read_bytes()).items() if k!='messages'}
        files=session.candidate.file_map
        for row in reference_rows():
            old,new=row['old'].encode(),row['new'].encode()
            assert files[row['path']].count(old)==1
            files[row['path']]=files[row['path']].replace(old,new,1)
        reference=Candidate.create(files,max_file_bytes=task.original.FILE_LIMIT)
        result=load_json_strict((task.CPU_QUALIFIED/'RESULTS.json').read_bytes())
        expected=next(r['candidate_id'] for r in result['cases'] if r['case']=='correct_reference')
        assert reference.candidate_id==expected
        return bound,reference.candidate_id


def qualify(folder):
    bound,reference_id=preflight()
    module=task.Task();session=module.initial_session();adapter=runner.Adapter(module)
    folder.mkdir(exist_ok=False)
    store=ArtifactStore(folder)
    log=legacy.QualificationLog(folder/'records.jsonl','configparser-native-rehearsal',task_module=module)
    criteria={k:False for k in task.NATIVE_CRITERIA}
    decisions=[];checks=0;native_requests=0;error=None;health=None;broad=[];source_paths=set()

    def save(name,value):
        raw=value if isinstance(value,bytes) else canonical_json_bytes(value)
        artifact=store.put(name,raw)
        log.append('qualification_artifact',dict(name=name),[artifact])

    def preserved(record,artifacts):
        log.append('check_observation_preserved',record,
                   [{**r,'path':'observations/'+r['path']} for r in artifacts])

    session.observations=ObservationStore(folder/'observations',on_preserved=preserved)
    try:
        save('REFERENCE_CLASSIFICATION.json',dict(source=str(REFERENCE.relative_to(task.ROOT)),
            sha256=sha256_file(REFERENCE),reference_candidate=reference_id,
            classification='Evaluator-scripted feasibility, not autonomous discovery or a Qwen contribution.',
            initial_input_contains_reference=False,maximum_new_checker_executions=2))
        server,model,_=module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=runner.Loop(folder,store,log,url=url,task_module=adapter,
                             source_check=lambda:task.verify_sources(bound))

            def snapshot(label):
                view=session.view();count=loop.measure(view)
                assert count<=LIMIT and not session.delivery_blocked,(label,count)
                save(label+'-view.json',view)
                loop.snapshot(session,label)
                raw=load_json_strict((folder/(label+'-candidate.json')).read_bytes())
                assert raw['max_file_bytes']==task.original.FILE_LIMIT
                rebuilt=Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},
                                          max_file_bytes=raw['max_file_bytes'])
                assert rebuilt==session.candidate
                for source in view['working_set']['sources']:
                    source_paths.add(source['path'])
                    lines=session.candidate.file_map[source['path']].decode().splitlines(keepends=True)
                    exact=''.join(lines[source['returned_start_line']-1:source['returned_end_line']])
                    assert source['content']==exact
                    assert source['file_sha256']==session.candidate.file_sha256(source['path'])
                return count

            def perform(label,operation,basis,accepted=True):
                nonlocal checks
                assert session.calls_used<task.MAX_OPERATIONS
                adapter.preceding_feedback.clear()
                before=session.view();input_count=loop.measure(before)
                assert input_count<=LIMIT
                session.mark_delivered(before)
                save(label+'-before-view.json',before)
                if operation['action']=='check':
                    checks+=1;assert checks<=2
                result=session.execute(operation,loop.measure)
                assert result.get('accepted') is accepted,(label,result)
                save(label+'-operation.json',dict(operation=operation,result=result))
                after_count=snapshot(label)
                decisions.append(dict(label=label,operation=operation['action'],basis=basis,
                    before_view=label+'-before-view.json',after_view=label+'-view.json',
                    input_tokens=input_count,next_input_tokens=after_count,
                    accepted=result['accepted'],candidate_id=session.candidate.candidate_id,
                    mode=session.view()['presentation']['mode']))
                return result

            initial_count=snapshot('initial')
            initial=adapter.request_for(session.view())
            save('initial-wire-request.json',completion_request_bytes(initial))
            assert session.task==task.original.task_text() and not session.pairs
            assert session.view()['working_set']==dict(sources=[],saved_results=[])
            criteria['initial_native_input']=True
            criteria['public_only_decoder_forms']=True  # Byte-identical native-005 proof, verified in preflight.

            for label,path in [('root','.'),('library','Lib'),('tests','Lib/test'),('docs','Doc'),('reference-docs','Doc/library')]:
                perform('navigation-'+label,dict(action='tree',path=path,offset=0,limit=16),
                    'Root/current navigation and task identify these directories; returned entries identify the three target files.')
            criteria['original_source_navigation']=True

            failed=perform('baseline-check',dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
                'The unchanged public check can observe the original candidate; no repair or expected answer is supplied.')
            assert failed['executed'] and not failed['passed']
            observation=failed['observation']
            overview=session.view()['verification']['checks']['public']['assessment']
            assert session.view()['latest_feedback']['result']['report']==overview
            assert 'contract.execution' in overview['failed_criteria']
            raw=load_json_strict((session.observations.directory(observation)/'stdout.bin').read_bytes())
            trace=raw['contract']['details'][0]['trace']
            assert any(d['diagnostic'].get('text')==trace and d['diagnostic']['complete']
                for row in overview['criteria'] for d in row.get('diagnostics',[]))
            detail=perform('failure-detail',dict(action='inspect_check',observation=observation,offset=0),
                'The actual failed report supplies this observation and complete criterion-retrieval route.')
            assert any(d['diagnostic'].get('text')==trace and d['diagnostic']['complete']
                for row in detail['entries'] for d in row.get('diagnostics',[]))
            assert session.view()['latest_feedback']['result']==detail
            outcome=perform('failure-exact-outcome',dict(action='inspect_observation',observation=observation,stream='outcome',offset=0),
                'The check receipt supplies its exact observation identity; the outcome confirms scope, capture and execution.')
            expected=(session.observations.directory(observation)/'outcome.json').read_bytes()
            assert outcome['content'].encode()==expected and outcome['next_offset'] is None
            assert session.view()['verification']['checks']['public']['assessment']==overview
            criteria['standing_failure_after_later_action']=True

            # Plausible broad acquisition, not filler. Source pages are whatever
            # the host can actually admit; no preselected efficient group replaces it.
            next_line={LIB:1,TEST:1,DOC:1}
            for i,path in enumerate((LIB,TEST,DOC,LIB,TEST,DOC),1):
                label=f'broad-{i:02d}'
                adapter.preceding_feedback.clear();session.mark_delivered(session.view())
                op=dict(action='read',path=path,start_line=next_line[path],end_line=0)
                before=session.view();save(label+'-before-view.json',before)
                result=session.execute(op,loop.measure)
                save(label+'-operation.json',dict(operation=op,result=result))
                count=snapshot(label)
                broad.append(dict(path=path,accepted=result['accepted'],next_input_tokens=count,
                    mode=session.view()['presentation']['mode'],source=result.get('source')))
                decisions.append(dict(label=label,operation='read',basis='Discovered real task source; exploratory onward page, no promised full-file coverage.',
                    before_view=label+'-before-view.json',after_view=label+'-view.json',accepted=result['accepted']))
                if result.get('source'):
                    next_line[path]=result['source'].get('next_start_line') or result['source']['returned_end_line']+1
                if session.recovery or not result['accepted']:break
            # A truthful supported rejection is delivered even if the finite
            # exploratory sequence has not required the recovery arrangement.
            perform('broad-rejection',dict(action='read',path='missing-configparser-source.py',start_line=1,end_line=1),
                'Deliberate evaluator rejection-path probe; no claim that the task requires this nonexistent file.',accepted=False)

            def locate(label,path,query,function=False):
                result=perform(label,dict(action='search',path=path,query=query,offset=0,limit=16),
                    'The task or explicitly evaluator-authored proposal names this item; actual search supplies its current coordinates and fingerprint.')
                assert result['matches'] and result['regions'],(label,result)
                regions=result['regions']
                if function:
                    options=[r for r in regions if r.get('extent_kind')=='enclosing Python function']
                    if options:return options[0]['region_ref']
                return regions[0]['region_ref']

            parent=locate('recover-parse-error',LIB,'class ParsingError')
            perform('recover-selection',dict(action='work_on_exact',regions=[parent],results=[]),
                'The exact returned ParsingError context supports the task-required parent exception; replacement releases broad acquisition.')
            assert not session.recovery
            criteria['broad_selection_recovery']=True
            rows=reference_rows();changed=[]
            for i,row in enumerate(rows):
                path=row['path'];query=row['old'].splitlines()[0].strip()
                anchor=locate(f'edit-{i}-anchor',path,query,function=i==2)
                support=[]
                if i==1:
                    for j,query in enumerate(('class Error','class ParsingError','class MissingSectionHeaderError')):
                        support.append(locate(f'exception-interface-{j}',LIB,query))
                if i==3:
                    # Existing imports are first read, rather than supplied by the script.
                    read=perform('test-imports',dict(action='read',path=TEST,start_line=1,end_line=12),
                        'The existing test file determines available imports for the proposed regression.')
                    support.append(read['source']['region_ref'])
                if i>=3:
                    support.append(locate(f'edit-{i}-current-exception',LIB,'self.args = (source, lineno, line)',function=True))
                    support.append(locate(f'edit-{i}-current-guard',LIB,'raise MultilineContinuationError',function=True))
                perform(f'edit-{i}-source',dict(action='work_on_exact',regions=[anchor,*support],results=[]),
                    'Actual returned references select exact anchor plus required interfaces; proposals remain evaluator work, not model discovery.')
                visible=session.view()['working_set']['sources']
                assert any(s['path']==path and row['old'] in s['content'] for s in visible)
                before=session.candidate
                result=perform(f'edit-{i}',dict(action='patch',path=path,old=row['old'],new=row['new'],
                    expected_candidate_id=before.candidate_id,expected_file_sha256=before.file_sha256(path)),
                    'The qualified evaluator proposal is applied only after its exact current old text is delivered. Task and shown interfaces support its purpose.')
                assert result['previous_candidate_id']==before.candidate_id
                assert result['applied_diff']==session.diffs[len(session.pairs)]
                assert session.view()['latest_feedback']['applied_change']['diff_utf8']==result['applied_diff']
                assert not session.view()['verification']['checks']['public']['applies_to_current']
                changed.append(dict(path=path,before=before.candidate_id,after=session.candidate.candidate_id,
                                    result_handle=f'RES-{len(session.pairs):04d}'))
            criteria['read_to_edit_and_refresh']=True
            criteria['large_file_read_and_snapshot']={LIB,TEST,DOC}<=source_paths
            assert session.candidate.candidate_id==reference_id

            # Release source bodies, then retrieve the actual saved edit receipt.
            # This qualifies independent result access; it does not replay the edit.
            handle=changed[-1]['result_handle'];exact=session.payload(handle)
            perform('release-selection',dict(action='work_on',sources=[],results=[]),
                'The reference contribution has been saved; exact edit recovery is the next explicit engineering check.')
            recovered=perform('recover-exact-diff',dict(action='reopen_result',handle=handle,offset=0),
                'The accepted edit supplied this RES handle; retrieval returns its exact observation without mutation.')
            assert recovered['next_offset'] is None and recovered['exact_utf8'].encode()==exact
            assert load_json_strict(exact)['applied_diff']
            assert session.candidate.candidate_id==reference_id
            criteria['exact_diff_recovery']=True

            passed=perform('corrected-check',dict(action='check',check_id='public',expected_candidate_id=reference_id),
                'Actual saved library, tests and documentation now require verification on this exact successor.')
            assert passed['executed'] and passed['passed']
            assessment=session.view()['verification']['checks']['public']['assessment']
            assert assessment['failed_criteria']==[] and assessment['passed']
            actual=load_json_strict((session.observations.directory(passed['observation'])/'stdout.bin').read_bytes())
            assert actual['regression_detects_original'] and not actual['new_tests_on_original']['successful']
            assert all(actual[k]['successful'] for k in ('upstream','contract','candidate_tests'))
            criteria['ordinary_failure_and_correction']=True
            perform('submit',dict(action='submit',expected_candidate_id=reference_id),
                'The actual applicable public pass permits submission; documentation accuracy remains separately reviewed.')
            assert session.submitted and checks==2 and session.requests_used==0
            criteria['checked_contribution_and_submission']=True
            assert all(criteria.values()),criteria
            original_test=task.original.starting_candidate().file_map[TEST]
            assert session.candidate.file_map[TEST]==original_test.replace(rows[3]['old'].encode(),rows[3]['new'].encode(),1)
            assert rows[3]['old'] in rows[3]['new']
            save('REFERENCE_ARTIFACT.json',dict(candidate_id=reference_id,changes=changed,
                matches_previously_qualified_reference=True,documentation_accuracy_requires_direct_review=True,
                existing_test_text_preserved=(rows[3]['old'] in rows[3]['new']),
                evaluator_script_not_model_outcome=True))
            health=loop.health()
            assert loop.sent==0 and not any(r['record_type']=='invocation_started' for r in verify_records(folder/'records.jsonl',folder))
    except BaseException as exc:
        error=exc;save('FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        records=verify_records(folder/'records.jsonl',folder)
        native_requests=sum(r['record_type']=='native_request_started' for r in records)
        actual_checks=sum(r['record_type']=='check_observation_preserved' for r in records)
        save('DECISION_PATH.json',decisions)
        save('RESULTS.json',dict(status='failed_preserved' if error else 'passed',criteria=criteria,
            completion_requests=0,native_requests=native_requests,checks_executed=actual_checks,
            checks_requested=checks,native_input_measurements=sum(r['record_type']=='native_input_prepared' for r in records),
            starting_candidate=task.original.STARTING_ID,checker_sha256=sha256_bytes(task.original.checker()),
            actor=task.ACTOR,maximum_requests=task.MAX_REQUESTS,maximum_operations=task.MAX_OPERATIONS,
            actual_operations=session.calls_used,model_requests_used=session.requests_used,
            reference_material_in_initial_input=False,reference_candidate=reference_id,
            classification='Native host feasibility using evaluator reference work; no model performance evidence.',
            broad_acquisition=broad,runtime_health=health,memory=RUNTIME.memory_stats(folder/'memory.csv'),
            port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    print(json.dumps(dict(status='passed',native_requests=native_requests,checks_executed=checks,
                          operations=session.calls_used,completion_requests=0)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('preflight','native'),default='preflight',nargs='?')
    parser.add_argument('--folder',default='native-qualification-001')
    args=parser.parse_args()
    if args.mode=='preflight':
        bound,reference=preflight()
        print(json.dumps(dict(status='preflight_passed',sources=len(bound),reference_candidate=reference,
            native_requests=0,checks_executed=0,completion_requests=0)),flush=True)
    else:
        if Path(args.folder).name!=args.folder or args.folder in ('','.','..'):
            raise ValueError('Use one new qualification folder name')
        qualify(task.AREA/args.folder)
