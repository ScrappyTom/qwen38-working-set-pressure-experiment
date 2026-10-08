"""Bound exact current input to the existing nonexecuting consultation lifecycle."""
import argparse
import copy
from functools import partial
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
sys.path.insert(0,str(ROOT/'development/workload_requalification/interpolation_completion'))
import qualified_task
import run_completion
import bounded_visibility_dialogue as dialogue
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

def load(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value

composition = load('preserved_discovery_composition',AREA.parent/'prepare_cpu.py')
study = qualified_task.Task()
RUNTIME = run_completion.execution.RUNTIME
SOURCE = study.RUN
SYSTEM = (AREA.parent/'SYSTEM.txt').read_text(encoding='utf-8')


def original():
    seal = RUNTIME.verify_seal(SOURCE)
    composition.require(seal['disposition']=='request_allowance_exhausted' and
                        seal['sent_requests']==32,'closed source differs')
    old = study.read(SOURCE/'calls/C63-wire-request.json')
    composition.require(old['chat_template_kwargs']==dict(enable_thinking=True,reasoning_effort='medium'),
                        'source reasoning policy differs')
    return old


def request_for(turn, follow=None):
    composition.require(turn==1 and follow is None,'only initial D1 is enabled; review before any clarification')
    old = original()
    question = (AREA/'QUESTION_1.txt').read_text(encoding='utf-8')
    request = composition.compose(old,SYSTEM,question)
    composition.validate_request(request,old,SYSTEM,question)
    return request


def native_for(request):
    # Constraints affect output, not the template. Reinstate them only to use
    # the source package's exact native renderer assertion.
    anchor = copy.deepcopy(request)
    anchor['seed'] = study.SEED
    anchor['grammar'] = study.response_constraints()['grammar']
    return study.expected_native(anchor)


def identities():
    paths = [*AREA.glob('*.py'),AREA/'SPEC.md',AREA/'QUESTION_1.txt',AREA.parent/'SYSTEM.txt',
             AREA.parent/'prepare_cpu.py',SOURCE/'RESPONSE_SEAL.json',SOURCE/'calls/C63-wire-request.json',
             ROOT/'scripts/bounded_visibility_dialogue.py']
    return {**study.source_identities(),**{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


task = SimpleNamespace(ROOT=ROOT,RUN=SOURCE,ACTOR=study.ACTOR,base=RUNTIME,pilot=study.base.pilot,
    delivery=study.base.delivery,runtime_paths=study.runtime_paths,read=study.read,save=study.save,
    require=composition.require)
dialogue.AREA, dialogue.task = AREA, task
dialogue.identities, dialogue.request_for, dialogue.native_for = identities, request_for, native_for
dialogue.RunLog = partial(dialogue.RunLog,task_module=task)


def prepare():
    dialogue.prepare(1,None)
    folder = AREA/'native-preparation-01'; folder.mkdir(exist_ok=False)
    store = ArtifactStore(folder)
    log = dialogue.RunLog(folder/'records.jsonl','discovery-native-preparation')
    bound = identities(); failure = None
    plan = study.read(AREA/'preparation-01/PLAN.json')
    request = request_for(1)
    try:
        server, model, _ = study.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            template,native,tokens,count = study.base.pilot.render_only(url,request)
            log.append('input_qualified',dict(prompt_tokens=count,completion_sent=False),
                [store.put('request.json',canonical_json_bytes(request)),store.put('native.txt',native),
                 store.put('template.json',template),store.put('tokens.json',tokens)])
            assert native==native_for(request) and count==plan['prompt_tokens']<=23808
            assert identities()==bound
    except BaseException as error:
        failure=error
        store.put('FAILED.json',canonical_json_bytes(dict(type=type(error).__name__,message=str(error))))
    finally:
        run_completion.execution.legacy.seal(folder,'failed_preserved' if failure else 'qualified_no_model_inference',
                                              bound,completion_requests=0)
    if failure: raise failure
    print('Native consultation input qualified; no completions.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','run'))
    mode=parser.parse_args().mode
    if mode=='prepare': prepare()
    else:
        seal=study.read(AREA/'native-preparation-01/SEAL.json')
        assert seal['source_sha256']==identities() and seal['status']=='qualified_no_model_inference'
        dialogue.run(1,None,'Proceed with the separate focused source-discovery consultation after the closed interpolation attempt.')
