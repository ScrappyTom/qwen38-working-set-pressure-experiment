"""Exact C02 input/proposal over the existing nonexecuting dialogue lifecycle."""
import argparse
import copy
from functools import partial
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
sys.path.insert(0, str(AREA.parent))
import bootstrap
import observation_task
import run_ecological
import bounded_visibility_dialogue as dialogue
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

study = observation_task.Task('002')
RUNTIME, SOURCE = run_ecological.RUNTIME, study.RUN
COMPOSITION = ROOT / 'development/workload_requalification/source_discovery_consultation/prepare_cpu.py'
spec = importlib.util.spec_from_file_location('replacement_composition', COMPOSITION)
composition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composition)
SOURCE_IDENTITIES = {
    'RESPONSE_SEAL.json': '9a0250225334ed26b2ad695ae01c3640774851229f110ce8c522732dde9af121',
    'calls/C02-wire-request.json': '7191de67a338af0d68acd2769e4fd1bd67945168d132821187ba68494102921c',
    'calls/C02-assistant-content.txt': 'afe769528aed095eac16693988154b577e5b2dbbb19bc6044c2c5f5b5610fd7c',
}
REPLY_START, REPLY_END = 'BEGIN EXACT ARCHIVED PUBLIC REPLY', 'END EXACT ARCHIVED PUBLIC REPLY'


def original():
    for name, digest in SOURCE_IDENTITIES.items():
        composition.require(sha256_file(SOURCE / name) == digest, 'source identity differs: ' + name)
    seal = RUNTIME.verify_seal(SOURCE)
    composition.require(seal['disposition'] == 'checked_submission' and
                        seal['sent_requests'] == seal['returned_responses'] == 10,
                        'closed source run differs')
    raw = (SOURCE / 'calls/C02-assistant-content.txt').read_bytes()
    return study.read(SOURCE / 'calls/C02-wire-request.json'), raw.decode('utf-8')


def compose(old, reply, system, question):
    composition.require(REPLY_START not in reply and REPLY_END not in reply,
                        'public reply delimiter collision')
    request = composition.compose(old, system, question)
    request['messages'][1]['content'] += '\n\n' + REPLY_START + '\n' + reply + '\n' + REPLY_END
    return request


def validate(request, old, reply, system, question):
    composition.require(request == compose(old, reply, system, question), 'unreviewed input or policy change')
    base = copy.deepcopy(request)
    base['messages'][1]['content'] = composition.compose(old, system, question)['messages'][1]['content']
    composition.validate_request(base, old, system, question)


def request_for(turn, follow=None):
    composition.require(turn == 1 and follow is None, 'only the initial D1 is enabled')
    old, reply = original()
    system = (AREA / 'SYSTEM.txt').read_text(encoding='utf-8')
    question = (AREA / 'QUESTION_1.txt').read_text(encoding='utf-8')
    request = compose(old, reply, system, question)
    validate(request, old, reply, system, question)
    return request


def native_for(request):
    # The output grammar does not affect input templating. Reinsert it only for
    # the source renderer's assertion; it is never sent with the consultation.
    anchor = copy.deepcopy(request)
    anchor['seed'] = study.SEED
    anchor['grammar'] = study.response_constraints()['grammar']
    return study.expected_native(anchor)


def identities():
    paths = [*AREA.glob('*.py'), *AREA.glob('*.txt'), AREA / 'SPEC.md',
             *(AREA / 'tests').glob('*.py'), COMPOSITION,
             ROOT / 'scripts/bounded_visibility_dialogue.py',
             *(SOURCE / name for name in SOURCE_IDENTITIES)]
    return {**study.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


task = SimpleNamespace(ROOT=ROOT, RUN=SOURCE, ACTOR=study.ACTOR, base=RUNTIME,
    pilot=study.base.pilot, delivery=study.base.delivery, runtime_paths=study.runtime_paths,
    read=study.read, save=study.save, require=composition.require)
dialogue.AREA, dialogue.task = AREA, task
dialogue.identities, dialogue.request_for, dialogue.native_for = identities, request_for, native_for
dialogue.RunLog = partial(dialogue.RunLog, task_module=task)


def prepare():
    dialogue.prepare(1, None)
    folder = AREA / 'native-preparation-01'
    folder.mkdir(exist_ok=False)
    store = ArtifactStore(folder)
    log = dialogue.RunLog(folder / 'records.jsonl', 'replacement-native-preparation')
    bound, failure = identities(), None
    plan = study.read(AREA / 'preparation-01/PLAN.json')
    request = request_for(1)
    try:
        server, model, _ = study.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            template, native, tokens, count = study.base.pilot.render_only(url, request)
            log.append('input_qualified', dict(prompt_tokens=count, completion_sent=False),
                [store.put('request.json', canonical_json_bytes(request)), store.put('native.txt', native),
                 store.put('template.json', template), store.put('tokens.json', tokens)])
            assert native == native_for(request) and count == plan['prompt_tokens'] <= 23808
            assert identities() == bound
    except BaseException as error:
        failure = error
        store.put('FAILED.json', canonical_json_bytes(dict(type=type(error).__name__, message=str(error))))
    finally:
        run_ecological.legacy.seal(folder, 'failed_preserved' if failure else 'qualified_no_model_inference',
                                   bound, completion_requests=0)
    if failure:
        raise failure
    print('Native consultation qualified; no completions.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    mode = parser.parse_args().mode
    if mode == 'prepare':
        prepare()
    else:
        seal = study.read(AREA / 'native-preparation-01/SEAL.json')
        assert seal['source_sha256'] == identities() and seal['status'] == 'qualified_no_model_inference'
        composition.verify_inventory(AREA / 'native-preparation-01', seal['files'], seal['aggregate_sha256'])
        dialogue.run(1, None, 'Keep working: one separate interpretation of the closed E18 C02 input and proposal.')
