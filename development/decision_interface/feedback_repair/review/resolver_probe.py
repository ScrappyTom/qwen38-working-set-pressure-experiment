"""Read-only checkout probe of a reference actually delivered in C14."""
import copy
import json
from pathlib import Path

import feedback_task as task
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore

AREA = Path(__file__).resolve().parents[1]
RUN = AREA / 'run-001'


def read(path):
    return json.loads(path.read_bytes())


def main():
    state = read(RUN / 'after/C13-O03-state.json')
    candidate = read(RUN / 'after/C13-O03-candidate.json')
    session = task.from_checkpoint()
    session.candidate = Candidate.create(
        {f['path']: f['content_utf8'].encode() for f in candidate['files']},
        max_file_bytes=candidate['max_file_bytes'])
    for key, value in state.items():
        if key != 'candidate_id':
            setattr(session, key, copy.deepcopy(value))
    session.observations = ObservationStore(RUN / 'observations', replay=True)
    wire = read(RUN / 'calls/C14-wire-request.json')
    view = json.loads(wire['messages'][1]['content'])['workspace']
    assert session.view() == view, 'reconstructed view differs from actual input'
    session.mark_delivered(view)
    action = read(RUN / 'calls/C14-reply.json')['operation']
    source, = [s for s in view['working_set']['sources'] if s['region_ref'] == action['region']]
    assert source['file_sha256'] == session.candidate.file_sha256(source['path'])
    outcomes = []
    for s in view['working_set']['sources']:
        try:
            resolution = session.resolve_region(s['region_ref'])
            outcomes.append(dict(reference=s['region_ref'], resolved=True, region=resolution))
        except ValueError as exc:
            outcomes.append(dict(reference=s['region_ref'], resolved=False, error=str(exc)))
    result = dict(actual_input_reconstructed_exactly=True,
        actual_reply_reference_present=True, actual_reply_file_version_current=True,
        supplied_reference=action['region'], source_path=source['path'],
        source_extent=[source['returned_start_line'], source['returned_end_line']],
        all_displayed_reference_resolution=outcomes,
        no_model_inference=True, no_check_execution=True, no_candidate_change=True)
    (AREA / 'review/RESOLVER_PROBE.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
