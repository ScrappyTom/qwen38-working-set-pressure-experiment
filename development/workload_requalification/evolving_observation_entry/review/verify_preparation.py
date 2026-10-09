"""Read-only replay of native preparation and its actual information paths."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import observation_task as study
import qualification_route
import run_ecological
from working_set_exp.custody import verify_records
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file


def helpers():
    path=study.ROOT/'development/workload_requalification/url_port_entry/review/verify_run.py'
    spec=importlib.util.spec_from_file_location('e18_preparation_native_helpers',path)
    core=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'url_task':study}):spec.loader.exec_module(core)
    return core


def verify(version='001'):
    module=study.Task(version);folder=module.PACKAGE;core=helpers()
    manifest=run_ecological.verify_preparation(module)
    seal=study.read(folder/'SEAL.json');proof=study.read(folder/'QUALIFICATION.json')
    assert seal['status']=='qualified_no_model_inference' and seal['completion_requests']==0
    assert proof['actor']==manifest['actor']==module.ACTOR
    assert proof['entry_unchanged_after_qualification'] and proof['route']['audit']['temporal_contract_met']
    core._inventory(folder,seal)
    records=verify_records(folder/'records.jsonl',folder)
    assert not any(r['record_type']=='invocation_started' for r in records)
    adapter=core._runner().Adapter(module)
    counts=core._native_counts(folder,records,adapter)
    assert completion_request_bytes(adapter.request_for(module.initial_session().view()))==(folder/'initial-wire-request.json').read_bytes()

    def measure(view):
        key=sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts,'replay requires an absent saved native measurement'
        return counts[key]

    def record(row,current):
        stem=folder/'route'/row['name']
        assert row==study.read(stem.with_suffix('.json'))
        assert canonical_json_bytes(module.snapshot(current))==Path(str(stem)+'-state.json').read_bytes()
        assert module.candidate_bytes(current.candidate)==Path(str(stem)+'-candidate.json').read_bytes()
        restored=module.restore(module.snapshot(current),current.candidate,folder/'scripted',replay=True)
        assert restored.view()==current.view()

    with patch('working_set_exp.observations.subprocess.Popen',side_effect=AssertionError('no checker during replay')):
        session=study.initial_session(folder/'scripted',replay=True)
        route=qualification_route.journey(module,session,measure,feedback=adapter.preceding_feedback,record=record,request_for=adapter.request_for)
        assert route=={k:v for k,v in proof['route'].items() if k!='crowded_transition'}
        crowded=study.initial_session(folder/'unused',replay=True)
        adapter.preceding_feedback.clear()
        files=sorted((folder/'crowded').glob('*.json'),key=lambda p:int(p.stem))
        for path in files:
            row=study.read(path)
            assert crowded.view()==row['before_view'] and measure(crowded.view())==row['input_tokens']
            crowded.mark_delivered(crowded.view());crowded.begin_request()
            actual=module.process_reply(crowded,dict(discussion='Declared crowded engineering case.',operation=row['action']),measure,adapter.preceding_feedback)
            assert actual==row['outcome'] and crowded.view()==row['after_view']
            assert measure(crowded.view())==row['next_input_tokens']
        assert crowded.candidate.candidate_id==module.STARTING_ID
        assert crowded.view()['presentation']['mode']=='ordinary'
        assert len(files)==proof['route']['crowded_transition']['steps']
    closed=[r['payload'] for r in records if r['record_type']=='runtime_closed']
    assert len(closed)==1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    return dict(status='preparation_replayed_exactly',artifacts=len(seal['files']),source_files=len(seal['source_sha256']),
        custody_records=len(records),native_inputs=len(counts),scripted_steps=len(route['trials']),crowded_steps=len(files),
        temporal_contract_met=route['audit']['temporal_contract_met'],researcher_scripted=True,
        no_new_model_or_checker_or_tokenizer_execution=True,preparation_seal_sha256=sha256_file(folder/'SEAL.json'),
        verification_source_sha256=sha256_file(Path(__file__)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--version',default='001');args=parser.parse_args()
    path=Path(__file__).with_name('PREPARATION-VERIFICATION-'+args.version+'.json')
    try:result=verify(args.version)
    except BaseException as error:
        raw=canonical_json_bytes(dict(status='failed',type=type(error).__name__,error=str(error),traceback=traceback.format_exc()))
        failure=path.with_name(path.stem+'-FAILED.json')
        if failure.exists():assert failure.read_bytes()==raw
        else:failure.write_bytes(raw)
        raise
    raw=canonical_json_bytes(result)
    if path.exists():assert path.read_bytes()==raw
    else:path.write_bytes(raw)
    print(json.dumps(result,indent=2))
