"""Native saved-state projection and capture transitions; no model completions."""
import argparse
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import closure_task as study
import run_closure as controller
sys.path.insert(0, str(HERE.parent))
import verify_run as audit
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

MODULE = study.Task('E14-CLOSURE-MINT')
RUN = MODULE.RUN
BOUND = {}


def original(name):
    seal = MODULE.read(RUN / 'RESPONSE_SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    row, = [r for r in seal['files'] if r['path'] == name]
    path = RUN / name
    assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256']
    BOUND[path.relative_to(study.ROOT).as_posix()] = row['sha256']
    BOUND[(RUN/'RESPONSE_SEAL.json').relative_to(study.ROOT).as_posix()] = sha256_file(RUN/'RESPONSE_SEAL.json')
    return MODULE.read(path)


def restored(tag):
    stem = dict(C02='C01-O01', C03='C02-O02')[tag]
    state = original(f'after/{stem}-state.json')
    candidate = original(f'after/{stem}-candidate.json')
    session = MODULE.restore(state, candidate, RUN, replay=True)
    feedback = original(f'after/{stem}-preceding-feedback.json')
    request = original(f'calls/{tag}-wire-request.json')
    return session, feedback, request


def cases(loop, adapter, store):
    rows = []
    for tag in ('C02', 'C03'):
        session, feedback, old_request = restored(tag)
        adapter.preceding_feedback[:] = feedback
        actual = adapter.request_for(session.view())
        expected = copy.deepcopy(old_request)
        envelope = json.loads(expected['messages'][-1]['content'])
        row, = [r for r in envelope['workspace']['imported_observations']['entries'] if r['handle']=='OBS-0002']
        assert row['shown_complete'] is False
        row['shown_complete'] = True
        expected['messages'][-1]['content'] = canonical_json_bytes(envelope).decode()
        assert actual == expected, 'Changes exceed the one incorrect visibility flag'
        count = loop.measure(session.view())
        assert count <= 23808
        value = dict(tag=tag, input_tokens=count, only_changed_field='OBS-0002.shown_complete',
            request=actual, snapshot=MODULE.snapshot(session), preceding=feedback)
        store.put(tag+'.json', canonical_json_bytes(value))
        rows.append(dict(tag=tag, input_tokens=count))

    session, feedback, _ = restored('C02')
    adapter.preceding_feedback[:] = feedback
    original_pairs = canonical_json_bytes(session.pairs)
    for name, operation in [
        ('modern-reacquisition', dict(action='reopen_observation', handle='OBS-0002')),
        ('release', dict(action='work_on', sources=[], results=[])),
        ('legacy-recovery', dict(action='reopen_result', handle='RES-0001', offset=0))]:
        before = session.view()
        before_count = loop.measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion='Mechanical native qualification; no actor decision.', operation=operation)
        result = MODULE.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        assert result['operations'][-1]['result']['accepted']
        after = session.view()
        shown = after['imported_observations']['entries'][1]['shown_complete']
        assert shown is (name != 'release')
        assert session.candidate.candidate_id == MODULE.STARTING_ID
        assert canonical_json_bytes(session.pairs[:6]) == original_pairs
        assert not after['verification']['submission']['eligible']
        if name == 'modern-reacquisition':
            assert 'RES-0001' not in session.saved
        if name == 'legacy-recovery':
            session.mark_delivered(after)
            assert session.delivered_sources == []
        count = loop.measure(after)
        assert count <= 23808 and not session.delivery_blocked
        state = MODULE.snapshot(session)
        assert MODULE.restore(state, session.candidate, RUN, replay=True).view() == after
        store.put(name+'.json', canonical_json_bytes(dict(before=before, reply=reply, result=result,
            after=after, snapshot=state, preceding=adapter.preceding_feedback)))
        rows.append(dict(tag=name, input_tokens=before_count, following_tokens=count, shown_complete=shown))
    adapter.preceding_feedback.clear()
    return rows


def qualify(folder):
    for tag in ('C02', 'C03'):
        restored(tag)
    folder.mkdir(exist_ok=False)
    store = ArtifactStore(folder)
    log = controller.legacy.QualificationLog(folder/'records.jsonl', 'legacy-capture-visibility', task_module=MODULE)
    bound = {**MODULE.source_identities(), **BOUND,
             Path(__file__).relative_to(study.ROOT).as_posix(): sha256_file(Path(__file__))}
    rows, error = [], None
    try:
        server, model, _ = MODULE.runtime_paths()
        with controller.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            adapter = controller.runner.Adapter(MODULE)
            loop = controller.runner.Loop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: MODULE.verify_sources(bound))
            rows = cases(loop, adapter, store)
            MODULE.verify_sources(bound)
    except BaseException as problem:
        error = problem
        store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))
    finally:
        store.put('QUALIFICATION.json', canonical_json_bytes(dict(status='failed' if error else 'qualified',
            completion_requests=0, cases=rows, port_free=controller.RUNTIME.port_free(controller.RUNTIME.PORT),
            memory=controller.RUNTIME.memory_stats(folder/'memory.csv'))))
        verify_records(folder/'records.jsonl', folder)
        controller.legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound,
            completion_requests=0)
    if error:
        raise error


def verify(folder):
    report, seal = MODULE.read(folder/'QUALIFICATION.json'), MODULE.read(folder/'SEAL.json')
    assert report['status']=='qualified' and report['completion_requests']==0 and report['port_free']
    audit._inventory(folder, seal)
    MODULE.verify_sources(seal['source_sha256'])
    records = verify_records(folder/'records.jsonl', folder)
    assert not any(r['record_type']=='invocation_started' for r in records)
    adapter = controller.runner.Adapter(MODULE)
    counts = audit._native_counts(folder, records, adapter)
    used = set()
    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts
        used.add(key)
        return counts[key]
    class ExactStore:
        def put(self, name, raw):
            assert (folder/name).read_bytes()==raw, name
    assert cases(SimpleNamespace(measure=measure), adapter, ExactStore()) == report['cases']
    assert used == set(counts)
    closed = [r['payload'] for r in records if r['record_type']=='runtime_closed']
    assert len(closed)==1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    result = dict(status='replayed_exactly', cases=len(report['cases']), native_inputs=len(counts),
        artifacts=len(seal['files']), source_bindings=len(seal['source_sha256']), custody_records=len(records),
        qualification_seal_sha256=sha256_file(folder/'SEAL.json'), no_new_inference_or_execution=True)
    output = folder.with_name(folder.name+'-VERIFICATION.json')
    raw = canonical_json_bytes(result)
    if output.exists():
        assert output.read_bytes()==raw
    else:
        output.write_bytes(raw)
    print(json.dumps(result, indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['qualify', 'verify'])
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    folder = HERE / ('capture-visibility-qualification-'+args.version)
    if args.mode=='qualify':
        qualify(folder)
    else:
        verify(folder)
