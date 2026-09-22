"""Finite operational continuation; preserve inherited request numbering."""
import argparse
import json
from types import SimpleNamespace

import bootstrap  # noqa: F401
import continuation_task as study
import native_forms
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

# Load an isolated module namespace. Historical runner users retain their Loop.
runner = load_helper('operational_continuation_runner', 'scripts/run_uncoached_contribution.py')
OrdinaryLoop = runner.Loop
INHERITED_REQUESTS, INHERITED_OPERATIONS = 5, 5
OWNER_DIRECTION = 'Continue the authorized repair/qualify/run programme, preserving consumed allowances and uncoached execution.'
INITIAL_KEYS = ('prompt_tokens', 'request_sha256', 'native_sha256', 'wire_request_sha256')


class ContinuationLoop(OrdinaryLoop):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sent = INHERITED_REQUESTS

    def invoke(self, session):
        # The inherited loop checks its frozen first input only at offset zero.
        if self.sent == INHERITED_REQUESTS and self.initial:
            self.measure(session.view())
            key = sha256_bytes(canonical_json_bytes(self.task.request_for(session.view())))
            selected = self.cache[key]
            self.task.require(all(selected[k] == self.initial[k] for k in INITIAL_KEYS),
                              'continuation first input differs from qualification')
        return super().invoke(session)

    def execute(self, session):
        self.task.require(self.sent == session.requests_used == INHERITED_REQUESTS
                          and session.calls_used == INHERITED_OPERATIONS,
                          'continuation consumed allowance differs')
        self.log.append('continuation_accounting_started', dict(
            inherited_requests=INHERITED_REQUESTS, inherited_operations=INHERITED_OPERATIONS,
            cumulative_request_limit=self.task.MAX_REQUESTS,
            cumulative_operation_limit=session.call_limit,
            maximum_new_requests=self.task.MAX_REQUESTS-INHERITED_REQUESTS,
            maximum_new_operations=session.call_limit-INHERITED_OPERATIONS), [])
        try:
            return super().execute(session)
        finally:
            self.log.append('continuation_accounting_closed', dict(
                inherited_requests=INHERITED_REQUESTS, inherited_operations=INHERITED_OPERATIONS,
                new_dispatches=self.sent-INHERITED_REQUESTS,
                cumulative_requests=self.sent, displayed_requests_used=session.requests_used,
                new_operations=session.calls_used-INHERITED_OPERATIONS,
                cumulative_operations=session.calls_used,
                task_loop_completed_totals_are_cumulative=True,
                response_seal_dispatch_totals_are_new=True), [])


runner.Loop = ContinuationLoop


def verify_preparation(module):
    manifest = runner.verify_package(module)
    expected = dict(inherited_requests=5,inherited_operations=5,
        maximum_new_requests=19,maximum_new_operations=67,
        request_numbering='cumulative C06 through C24',no_live_coaching=True,automatic_retry=False)
    module.require(all(manifest.get(key)==value for key,value in expected.items()),
                   'continuation manifest accounting differs')
    qualification = module.read(module.PACKAGE/'QUALIFICATION.json')
    native = module.read(module.PACKAGE/'native-forms/RESULTS.json')
    request = runner.Adapter(module).request_for(module.initial_session().view())
    module.require(qualification['completion_requests']==0 and qualification['checks_executed']==1
                   and not qualification['checker_starts_without_outcomes']
                   and qualification['initial']==manifest['initial']
                   and all(qualification.get(key)==expected[key] for key in
                       ('inherited_requests','inherited_operations','maximum_new_requests','maximum_new_operations')),
                   'incomplete route qualification')
    module.require(native['status']=='passed' and native['completion_requests']==0
                   and native['model_inference_calls']==0 and native['checker_executions']==0
                   and native['wire_sha256']==sha256_bytes(completion_request_bytes(request))
                   and native['grammar_sha256']==sha256_bytes(request['grammar'].encode())
                   and native['cases'] and all(row['accepted_including_eos']==row['expected']
                                              for row in native['cases']),
                   'native operational contract was not qualified')
    return manifest


def prepare(module):
    folder = module.PACKAGE
    folder.mkdir(exist_ok=False)
    bound = module.source_identities()
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl', 'operational-receipt-preparation', task_module=module)
    session, adapter = module.initial_session(), runner.Adapter(module)
    initial, trials, error, native = None, [], None, None
    try:
        request = adapter.request_for(session.view())
        native = native_forms.qualify(folder/'native-forms', task=module, request=request,
                                     source_identities=module.source_identities)
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = ContinuationLoop(folder, store, log, url=url, task_module=adapter,
                                    source_check=lambda: module.verify_sources(bound))
            view = session.view()
            count = loop.measure(view)
            assert count <= 23808
            selected = loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial = {key:selected[key] for key in INITIAL_KEYS}
            loop.snapshot(session, 'starting')
            store.put('initial-wire-request.json', completion_request_bytes(request))
            trials.append(dict(stage='continuation-entry', tokens=count, requests_used=session.requests_used,
                               operations_used=session.calls_used))
            session.observations = ObservationStore(folder/'scripted-observations')

            def action(tag, operation):
                session.mark_delivered(session.view())
                reply = dict(discussion='Researcher-scripted engineering qualification.', operation=operation)
                result = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
                count = loop.measure(session.view())
                assert all(row['result']['accepted'] for row in result['operations']), result
                assert count <= 23808 and not session.delivery_blocked
                store.put(tag+'-view.json', canonical_json_bytes(session.view()))
                store.put(tag+'-outcome.json', canonical_json_bytes(result))
                trials.append(dict(stage=tag, tokens=count, operations=len(result['operations'])))

            # Explicit feasibility route, not supplied to Qwen. Its target and
            # replacement are the unchanged task's researcher reference repair.
            path = module.legacy.TARGET
            text = session.candidate.file_map[path].decode()
            start = text[:text.index(module.legacy.BAD)].count('\n')+1
            end = start+len(module.legacy.BAD.splitlines())-1
            action('source', dict(action='work_on', sources=[dict(path=path,start_line=start,end_line=end)],results=[]))
            action('repair', dict(action='patch',path=path,old=module.legacy.BAD,new=module.legacy.GOOD,
                expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(path)))
            assert session.last['action_summary']['action']=='patch'
            action('successor-check', dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id))
            assert session.last['result']['passed']
            action('submit', dict(action='submit',expected_candidate_id=session.candidate.candidate_id))
            assert session.submitted and session.calls_used==INHERITED_OPERATIONS+4
            module.verify_sources(bound)
    except BaseException as exc:
        error = exc
        module.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        starts = sorted((folder/'scripted-observations').glob('*/started.json'))
        outcomes = sorted((folder/'scripted-observations').glob('*/outcome.json'))
        module.save(folder,'QUALIFICATION.json',dict(initial=initial,trials=trials,completion_requests=0,
            native_cases=len(native['cases']) if native else None,
            checks_executed=len(outcomes),checker_starts=len(starts),
            checker_starts_without_outcomes=[p.parent.name for p in starts if not (p.parent/'outcome.json').exists()],
            inherited_requests=5,inherited_operations=5,maximum_new_requests=19,maximum_new_operations=67,
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:
        raise error
    module.save(module.AREA,module.MANIFEST.name,dict(actor=module.ACTOR,seed=module.SEED,
        maximum_requests=module.MAX_REQUESTS,maximum_operations=module.MAX_OPERATIONS,
        source_sha256=bound,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),
        preparation_package=folder.name,initial=initial,owner_direction=OWNER_DIRECTION,
        starting_candidate=module.initial_session().candidate.candidate_id,
        inherited_requests=5,inherited_operations=5,maximum_new_requests=19,maximum_new_operations=67,
        request_numbering='cumulative C06 through C24',no_live_coaching=True,automatic_retry=False))
    verify_preparation(module)
    print(json.dumps(dict(initial=initial,trials=trials)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    module=study.Task(args.version)
    if args.mode=='prepare':
        prepare(module)
    else:
        verify_preparation(module)
        runner.run_once(SimpleNamespace(owner_direction=OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)),module)
