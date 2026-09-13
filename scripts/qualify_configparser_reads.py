"""Offline exact-read capacity screen at three consumed states; no inference path."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
from types import SimpleNamespace

import configparser_patch_dialogue as dialogue
import configparser_work as work
import qualify_compiler_delivery as envelope
import run_configparser_backport as original
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count
from working_set_exp.tools import action_schema

ROOT, RUN, AREA = original.ROOT, original.RUN, dialogue.AREA
require = work.require
COUNTS = (30, 100, 250)
CASES = {25: dict(previous=15, companions=[22, 23, 24]),
         27: dict(previous=22, companions=[25]),
         32: dict(previous=25, companions=[27, 31])}
OLD_EFFECT = ("Returns exact current source from start_line (one-based), as the largest whole-line page fitting "
    "18,000 content bytes, 22,000 complete-result JSON bytes AND 22,000 bytes for its exact saved-result wrapper. "
    "Escaping can shorten the page. Includes candidate_id, file_sha256, returned interval and next_start_line; "
    "no line_count argument. complete means no later page, not that earlier lines were read. Empty reads beyond "
    "EOF add no coverage. Validates the complete return before recording acquisition. Does not edit or check the candidate.")
NEW_EFFECT = ("Returns exact current source from start_line (one-based), up to line_count whole lines, shortened "
    "when needed to fit 18,000 content bytes, 22,000 complete-result JSON bytes AND 22,000 bytes for its exact "
    "saved-result wrapper. Escaping can shorten the page. Includes requested_line_count, candidate_id, file_sha256, "
    "returned interval and next_start_line. complete means no later page, not that earlier lines were read. "
    "Empty reads beyond EOF add no coverage. Validates the complete return before recording acquisition. "
    "Does not edit or check the candidate.")


def counted_request(value, prefix):
    """A declared development variant; original renderer and host stay unchanged."""
    request = work.request_for(value, prefix)
    old_schema = request['response_format']
    schema = action_schema('continuation', probe_id=None, read_mode='actor_selected_count',
                           hierarchical_p0=True, result_reopen=True, event_reopen=True)
    without_read = lambda s: [f for f in s['json_schema']['schema']['oneOf']
                              if f['properties']['action']['const'] != 'read']
    require(without_read(schema) == without_read(old_schema), 'non-read grammar drift')
    old_ref = work.pilot.tool_reference(old_schema, candidate=value.state.candidate)
    new_ref = work.pilot.tool_reference(schema, candidate=value.state.candidate)
    require(new_ref.count(OLD_EFFECT) == 1, 'read effect needs review')
    new_ref = new_ref.replace(OLD_EFFECT, NEW_EFFECT)
    system = request['messages'][0]['content']
    require(system.count(old_ref) == 1, 'old visible reference differs')
    request['messages'][0]['content'] = system.replace(old_ref, new_ref)
    state = envelope.state_of(request)
    require(state['read_paging_mode'] == 'maximal_bounded_page', 'old state read mode differs')
    require(state['tool_contract']['read'] == 'largest exact current whole-line page that fits the frozen result bound, with non-guessing continuation', 'old read summary differs')
    state['read_paging_mode'] = 'actor_selected_count'
    state['tool_contract']['read'] = 'up to the requested line_count exact current whole lines within the frozen result bounds, with exact continuation'
    request['messages'][1]['content'] = canonical_json_bytes(state).decode()
    request['response_format'] = schema
    return request


def history_before(n):
    value = new_state('offline-read-screen', original.task.fixture())
    for i in range(1, n):
        saved = original.task.read(RUN/f'calls/C{i:02d}-host-result.json')
        require(value.execute(saved['action']) == saved['result'], 'historical replay differs')
    require(original.pilot.reference.candidate_bytes(value.state.candidate) ==
            (RUN/f'after/C{n-1:02d}-candidate.json').read_bytes(), 'pre-read candidate differs')
    return value


def narrowed(value, n, count):
    value = copy.deepcopy(value)
    value.executor.read_mode = 'actor_selected_count'
    action = original.task.read(RUN/f'calls/C{n:02d}-action.json')
    require(action['action'] == 'read', 'case is not a read')
    action['line_count'] = count
    request = counted_request(value, CASES[n]['previous'])
    original.host.validate_action(action, request)
    before = value.state.candidate.candidate_id
    result = value.execute(action)
    require(result['accepted'] and value.state.candidate.candidate_id == before, 'read rejected or mutated')
    source = value.state.candidate.file_map[action['path']]
    expected = ''.join(source.decode().splitlines(keepends=True)[action['start_line']-1:result['returned_end_line']])
    require(result['content'] == expected and result['file_sha256'] == sha256_bytes(source), 'read source identity differs')
    saved = canonical_json_bytes(result)
    recovered = value.executor._saved_result(f'RES-{n:04d}', saved)
    require(recovered['exact_result_utf8'].encode() == saved and
            recovered['exact_result_sha256'] == sha256_bytes(saved), 'recovery differs')
    require(len(result['content'].encode()) <= 18000 and len(saved) <= 22000 and
            len(canonical_json_bytes(recovered)) <= 22000, 'return bound violated')
    return value, dict(action=action, result=result, source_bytes=len(result['content'].encode()),
        result_bytes=len(saved), recovery_bytes=len(canonical_json_bytes(recovered)))


def qualify(tokenizer, output):
    require(not output.exists(), 'preserve existing qualification')
    dialogue.verify_source()
    launch = original.task.read(RUN/'private-runtime/launch.json')
    require(sha256_file(tokenizer) == envelope.TOKENIZER_SHA, 'tokenizer differs')
    require(sha256_file(Path(launch[2])) == work.ACTOR['model_sha256'], 'model differs')
    # Do not compete with a Qwen completion for resources during token measurements.
    require(original.base.port_free(original.base.PORT) and
            not original.base.running_process_ids(Path(launch[0]).name), 'owned model runtime must be closed')
    profile = SimpleNamespace(model_path=Path(launch[2]), tokenizer_path=tokenizer)
    output.mkdir(parents=True)
    rows, counts = [], {}
    def save(name, raw):
        path = output/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    def count(raw):
        if raw not in counts: counts[raw] = tokenizer_count(profile, raw)
        return counts[raw]
    try:
        for n, setting in CASES.items():
            before = history_before(n)
            # Use any saved native envelope for the next turn, preserving its settings.
            stem = sorted((RUN/'admission').glob(f'C{n+1:02d}-x*-endpoint-request.json'))[0]
            saved_request = original.task.read(stem)
            saved_native = Path(str(stem).replace('-endpoint-request.json', '-native.txt')).read_bytes().decode()
            require(envelope.native_for(saved_request, saved_request, saved_native) == saved_native.encode(), 'native envelope differs')
            require(count(saved_native.encode()) == len(original.task.read(Path(str(stem).replace('-endpoint-request.json', '-tokens.json')))['tokens']), 'original token count differs')
            for requested in ('original', *COUNTS):
                if requested == 'original':
                    value = copy.deepcopy(before)
                    action = original.task.read(RUN/f'calls/C{n:02d}-action.json')
                    result = value.execute(action)
                    require(result == original.task.read(RUN/f'calls/C{n:02d}-host-result.json')['result'], 'original result differs')
                    detail = dict(action=action, result=result, source_bytes=len(result['content'].encode()),
                        result_bytes=len(canonical_json_bytes(result)),
                        recovery_bytes=len(canonical_json_bytes(value.executor._saved_result(f'RES-{n:04d}', canonical_json_bytes(result)))))
                    make = work.request_for
                else:
                    value, detail = narrowed(before, n, requested)
                    make = counted_request
                row = dict(call=f'C{n:02d}', requested_count=requested, previous_prefix=setting['previous'],
                    companion_sequences=setting['companions'], **detail, attempts=[])
                name = f'C{n:02d}-{requested}'
                save(name+'/read.json', canonical_json_bytes(detail))
                for prefix in range(setting['previous'], n+1):
                    request = make(value, prefix)
                    template = copy.deepcopy(saved_request)
                    # Schema differs only by the declared read argument. It is not part of this
                    # verified native text envelope; visible schema-derived reference is included.
                    template['response_format'] = request['response_format']
                    raw = envelope.native_for(request, template, saved_native)
                    tokens = count(raw)
                    delivered = work.latest_result_delivered(request, value)
                    attempt = dict(prefix=prefix, input_tokens=tokens, physical_generation_space=56576-tokens,
                        latest_delivered=delivered, fits=tokens<=work.INPUT_CEILING,
                        companion_bodies_resident=[i for i in setting['companions'] if i>prefix])
                    row['attempts'].append(attempt)
                    save(f'{name}/x{prefix:03d}-request.json', canonical_json_bytes(request))
                    save(f'{name}/x{prefix:03d}-native.txt', raw)
                    if tokens<=work.INPUT_CEILING:
                        row['selected']=attempt
                        break
                row['usable_next_input'] = bool(row.get('selected',{}).get('latest_delivered'))
                rows.append(row)
                print(name, row.get('selected'), flush=True)
        dialogue.verify_source()
        sources={p.relative_to(ROOT).as_posix():sha256_file(p) for p in
            (Path(__file__), ROOT/'tests/test_configparser_reads.py', AREA/'SPEC.md')}
        result=dict(status='offline_capacity_screen', historical_seal_sha256=dialogue.SOURCE_SEAL,
            source_sha256=sources, actor=work.ACTOR, tokenizer_sha256=envelope.TOKENIZER_SHA,
            input_ceiling=work.INPUT_CEILING, cases=rows, native_tokenizations=len(counts),
            model_requests=0, historical_evidence_unchanged=True, production_host_changed=False,
            limitations=['Reviewer-selected counts with original start lines; not model choices or task completion.',
                'Single-read substitutions into actual ordered history, not a simulated alternative trajectory.',
                'No retention policy, restored earlier body or budget change; native variant requires server confirmation before live use.',
                'Smaller next pages do not bound continued signal growth, additional acquisitions or uncapped reasoning.'])
        save('MEASUREMENTS.json', canonical_json_bytes(result))
        files=[dict(path=p.relative_to(output).as_posix(),sha256=sha256_file(p),size_bytes=p.stat().st_size)
               for p in sorted(output.rglob('*')) if p.is_file()]
        save('SEAL.json', canonical_json_bytes(dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))))
        return result
    except BaseException as error:
        save('FAILED.json', canonical_json_bytes(dict(error_type=type(error).__name__,error=str(error),completed_cases=rows)))
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=AREA/'read-qualification-001')
    args=parser.parse_args();qualify(args.tokenizer,args.output)
