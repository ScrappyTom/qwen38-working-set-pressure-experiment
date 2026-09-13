"""Replay the final two-edit proposal and verify the separately authored short anchor."""
import argparse
import copy
import json
from pathlib import Path
import re

import qualify_configparser_reads as q
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


def verify(output):
    q.require(not output.exists(),'preserve earlier verification')
    folder=q.AREA/'proposal-001'
    text=(q.AREA/'turn-01/calls/D1-assistant-content.txt').read_bytes().decode()
    blocks=[(m.start(1),m.end(1),json.loads(m.group(1))) for m in re.finditer(r'```json\n(.*?)\n```',text,re.S)]
    actions=[b for b in blocks if isinstance(b[2],dict) and b[2].get('action')=='patch']
    q.require(len(actions)==1 and isinstance(blocks[-1][2],str),'proposal form differs')
    first=actions[0][2];second=copy.deepcopy(first);second['new']=blocks[-1][2]
    q.require(first==q.original.task.read(folder/'operation-1.json') and
              second['new']==q.original.task.read(folder/'operation-2-new.json'),'extracted proposal differs')
    request=q.original.task.read(Path(str(q.dialogue.OLD)+'-endpoint-request.json'))
    value=q.history_before(11);before=value.state.candidate.file_map['Lib/configparser.py'].decode()
    rows=[]
    for i,action in enumerate((first,second),1):
        if i==2:
            action['expected_candidate_id']=value.state.candidate.candidate_id
            action['expected_file_sha256']=q.sha256_bytes(value.state.candidate.file_map[action['path']])
        q.original.host.validate_action(action,request)
        result=value.execute(action)
        row=dict(operation=i,action=action,result=result)
        try:
            compile(value.state.candidate.file_map[action['path']],action['path'],'exec')
            row['syntax_valid']=True
        except SyntaxError as error:row.update(syntax_valid=False,syntax_error=str(error))
        q.work.request_for(value,5);row['next_input_constructs']=True
        rows.append(row)
    prior=q.original.task.read(folder/'SEQUENCE_CHECK.json')
    q.require(rows==prior['operations'],'recorded proposal execution differs')
    proposed=json.loads(q.dialogue.evidence_packet()['proposed_action_in_reasoning']['text'])
    intended=before.replace(proposed['old'],proposed['new'])
    q.require(value.state.candidate.file_map['Lib/configparser.py'].decode()==intended,'sequence differs from intent')
    single=q.original.task.read(folder/'reviewer-single-action.json')
    q.require(before.count(single['old'])==1 and len(single['new'])==420,'short anchor qualification differs')
    other=q.history_before(11);q.original.host.validate_action(single,request)
    q.require(other.execute(single)==prior['reviewer_single_actual_result'],'single result differs')
    q.require(other.state.candidate.file_map==value.state.candidate.file_map,'successor equality differs')
    result=dict(source_sha256=sha256_file(Path(__file__)),historical_seal_sha256=q.dialogue.SOURCE_SEAL,
        final_text_sha256=sha256_file(q.AREA/'turn-01/calls/D1-assistant-content.txt'),
        exact_final_proposal_extraction=True,model_proposed_operations_replayed=2,
        second_guards_bound_from_actual_first_result=True,intermediate_syntax_valid=False,
        next_inputs_construct=True,final_syntax_valid=True,final_matches_intended_successor=True,
        reviewer_single_patch_equivalent=True,reviewer_single_new_characters=420,
        source_identity_unchanged=True,new_model_requests=0,qwen_consumed_offline_results=False)
    q.dialogue.verify_source()
    with output.open('xb') as stream:stream.write(canonical_json_bytes(result))
    print(canonical_json_bytes(result).decode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    verify(p.parse_args().output)
