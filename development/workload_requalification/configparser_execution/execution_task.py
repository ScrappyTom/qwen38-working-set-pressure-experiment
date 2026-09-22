"""Original configparser entry on the qualified common contribution lifecycle."""
from functools import lru_cache
import copy
import importlib.util
from pathlib import Path
import re

import bootstrap
import configparser_task as original
import navigation
import repair_task as host
from working_set_exp import decision_view
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict,sha256_bytes,sha256_file
from working_set_exp.thinking_grammar import with_thinking

ROOT,AREA=original.ROOT,Path(__file__).resolve().parent
CPU_QUALIFIED=original.AREA/'checker-qualification-005'
NATIVE_QUALIFIED=AREA/'native-qualification-001'
ACTOR,SEED=dict(host.ACTOR),host.SEED
MAX_REQUESTS,MAX_OPERATIONS=40,80
DESCRIPTIONS=original.DESCRIPTIONS
OWNER_DIRECTION='Repeat the repair/qualify/run process until the previously tested workloads pass.'
NATIVE_CRITERIA=(
    'initial_native_input','public_only_decoder_forms','original_source_navigation',
    'large_file_read_and_snapshot','read_to_edit_and_refresh','exact_diff_recovery',
    'ordinary_failure_and_correction','standing_failure_after_later_action',
    'broad_selection_recovery','checked_contribution_and_submission',
)


class Session(navigation.NavigationMixin,original.Session):
    pass


def verified_package(folder,expected_sources,*,status,root=ROOT):
    """Check status, complete source closure and each sealed output before use."""
    folder,root=Path(folder).resolve(),Path(root).resolve()
    seal_path=folder/'SEAL.json';seal=load_json_strict(seal_path.read_bytes())
    assert seal['status']==status and seal['completion_requests']==0,'Qualification incomplete or exposed'
    assert seal['source_sha256']==expected_sources,'Qualification source closure differs'
    for name,digest in expected_sources.items():
        path=(root/name).resolve()
        assert path.is_relative_to(root),'Source path escapes project'
        assert sha256_file(path)==digest,'Qualification source changed: '+name
    rows=seal['files'];names=[r['path'] for r in rows]
    assert len(names)==len(set(names)) and 'RESULTS.json' in names,'Invalid qualification inventory'
    assert not any(Path(n).name in ('FAILED.json','FAILURE.txt') for n in names),'Failed qualification preserved'
    assert sha256_bytes(canonical_json_bytes(rows))==seal['aggregate_sha256'],'Qualification inventory differs'
    bindings={seal_path.relative_to(root).as_posix():sha256_file(seal_path)}
    for row in rows:
        path=(folder/row['path']).resolve()
        assert path.is_relative_to(folder) and path!=seal_path,'Output path escapes qualification'
        assert path.stat().st_size==row['size_bytes'] and sha256_file(path)==row['sha256'],row['path']
        bindings[path.relative_to(root).as_posix()]=row['sha256']
    result=load_json_strict((folder/'RESULTS.json').read_bytes())
    assert result['completion_requests']==0
    return bindings,seal,result


def cpu_bindings():
    bindings,seal,result=verified_package(CPU_QUALIFIED,original.source_identities(),status='qualified_cpu_only')
    assert seal['native_requests']==result['native_requests']==0
    assert result['status']=='qualified_cpu_only'
    assert result['original_checker_sha256']==original.CHECKER_SHA
    assert result['adapted_checker_sha256']==sha256_bytes(original.checker())
    expected={'original','correct_reference','exception_api_without_behavior',
              'rejects_valid_continuations','wrong_line_number','vacuous_added_test','documentation_unchanged'}
    rows={r['case']:r for r in result['cases']}
    assert len(rows)==len(result['cases'])==7 and set(rows)==expected
    assert all(r['acceptance_equivalent'] and r['assessment_in_immediate_and_standing_view']
               and r['passed'] is (name=='correct_reference') for name,r in rows.items())
    assert rows['original']['candidate_id']==original.STARTING_ID
    assert len(result['suite_edges'])==1 and result['suite_edges'][0]['case']=='unexpected_success'
    assert result['suite_edges'][0]['acceptance_equivalent'] and result['suite_edges'][0]['actual_runner_diagnostic_delivered']
    assert not result['suite_edges'][0]['passed']
    boundary_names={r['case'] for r in result['boundaries']}
    assert boundary_names=={'long_escaping','malformed','crash_after_partial','timeout_after_complete_looking_report',
        'capture_limit','nonzero_after_passing_report','unknown_success','lone_surrogate','zero_after_failed_report'}
    assert len(result['boundaries'])==len(boundary_names)
    return bindings


def implementation_identities():
    # Frozen CPU adapter sources remain untouched. Its reference work is custody
    # metadata for the evaluator, never an actor input or starting contribution.
    paths=[*AREA.glob('*.py'),*sorted((AREA/'tests').glob('*.py')),
           AREA/'PLAN.md',AREA/'SPEC.md',AREA/'SYSTEM.txt',
           ROOT/'development/workload_requalification/navigation_continuity/navigation.py',
           ROOT/'development/workload_requalification/navigation_continuity/PLAN.md',
           ROOT/'development/workload_requalification/navigation_continuity/SPEC.md',
           ROOT/'development/workload_requalification/small_repairs/repair_task.py']
    return {**original.source_identities(),**host.source_identities(),
            **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


def qualification_sources():
    return {**implementation_identities(),**cpu_bindings(),**decoder_reuse_bindings()}


def native_bindings():
    bindings,seal,result=verified_package(NATIVE_QUALIFIED,qualification_sources(),
                                        status='qualified_no_model_inference')
    assert result['status']=='passed' and result['native_requests']>0
    assert result['checks_executed']>=2,'Actual failure/correction checking route not qualified'
    assert result['starting_candidate']==original.STARTING_ID
    assert result['checker_sha256']==sha256_bytes(original.checker())
    assert result['actor']==ACTOR and result['maximum_requests']==MAX_REQUESTS and result['maximum_operations']==MAX_OPERATIONS
    assert set(result['criteria'])==set(NATIVE_CRITERIA) and all(v is True for v in result['criteria'].values())
    assert result['reference_material_in_initial_input'] is False
    return bindings


@lru_cache(maxsize=1)
def response_constraints():
    path=ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path)=='ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec=importlib.util.spec_from_file_location('configparser_execution_converter',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return dict(grammar=with_thinking(decision_view.reply_grammar(DESCRIPTIONS,module.SchemaConverter)))


def expected_native(request):
    assert request['grammar']==response_constraints()['grammar'] and 'response_format' not in request
    envelope=copy.deepcopy(request)
    envelope['grammar']=host.response_constraints()['grammar']
    return host.expected_native(envelope)


def decoder_reuse_bindings():
    """Reuse exact public-only grammar proof; do not rerun unchanged native cases."""
    folder=host.AREA/'native-005'
    bindings=host.repair_qualification.verify(ROOT,folder,
        host.Task('artifact_map').implementation_identities(),'native')
    raw=(folder/'reply.gbnf').read_bytes()
    assert raw==response_constraints()['grammar'].encode(),'Qualified grammar differs'
    old=load_json_strict((folder/'wire-request.json').read_bytes())
    assert old['grammar']==response_constraints()['grammar'] and 'response_format' not in old
    # The task contents change, while decoder and template/sampling controls do not.
    import run_uncoached_contribution as runner
    module=Task();current=runner.Adapter(module).request_for(module.initial_session().view())
    assert {k:v for k,v in current.items() if k!='messages'}=={k:v for k,v in old.items() if k!='messages'}
    assert module.reply_schema()==host.Task('artifact_map').reply_schema()
    result=load_json_strict((folder/'RESULTS.json').read_bytes())
    cases={row['name']:row for row in result['cases']}
    for name in ('explicit_patch','ordinary_json_replacement','account_source','scope_public'):
        assert cases[name]['accepted_including_eos'] is True
    for name in ('unsupported_check_after','scope_tests','scope_examples'):
        assert cases[name]['accepted_including_eos'] is False
    server,_,_=host.runtime_paths()
    for name,digest in result['binaries'].items():
        path=server.parent/name
        assert sha256_file(path)==digest,'Qualified decoder binary changed: '+name
    return bindings


class Task:
    def __init__(self,version='001',replay_folder=None):
        if not re.fullmatch(r'[0-9]{3}',version):
            raise ValueError('Version must be exactly three decimal digits')
        self.AREA=AREA;self.case='configparser_original'
        self.PACKAGE,self.RUN=AREA/f'preparation-{version}',AREA/f'run-{version}'
        self.MANIFEST=AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder=Path(replay_folder) if replay_folder is not None else None

    def initial_session(self):
        folder=(self.replay_folder or AREA/'unexecuted')/'observations'
        session=original.initial_session(folder,replay=self.replay_folder is not None)
        session.__class__=Session
        assert session.request_limit==MAX_REQUESTS and session.call_limit==MAX_OPERATIONS
        assert not session.pairs and not session.ranges and not session.saved and session.working_account() is None
        assert session.candidate.max_file_bytes==original.FILE_LIMIT
        return session

    def reply_schema(self):return original.reply_schema()
    def operating_reference(self):return original.operating_reference()+'\n\n'+navigation.REFERENCE_ADDITION
    def present_receipts(self,view,receipts):return navigation.present_receipts(view,receipts)
    def source_identities(self):return {**qualification_sources(),**native_bindings()}
    def implementation_identities(self):return implementation_identities()
    def __getattr__(self,name):return globals()[name] if name in globals() else getattr(host,name)


def __getattr__(name):
    return getattr(host,name)
