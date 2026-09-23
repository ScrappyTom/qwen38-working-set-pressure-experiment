"""Actual-input sizing and recorded-check replay, never model inference."""
import argparse,copy,json
from types import SimpleNamespace
import qualification as q
import run_continuity as driver
from manage import RUNTIME,legacy
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes

class Adapter(driver.runner.Adapter):
    wire=None
    def request_for(self,view):
        value=copy.deepcopy(self.wire)
        user=json.loads(value['messages'][-1]['content'])
        user['workspace']=view
        from working_set_exp import decision_view
        user['preceding_operation_feedback']=decision_view.present_receipts(view,self.preceding_feedback)
        value['messages'][-1]['content']=canonical_json_bytes(user).decode()
        return value

def main(version):
    folder=q.AREA/f'qualification-{version}';folder.mkdir(exist_ok=False)
    bound=q.bindings();store=ArtifactStore(folder);module=q.previous.Task()
    log=legacy.QualificationLog(folder/'records.jsonl','recovery-chronology-native',task_module=module)
    adapter=Adapter(module);trials=[];error=None
    server,model,_=module.runtime_paths()
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            loop=driver.runner.Loop(folder,store,log,url=url,task_module=adapter,source_check=lambda:module.verify_sources(bound))
            for case in ('documentation-C52','diagnostic-C48'):
                session,wire,run=q.restore(case)
                adapter.wire=wire
                adapter.preceding_feedback=copy.deepcopy(json.loads(wire['messages'][-1]['content'])['preceding_operation_feedback'])
                before=session.view(); original=json.loads(wire['messages'][-1]['content'])['workspace']
                assert before==original,'restored input differs'
                assert adapter.request_for(before)==wire,'saved request envelope differs'
                before_tokens=loop.measure(before)
                frozen=canonical_json_bytes(q.previous.snapshot(session))
                session.__class__=q.Session
                assert session._fits_feedback(loop.measure)
                after=session.view();after_tokens=loop.measure(after)
                comparable=copy.deepcopy(after);comparable['recent_activity']=[]
                assert comparable==before,'required view changed'
                assert canonical_json_bytes(q.previous.snapshot(session))==frozen,'stored state changed'
                assert len(after['recent_activity'])==6 and after_tokens<=23808
                store.put(case+'-before.json',canonical_json_bytes(before))
                store.put(case+'-after.json',canonical_json_bytes(after))
                store.put(case+'-snapshot.json',canonical_json_bytes(q.snapshot(session)))
                trials.append(dict(case=case,before_tokens=before_tokens,after_tokens=after_tokens,rows=6,required_view_unchanged=True))
                if case=='diagnostic-C48':
                    # Actual public finals, independently known before this qualification.
                    # No unexecuted reasoning draft is extracted or supplied to a model.
                    for tag in ('C48','C49'):
                        session.mark_delivered(session.view());session.begin_request()
                        reply=q.previous.read(run/f'calls/{tag}-reply.json')
                        result=module.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
                        expected=q.previous.read(run/f'calls/{tag}-host-result.json')
                        assert result==expected,'recorded operation outcome differs'
                        store.put(case+'-'+tag+'-outcome.json',canonical_json_bytes(result))
                        store.put(case+'-'+tag+'-view.json',canonical_json_bytes(session.view()))
                        trials.append(dict(case=case,recorded_reply=tag,tokens=loop.measure(session.view()),new_check_executions=0))
                    assert session.submitted
            module.verify_sources(bound)
    except BaseException as exc:
        error=exc;q.previous.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        q.previous.save(folder,'RESULTS.json',dict(status='failed' if error else 'qualified',trials=trials,
            model_requests=0,new_check_executions=0,recorded_check_replays=1 if any(t.get('recorded_reply')=='C48' for t in trials) else 0,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:raise error
    print(json.dumps(trials,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='001');main(p.parse_args().version)
