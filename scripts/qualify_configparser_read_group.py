"""Assisted terminal capacity probe with three exact, reviewer-selected source ranges."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import copy

import qualify_configparser_reads as q
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

# These locations come from the saved source, not a Qwen choice in a new run.
# No source content or old action outside these three reads is changed.
RANGES={25:(1,32),27:(299,43),32:(2136,7)}


def assemble():
    value=q.new_state('assisted-terminal-group',q.original.task.fixture())
    value.executor.read_mode='actor_selected_count'
    replacements=[]
    for i in range(1,33):
        saved=q.original.task.read(q.RUN/f'calls/C{i:02d}-host-result.json')
        action=copy.deepcopy(saved['action'])
        if action['action']=='read':
            # Preserve exact historical behavior except the three declared substitutions.
            value.executor.read_mode='actor_selected_count' if i in RANGES else 'maximal_bounded_page'
        if i in RANGES:
            action['start_line'],action['line_count']=RANGES[i]
        result=value.execute(action)
        if i in RANGES:
            q.require(result['accepted'],'range rejected')
            q.original.host.validate_action(action,q.counted_request(q.history_before(i),q.CASES[i]['previous']))
            replacements.append(dict(sequence=i,action=action,result=result))
        else:
            q.require(result==saved['result'],'unchanged operation differs')
    value.executor.read_mode='actor_selected_count'
    q.require(q.original.pilot.reference.candidate_bytes(value.state.candidate)==
              (q.RUN/'calls/C32-candidate-after.json').read_bytes(),'terminal source changed')
    q.require('Lib/test/test_configparser.py' not in value.state.complete_reads,
              'separated test ranges incorrectly credited as complete')
    return value,replacements


def qualify(tokenizer,output):
    q.require(not output.exists(),'preserve previous probe')
    q.dialogue.verify_source()
    launch=q.original.task.read(q.RUN/'private-runtime/launch.json')
    q.require(q.original.base.port_free(q.original.base.PORT) and not
              q.original.base.running_process_ids(Path(launch[0]).name),'runtime must be closed')
    q.require(sha256_file(tokenizer)==q.envelope.TOKENIZER_SHA and
              sha256_file(Path(launch[2]))==q.work.ACTOR['model_sha256'],'runtime identity differs')
    value,replacements=assemble()
    output.mkdir(parents=True)
    def save(name,raw): (output/name).write_bytes(raw)
    try:
        save('scripted-pairs.json',canonical_json_bytes(value.pairs))
        stem=q.RUN/'admission/C33-x025'
        original=q.original.task.read(Path(str(stem)+'-endpoint-request.json'))
        native=Path(str(stem)+'-native.txt').read_bytes().decode()
        rows=[]
        # The earlier original eviction frontier is deliberately not treated as reversible.
        # These are static counterfactual input sizes, not continuation from the consumed state.
        for prefix in (24,25,26,27,30,31):
            request=q.counted_request(value,prefix)
            template=copy.deepcopy(original);template['response_format']=request['response_format']
            raw=q.envelope.native_for(request,template,native)
            n=tokenizer_count(SimpleNamespace(model_path=Path(launch[2]),tokenizer_path=tokenizer),raw)
            save(f'x{prefix:03d}-request.json',canonical_json_bytes(request))
            save(f'x{prefix:03d}-native.txt',raw)
            rows.append(dict(prefix=prefix,input_tokens=n,fits=n<=q.work.INPUT_CEILING,
                generation_space=56576-n,latest_delivered=q.work.latest_result_delivered(request,value),
                group_bodies_resident=[i for i in (25,27,31,32) if i>prefix]))
        result=dict(status='assisted_static_group_capacity_only',historical_seal_sha256=q.dialogue.SOURCE_SEAL,
            source_sha256={p.relative_to(q.ROOT).as_posix():sha256_file(p) for p in (Path(__file__),Path(q.__file__))},
            completion_requests=0,original_evidence_unchanged=True,selected_ranges=RANGES,rows=rows,
            replacements=replacements,terminal_candidate=value.state.candidate.candidate_id,
            limitations=['Reviewer selected both start and count, including a previously externalized main-guard location.',
                'No Qwen selection, new action, completed contribution or alternative admission trajectory was observed.',
                'Prefix 24 is earlier than the consumed terminal frontier 25; it cannot rescue or reverse that run.',
                'This asks whether compact exact class/import/test-target/doc material can coexist with all ordered signal.',
                'Source/count choices and byte identity are qualified; semantic sufficiency remains task-dependent.'])
        save('MEASUREMENTS.json',canonical_json_bytes(result))
        files=[dict(path=p.name,sha256=sha256_file(p),size_bytes=p.stat().st_size) for p in sorted(output.iterdir()) if p.is_file()]
        save('SEAL.json',canonical_json_bytes(dict(files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))))
        print(rows)
    except BaseException as error:
        save('FAILED.json',canonical_json_bytes(dict(error_type=type(error).__name__,error=str(error))))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tokenizer',type=Path,required=True)
    p.add_argument('--output',type=Path,default=q.AREA/'read-group-qualification-001')
    a=p.parse_args();qualify(a.tokenizer,a.output)
