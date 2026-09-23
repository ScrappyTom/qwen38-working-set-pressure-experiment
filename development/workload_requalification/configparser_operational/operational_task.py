"""Original configparser entry with the qualified operational reply contract."""
import copy
import importlib.util
from functools import lru_cache
from pathlib import Path

import bootstrap  # noqa: F401
import execution_task as previous
import operational_reply
from working_set_exp.jsonutil import load_json_strict, sha256_bytes, sha256_file
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
original, host, navigation = previous.original, previous.host, previous.navigation
ACTOR, SEED = previous.ACTOR, previous.SEED
MAX_REQUESTS, MAX_OPERATIONS = previous.MAX_REQUESTS, previous.MAX_OPERATIONS
DESCRIPTIONS, OWNER_DIRECTION = previous.DESCRIPTIONS, previous.OWNER_DIRECTION
NATIVE_CRITERIA = previous.NATIVE_CRITERIA
CPU_QUALIFIED = previous.CPU_QUALIFIED
NATIVE_QUALIFIED = AREA/'native-qualification-001'
DECODER = ROOT/'development/workload_requalification/action_lifecycle/preparation-001/native-forms'
DECODER_SEAL_SHA = 'bc0e1a74a2ee7ba652977ff6acfdb24cd8cf9068f29a067ebd5dad309cf6d567'
verified_package, cpu_bindings = previous.verified_package, previous.cpu_bindings


class Session(previous.Session):
    def reply_schema(self):
        return operational_reply.reply_schema(DESCRIPTIONS)


@lru_cache(maxsize=1)
def response_constraints():
    path=ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path)=='ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec=importlib.util.spec_from_file_location('configparser_operational_converter',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return dict(grammar=with_thinking(operational_reply.reply_grammar(DESCRIPTIONS,module.SchemaConverter)))


def decode_reply(content):
    return operational_reply.decode_reply(content,DESCRIPTIONS)


def expected_native(request):
    assert request['grammar']==response_constraints()['grammar'] and 'response_format' not in request
    envelope=copy.deepcopy(request)
    envelope['grammar']=previous.response_constraints()['grammar']
    return previous.expected_native(envelope)


def decoder_reuse_bindings():
    assert sha256_file(DECODER/'SEAL.json')==DECODER_SEAL_SHA, 'Pinned operational proof changed'
    seal=load_json_strict((DECODER/'SEAL.json').read_bytes())
    bindings,_,result=verified_package(DECODER,seal['source_sha256'],status='qualified_no_model_inference')
    bindings={**seal['source_sha256'],**bindings}
    assert result['status']=='passed' and result['model_inference_calls']==0 and result['checker_executions']==0
    assert (DECODER/'reply.gbnf').read_bytes()==response_constraints()['grammar'].encode()
    assert load_json_strict((DECODER/'reply-schema.json').read_bytes())==Task().reply_schema()['json_schema']['schema']
    import run_uncoached_contribution as runner
    module=Task();current=runner.Adapter(module).request_for(module.initial_session().view())
    old=load_json_strict((DECODER/'wire-request.json').read_bytes())
    assert {k:v for k,v in current.items() if k!='messages'}=={k:v for k,v in old.items() if k!='messages'}
    assert result['wire_sha256']==sha256_file(DECODER/'wire-request.json')
    assert result['grammar_sha256']==sha256_bytes(current['grammar'].encode())
    cases={r['name']:r for r in result['cases']}
    assert len(cases)==len(result['cases'])==31
    assert all(r['accepted_including_eos']==r['expected'] for r in cases.values())
    for name in ('explicit_patch','ordinary_json_replacement','literal_account_source','scope_public','account_only'):
        assert cases[name]['accepted_including_eos']
    for name in ('discussion_only','actual_C05_discussion_only','unsupported_check_after','scope_tests','scope_examples'):
        assert not cases[name]['accepted_including_eos']
    server,_,_=host.runtime_paths()
    for name,digest in result['binaries'].items():
        assert sha256_file(server.parent/name)==digest, name
    return bindings


def implementation_identities():
    paths=[*AREA.glob('*.py'),*sorted((AREA/'tests').glob('*.py')),
           AREA/'PLAN.md',AREA/'SPEC.md',AREA/'SYSTEM.txt',*sorted(AREA.glob('*TESTS*.log')),
           Path(operational_reply.__file__)]
    return {**previous.implementation_identities(),
            **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


def qualification_sources():
    return {**implementation_identities(),**cpu_bindings(),**decoder_reuse_bindings()}


def native_bindings():
    bindings,_,result=verified_package(NATIVE_QUALIFIED,qualification_sources(),status='qualified_no_model_inference')
    assert result['status']=='passed' and result['native_requests']>0
    assert result['checks_executed']==2 and result['completion_requests']==0
    assert result['starting_candidate']==original.STARTING_ID
    assert result['checker_sha256']==sha256_bytes(original.checker())
    assert result['actor']==ACTOR and result['maximum_requests']==MAX_REQUESTS and result['maximum_operations']==MAX_OPERATIONS
    assert set(result['criteria'])==set(NATIVE_CRITERIA) and all(v is True for v in result['criteria'].values())
    assert result['reference_material_in_initial_input'] is False
    return bindings


class Task(previous.Task):
    def __init__(self,version='001',replay_folder=None):
        super().__init__(version,replay_folder)
        self.AREA=AREA
        self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/f'run-{version}'
        self.MANIFEST=AREA/f'EXECUTION_MANIFEST-{version}.json'

    def initial_session(self):
        session=original.initial_session((self.replay_folder or AREA/'unexecuted')/'observations',
                                        replay=self.replay_folder is not None)
        session.__class__=Session
        assert (session.requests_used,session.calls_used)==(0,0)
        assert not session.pairs and not session.ranges and not session.saved and session.working_account() is None
        assert session.candidate.max_file_bytes==original.FILE_LIMIT
        assert (session.request_limit,session.call_limit)==(MAX_REQUESTS,MAX_OPERATIONS)
        return session

    def reply_schema(self):return operational_reply.reply_schema(DESCRIPTIONS)
    def operating_reference(self):return operational_reply.operating_reference(super().operating_reference())
    def response_constraints(self):return response_constraints()
    def expected_native(self,request):return expected_native(request)
    def source_identities(self):return {**qualification_sources(),**native_bindings()}
    def implementation_identities(self):return implementation_identities()
    def __getattr__(self,name):return globals()[name] if name in globals() else super().__getattr__(name)


def __getattr__(name):return getattr(previous,name)
