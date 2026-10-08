"""One reviewed, nonexecuting follow-up; preserve the sealed D1 adapter."""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import sys

AREA = Path(__file__).resolve().parent
sys.path.insert(0, str(AREA.parent))
import consult as first
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

ROOT, study, RUNTIME = first.ROOT, first.study, first.RUNTIME
dialogue, require = first.dialogue, first.composition.require
FOLLOW = AREA/'QUESTION_2.txt'
FIRST = AREA.parent/'turn-01'


def reviewed_material():
    seal = RUNTIME.verify_seal(FIRST)
    require(seal['disposition'] == 'completed_dialogue_turn' and
            seal['source_sha256'] == first.identities() and seal['sent_requests'] == 1,
            'reviewed first response differs')
    require((AREA.parent/'D1_REVIEW.md').is_file(), 'direct first-response review required')
    old = first.original()
    view = json.loads(old['messages'][1]['content'])['workspace']
    source = [s for s in view['working_set']['sources'] if s['path'] == 'Lib/configparser.py']
    require(len(source) == 1, 'original library presentation differs')
    facts = study.read(AREA/'SOURCE_FACTS.json')
    require(source[0]['file_sha256'] == facts['file_sha256'], 'clarification library version differs')
    snapshot = study.read(first.SOURCE/'starting-candidate.json')
    row = next(r for r in snapshot['files'] if r['path'] == facts['path'])
    from working_set_exp.jsonutil import sha256_bytes
    require(sha256_bytes(row['content_utf8'].encode()) == facts['file_sha256'], 'source bytes differ')
    lines = row['content_utf8'].splitlines(keepends=True)
    for definition in facts['definitions']:
        exact = ''.join(lines[definition['start_line']-1:definition['end_line']]).rstrip('\n')
        require(exact == definition['content'], 'provided definition differs from exact source')
    return old, view, source[0]


def quote(label, content):
    start, end = f'BEGIN {label}', f'END {label}'
    require(start not in content and end not in content, 'quotation delimiter collision')
    return start+'\n'+content+'\n'+end


def request_for(turn, follow=None):
    require(turn == 2 and follow == FOLLOW, 'only reviewed D2 is enabled; no additional dialogue')
    old, view, source = reviewed_material()
    supplied = [
        quote('EXACT ORIGINAL OPERATING SYSTEM MESSAGE', old['messages'][0]['content']),
        quote('EXACT ORIGINAL TASK TEXT', view['task']),
        quote('ORIGINAL DISPLAYED LIBRARY EXCERPT AND METADATA',
              json.dumps(source, ensure_ascii=False, indent=2)),
        quote('COMPLETE D1 PUBLIC ANSWER', (FIRST/'calls/D1-assistant-content.txt').read_text(encoding='utf-8')),
        quote('ADDITIONAL REVIEWER SOURCE AND LOOKUP OBSERVATIONS',
              (AREA/'SOURCE_FACTS.json').read_text(encoding='utf-8')),
    ]
    request = copy.deepcopy(old)
    for key in first.composition.EXECUTION_KEYS:
        request.pop(key, None)
    request['seed'] = 42
    request['messages'] = [dict(role='system', content=first.SYSTEM),
        dict(role='user', content=FOLLOW.read_text(encoding='utf-8')+'\n\n'+'\n\n'.join(supplied))]
    require(not first.composition.EXECUTION_KEYS & request.keys(), 'execution channel present')
    require(all(request[k] == -1 for k in first.composition.BUDGETS), 'generation policy changed')
    return request


def identities():
    paths = [*AREA.glob('*.py'), AREA/'SPEC.md', FOLLOW, AREA/'SOURCE_FACTS.json',
        AREA.parent/'D1_REVIEW.md', FIRST/'RESPONSE_SEAL.json', FIRST/'calls/D1-assistant-content.txt']
    return {**first.identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


dialogue.AREA = AREA
dialogue.identities, dialogue.request_for, dialogue.native_for = identities, request_for, first.native_for


def prepare():
    dialogue.prepare(2, FOLLOW)
    folder = AREA/'native-preparation-02'; folder.mkdir(exist_ok=False)
    store = ArtifactStore(folder)
    log = dialogue.RunLog(folder/'records.jsonl', 'discovery-clarification-native')
    bound, failure = identities(), None
    plan = study.read(AREA/'preparation-02/PLAN.json')
    request = request_for(2, FOLLOW)
    try:
        server, model, _ = study.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            template, native, tokens, count = study.base.pilot.render_only(url, request)
            log.append('input_qualified', dict(prompt_tokens=count, completion_sent=False),
                [store.put('request.json', canonical_json_bytes(request)), store.put('native.txt', native),
                 store.put('template.json', template), store.put('tokens.json', tokens)])
            require(native == first.native_for(request) and count == plan['prompt_tokens'] <= 23808,
                    'actual native input differs')
            require(identities() == bound, 'preparation sources changed')
    except BaseException as error:
        failure = error
        store.put('FAILED.json', canonical_json_bytes(dict(type=type(error).__name__, message=str(error))))
    finally:
        first.run_completion.execution.legacy.seal(folder,
            'failed_preserved' if failure else 'qualified_no_model_inference', bound, completion_requests=0)
    if failure:
        raise failure
    print('Native D2 qualified; zero completions.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=('prepare', 'run'))
    if parser.parse_args().mode == 'prepare':
        prepare()
    else:
        seal = study.read(AREA/'native-preparation-02/SEAL.json')
        require(seal['source_sha256'] == identities() and seal['status'] == 'qualified_no_model_inference',
                'native preparation differs')
        dialogue.run(2, FOLLOW, 'Proceed with one source-checked clarification after direct D1 review; no task execution or further dialogue.')
