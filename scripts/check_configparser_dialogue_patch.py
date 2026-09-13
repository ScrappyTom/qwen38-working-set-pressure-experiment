"""Source-check a saved consultation proposal offline; never change the consumed run."""
import argparse
import ast
import copy
from pathlib import Path
import pickle
import sys
import types

import qualify_configparser_reads as q
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def check(action_file,output,provenance):
    q.require(not output.exists(),'preserve previous check')
    q.dialogue.verify_source()
    value=q.history_before(11)
    before=value.state.candidate.file_map
    action=q.original.task.read(action_file)
    packet=q.dialogue.evidence_packet()
    import json
    intended=json.loads(packet['proposed_action_in_reasoning']['text'])
    outcome=dict(scope='offline source-check of a saved proposed edit, not a model-executed action',
        proposal_provenance=provenance,
        proposal_sha256=sha256_file(action_file),source_sha256=sha256_file(Path(__file__)),
        historical_seal_sha256=q.dialogue.SOURCE_SEAL,model_requests=0,
        old_characters=len(action.get('old','')),new_characters=len(action.get('new','')),
        original_candidate=value.state.candidate.candidate_id)
    try:
        request=q.original.task.read(Path(str(q.dialogue.OLD)+'-endpoint-request.json'))
        q.original.host.validate_action(action,request)
        outcome['schema_valid']=True
        outcome['old_matches']=before[action['path']].decode().count(action['old'])
        result=value.execute(action);outcome['actual_result']=result
        q.require(result['accepted'],'actual patch rejected')
        after=value.state.candidate.file_map
        q.require({k:v for k,v in before.items() if k!=action['path']}==
                  {k:v for k,v in after.items() if k!=action['path']},'other files changed')
        source=after['Lib/configparser.py'].decode()
        expected=before['Lib/configparser.py'].decode().replace(intended['old'],intended['new'])
        outcome['exactly_matches_original_intended_successor']=source==expected
        name='_offline_configparser_consultation_patch'
        module=types.ModuleType(name);sys.modules[name]=module
        try:
            exec(compile(source,'Lib/configparser.py','exec'),module.__dict__)
            module.RawConfigParser();module.ConfigParser()
            q.require('_UNSET' in module.__dict__,'sentinel missing')
            cls=module.MultilineContinuationError
            q.require(issubclass(cls,module.ParsingError),'wrong base')
            exc=cls('sample.ini',3,'  continued\n')
            expected_attrs=('sample.ini',3,'  continued\n')
            for candidate in (exc,copy.copy(exc),copy.deepcopy(exc),pickle.loads(pickle.dumps(exc))):
                q.require((candidate.source,candidate.lineno,candidate.line)==expected_attrs and
                          candidate.args==expected_attrs and candidate.errors==[(3,'  continued\n')],
                          'exception state or copy/pickle differs')
                q.require(str(candidate)=="Source contains parsing errors: 'sample.ini'\n\t[line  3]:   continued\n",
                          'exception message differs')
            outcome['module_executes_and_parser_constructors_work']=True
            outcome['exception_attributes_message_copy_pickle_pass']=True
            outcome['syntax_valid']=bool(ast.parse(source))
        finally:
            sys.modules.pop(name,None)
        outcome['passed']=True
    except Exception as error:
        outcome.update(passed=False,error_type=type(error).__name__,error=str(error))
    q.dialogue.verify_source()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:stream.write(canonical_json_bytes(outcome))
    print(canonical_json_bytes(outcome).decode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--action',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--provenance',choices=('qwen_final','reviewer_constructed'),required=True)
    a=p.parse_args();check(a.action,a.output,a.provenance)
