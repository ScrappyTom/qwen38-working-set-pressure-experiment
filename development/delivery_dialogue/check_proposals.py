"""Source-check D2 offline: copied-candidate repair and recorded admission choices."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import delivery_dialogue as dialogue
import run_compiler_incident as compiler
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file

area = dialogue.AREA
output = area/'proposal-check-001'
require = dialogue.require
read = lambda path: load_json_strict(path.read_bytes())


def main():
    require(not output.exists(), 'proposal check exists; preserve it')
    dialogue.base.verify_seal(area/'turn-02')
    dialogue.probe.verify_originals()
    compiler.verified_package()
    output.mkdir()
    def save(name, value):
        (output/name).write_bytes(canonical_json_bytes(value))
    status = 'incomplete'
    try:
        final = (area/'turn-02/calls/D2-assistant-content.txt').read_bytes().decode()
        blocks = re.findall(r'```python\n(.*?)\n```', final, re.S)
        require(len(blocks) == 4 and blocks[0] == blocks[1], 'D2 code block extraction differs')
        old, new = blocks[1], blocks[2]
        fixture = compiler.load_fixture()
        value = new_state('D2-proposal-offline-copy', fixture)
        candidate = fixture.initial
        original = dialogue.probe.state_of(read(Path(str(dialogue.OLD)+'-endpoint-request.json')))
        event = original['active_phase_event_frame']['events'][16]
        require(candidate.candidate_id == original['candidate_id'] == event['result']['candidate_id'], 'candidate binding differs')
        require(candidate.file_sha256('compiler/unary.py') == event['result']['file_sha256'], 'file guard differs')
        require(candidate.candidate_id in final and event['result']['file_sha256'] in final, 'D2 guards absent')
        require(candidate.file_map['compiler/unary.py'].decode().count(old) == 1, 'old fragment is not unique')
        # This script executes in a new offline copy. These are not additional
        # actor actions and are never appended to either sealed dialogue turn.
        acquisition = value.execute(dict(action='read', path='compiler/unary.py', start_line=1))
        require(acquisition['accepted'], 'offline acquisition rejected')
        action = dict(action='patch', path='compiler/unary.py', old=old, new=new,
            expected_candidate_id=event['result']['candidate_id'], expected_file_sha256=event['result']['file_sha256'])
        patch = value.execute(action)
        save('reviewer-assembled-action.json', action)
        save('patch-result.json', patch)
        require(patch['accepted'], 'proposed patch rejected')
        successor = value.state.candidate
        require(successor.file_map['reports/incident.json'] == candidate.file_map['reports/incident.json'], 'report changed')
        check = value.execute(dict(action='check', check_id='public', expected_candidate_id=successor.candidate_id))
        save('public-check-result.json', check)
        save('scripted-pairs.json', value.pairs)
        (output/'candidate.json').write_bytes(compiler.pilot.reference.candidate_bytes(successor))
        (output/'unary.py').write_bytes(successor.file_map['compiler/unary.py'])
        require(check['accepted'] and not check['passed'] and '25/26 contract cases passed' in check['stdout'], 'unexpected public boundary')
        failures = [line for line in check['stdout'].splitlines() if line.startswith('FAIL ')]
        require(len(failures) == 1 and failures[0].startswith('FAIL incident report agrees with captured builds:'), 'optimizer failure remains')

        measurements = read(dialogue.probe.DEST/'offline-001/MEASUREMENTS.json')
        rows = []
        for case in measurements['cases']:
            tag = case['id'].rsplit('-x', 1)[0]
            paths = sorted((dialogue.probe.RUN/'admission').glob(tag+'-x*-endpoint-request.json'))
            available = []
            for path in paths:
                removed = int(path.name.split('-x')[1].split('-')[0])
                stem = path.name.removesuffix('-endpoint-request.json')
                tokens = len(read(path.with_name(stem+'-tokens.json'))['tokens'])
                req = read(path)
                frame = dialogue.probe.state_of(req)['active_phase_event_frame']
                require(frame['externalized_payload_through_sequence'] == removed, 'prefix differs')
                available.append((removed, tokens, path, frame))
            require([v[0] for v in available] == list(range(available[0][0], available[-1][0]+1)), 'noncontiguous saved trials')
            chosen = next((v for v in available if v[1] <= 23808), None)
            require(chosen is not None, 'larger limit still denies all saved trials')
            cut, count, path, frame = chosen
            delivered = set(range(cut+1, frame['complete_through_sequence']+1))
            groups = {}
            for name, members in dialogue.probe.GROUPS.items():
                sequences = sorted({case['material_sequences'][m] for m in members})
                groups[name] = dict(required_sequences=sequences,
                    all_selected_bodies_resident=set(sequences) <= delivered,
                    absent_selected_sequences=sorted(set(sequences)-delivered))
            rows.append(dict(state=tag, previous_externalized_prefix=available[0][0],
                chosen_externalized_prefix=cut, input_tokens=count, generation_space=56576-count,
                newest_body_resident=frame['complete_through_sequence'] in delivered,
                whole_body_groups=groups, exact_request_path=path.relative_to(ROOT).as_posix(),
                exact_request_sha256=sha256_file(path)))
        save('RESULTS.json', dict(status='offline_source_checks_only', completion_calls=0,
            dialogue_actions_executed=0, reviewer_scripted_operations=len(value.pairs),
            original_candidate=candidate.candidate_id, proposed_successor=successor.candidate_id,
            optimizer_cases_passing=25, total_public_cases=26, overall_passed=False,
            report_unchanged=True, admission_threshold_under_review=23808,
            capacity_rows=rows, existing_native_counts_only=True,
            limitation='Capacity screen changes the ceiling at each saved state while preserving its previously externalized prefix. It is not a new trajectory from the beginning. Group membership checks only the selected whole-body examples, not every possible evidence copy or minimum sufficient set.'))
        dialogue.probe.verify_originals()
        status = 'completed_offline_checks'
    finally:
        inventory = dialogue.base.file_inventory(output)
        save('SEAL.json', dict(status=status, files=inventory, source_sha256=sha256_file(Path(__file__)),
            d2_seal_sha256=sha256_file(area/'turn-02/RESPONSE_SEAL.json')))
    print((output/'RESULTS.json').read_text())


if __name__ == '__main__':
    main()
