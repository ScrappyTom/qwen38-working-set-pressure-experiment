"""Isolated exact-path filter check; no model request or live-state mutation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from working_set_exp.candidate import Candidate
from working_set_exp.working_session import WorkingSession
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

session = WorkingSession(Candidate.create({'app.py': b'value = 1\n'}), b'', 'inspect app.py', call_limit=5)
# The issue is filtering, not input admission; native token capacity is not asserted.
measure = lambda view: len(canonical_json_bytes(view)) // 4
group = session.execute(dict(action='work_on', sources=[dict(path='app.py', start_line=1, end_line=0)], results=[]), measure)
filtered = session.clone().execute(dict(action='history', before=0, path='app.py'), measure)
unfiltered = session.clone().execute(dict(action='history', before=0, path=''), measure)
assert group['accepted'] and filtered['entries'] == [] and [r['sequence'] for r in unfiltered['entries']] == [1]
print(canonical_json_bytes(dict(
    source_sha256=sha256_file(ROOT/'src/working_set_exp/working_session.py'),
    group_acquisition_accepted=group['accepted'], filtered_sequences=[], unfiltered_sequences=[1],
    exact_action_available=bool(session.payload('EVT-0001')),
    finding='File-filtered history omits work_on acquisition; unfiltered history and exact archive retain it.',
    no_model_requests=True, live_state_unchanged=True, native_capacity_not_tested=True)).decode())
