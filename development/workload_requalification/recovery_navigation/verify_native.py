"""Replay exact custody, native inputs and selection; no runtime or inference."""
import ast
import json
from types import SimpleNamespace

import qualify_native as qualification
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

fixture = qualification.fixture
AREA, ROOT = fixture.AREA, fixture.ROOT
core = ROOT/'development/workload_requalification/url_port_entry/review/verify_run.py'
assert sha256_file(core) == '0c62d4c9d6285901d9d8c8017c2d366442148d26f12d422e2ce750f477532ed6'
tree = ast.parse(core.read_text(encoding='utf-8'))
helpers = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)
    and node.name in ('_within', '_inventory', '_native_counts')], type_ignores=[])
namespace = dict(study=fixture.previous, canonical_json_bytes=canonical_json_bytes,
    sha256_bytes=sha256_bytes, sha256_file=sha256_file,
    completion_request_bytes=qualification.completion_request_bytes)
exec(compile(helpers, str(core), 'exec'), namespace)


def verify():
    folder = AREA/'native-qualification-001'
    seal = fixture.read(folder/'SEAL.json')
    namespace['_inventory'](folder, seal)
    fixture.previous.verify_sources(seal['source_sha256'])
    records = verify_records(folder/'records.jsonl', folder)
    assert not any(row['record_type'] == 'invocation_started' for row in records)
    assert seal['status'] == 'qualified_no_model_inference' and seal['completion_requests'] == 0
    task = fixture.previous.Task('001')
    adapter = qualification.driver.runner.Adapter(task)
    counts = namespace['_native_counts'](folder, records, adapter)
    for tag, stem, adapter, old, new in qualification.frames():
        for label, session in [('original', old), ('projected', new)]:
            raw = qualification.completion_request_bytes(adapter.request_for(session.view()))
            assert raw == (folder/f'{tag}-{label}-wire.json').read_bytes()
            assert sha256_bytes(canonical_json_bytes(adapter.request_for(session.view()))) in counts
        state = fixture.read(folder/f'{tag}-restored-state.json')
        restored = task.restore(state, fixture.read(folder/f'{tag}-restored-candidate.json'), fixture.RUN, replay=True)
        restored.__class__ = fixture.Session
        assert restored.view() == new.view()
    adapter = qualification.frames()[1][2]
    session = fixture.restored()
    session.mark_delivered(session.view())
    operation = fixture.read(folder/'replacement-basis.json')['operation']
    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    result = task.process_reply(session, dict(discussion='Engineering qualification.', operation=operation),
                                measure, adapter.preceding_feedback)
    assert canonical_json_bytes(result) == (folder/'replacement-outcome.json').read_bytes()
    assert canonical_json_bytes(fixture.snapshot(session)) == (folder/'replacement-state.json').read_bytes()
    assert qualification.completion_request_bytes(adapter.request_for(session.view())) == (folder/'replacement-wire.json').read_bytes()
    proof = fixture.read(folder/'RESULTS.json')
    assert proof['port_free'] and all(row['expected'] == row['accepted_including_eos']
        for row in proof['native_forms']['cases'])
    return dict(status='replayed_exactly', artifacts=len(seal['files']),
        source_bindings=len(seal['source_sha256']), records=len(records), native_inputs=len(counts),
        native_forms=len(proof['native_forms']['cases']), restored_states=7,
        completion_requests=0, new_checker_executions=0, native_calls=0)


if __name__ == '__main__':
    output = verify()
    path = AREA/'VERIFICATION-001.json'
    raw = canonical_json_bytes(output)
    if path.exists():
        assert path.read_bytes() == raw
    else:
        path.write_bytes(raw)
    print(json.dumps(output, indent=2))
