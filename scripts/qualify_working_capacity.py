"""Counterfactual host replay of completed saved actions; never invoke the model."""
import argparse
import copy
from pathlib import Path

import bounded_parser as task
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT


def restored(evidence, tag):
    s = task.initial_session()
    snapshot = task.read(evidence / f'after/{tag}-state.json')
    candidate = task.read(evidence / f'after/{tag}-candidate.json')
    assert task.candidate_bytes(s.candidate) == canonical_json_bytes(candidate)
    for key in ('pairs','last','ranges','saved','starting_archive_length','call_limit',
                'submitted','delivery_blocked','delivered_sources'):
        setattr(s,key,copy.deepcopy(snapshot[key]))
    assert not snapshot['diffs']
    assert canonical_json_bytes(task.snapshot(s)) == canonical_json_bytes(snapshot)
    return s


def qualify(evidence):
    prepared = {}
    for path in sorted((evidence/'admission').glob('*-count.json')):
        count = task.read(path)
        stem = count['stem']
        raw = (evidence/(stem+'-endpoint-request.json')).read_bytes()
        request = task.read(evidence/(stem+'-endpoint-request.json'))
        native = (evidence/(stem+'-native.txt')).read_bytes()
        assert native == task.expected_native(request)
        assert native == task.read(evidence/(stem+'-template.json'))['prompt'].encode()
        assert len(task.read(evidence/(stem+'-tokens.json'))['tokens']) == count['prompt_tokens']
        assert sha256_bytes(raw) == count['request_sha256'] and sha256_bytes(native) == count['native_sha256']
        prepared[count['request_sha256']] = count
    rows = []
    evidence_names = set()
    for before, action_tag, expected_stem in (('C03','C04','admission/I0016'), ('C04','C05','admission/I0028')):
        session = restored(evidence,before)
        action = task.read(evidence/f'calls/{action_tag}-action.json')
        original = task.read(evidence/f'calls/{action_tag}-host-result.json')['result']
        observed = []
        def measure(view):
            digest = sha256_bytes(canonical_json_bytes(task.request_for(view)))
            assert digest in prepared, 'counterfactual input has no saved native measurement'
            row = prepared[digest]
            observed.append(row)
            return row['prompt_tokens']
        current, sources = session.candidate, session.sources()
        session.mark_delivered(session.view())
        result = session.execute(action,measure)
        assert session.candidate == current and session.sources() == sources
        assert result['accepted'] and 'output_scope' not in session.last
        assert len(observed) == 1 and observed[0]['stem'] == expected_stem
        assert observed[0]['prompt_tokens'] <= INPUT_LIMIT
        if action_tag == 'C04':
            assert not original['accepted']
            assert result['next_offset'] is None
            assert result['exact_utf8'].encode() == session.payload('RES-0030')
        else:
            assert result == original and result['matches'][0]['line'] == 1369
        names = [f'after/{before}-state.json',f'after/{before}-candidate.json',
                 f'calls/{action_tag}-action.json',f'calls/{action_tag}-host-result.json']
        names += [expected_stem+suffix for suffix in ('-endpoint-request.json','-native.txt','-template.json','-tokens.json','-count.json')]
        evidence_names.update(names)
        rows.append(dict(before=before,action=action_tag,actual_recorded_result=original,
            counterfactual_result=result,native_input=observed[0],input_tokens_remaining=INPUT_LIMIT-observed[0]['prompt_tokens'],
            saved_candidate_unchanged=True,all_selected_source_retained=True,
            full_feedback_deliverable=True,alternate_input_was_not_sent_to_model=True))
    return dict(status='two_saved_host_boundaries_qualified_offline',no_completion_requests=True,
        policy='Acquisition headroom is spendable; actual complete next input must fit 23808.',
        source_sha256={p:sha256_file(task.ROOT/p) for p in ('src/working_set_exp/working_session.py',
            'tests/test_working_capacity.py','tests/test_working_session.py','scripts/qualify_working_capacity.py')},
        evidence_sha256={name:sha256_file(evidence/name) for name in sorted(evidence_names)},rows=rows,
        limits='Reused actual inputs and actions; no evidence about which action Qwen would choose after corrected feedback.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = qualify(args.evidence)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as f:
        f.write(canonical_json_bytes(result))
    print(result['status'])
    for row in result['rows']:
        print(row['action'],row['native_input']['prompt_tokens'],'full result delivered in offline counterfactual')
