"""Native measurements of already requested small regions; never model calls."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import observation_task as study
from manage import RUNTIME, legacy, load_helper
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

RUN = AREA / 'run-001'
runner = load_helper('observation_sizing_review', 'scripts/run_uncoached_contribution.py')
BOUND = {}


def stored(name):
    seal = study.read(RUN / 'RESPONSE_SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    row, = [r for r in seal['files'] if r['path'] == name]
    path = RUN / name
    assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256']
    BOUND[path.relative_to(study.ROOT).as_posix()] = row['sha256']
    return study.read(path)


def cases():
    verification = study.read(AREA / 'review/VERIFICATION-001.json')
    assert verification['status'] == 'replayed_exactly'
    assert verification['response_seal_sha256'] == sha256_file(RUN / 'RESPONSE_SEAL.json')
    rows = []
    for tag in ('C02', 'C17', 'C19', 'C20', 'C22'):
        host = stored(f'calls/{tag}-host-result.json')
        stem = f'after/{tag}-O{len(host["operations"]):02d}'
        session = study.restore(stored(stem+'-state.json'), stored(stem+'-candidate.json'), RUN, replay=True)
        adapter = runner.Adapter(study.Task())
        adapter.preceding_feedback = stored(stem+'-preceding-feedback.json')
        next_tag = f'C{int(tag[1:])+1:02d}'
        wire = stored(f'calls/{next_tag}-wire-request.json')
        assert json.loads(wire['messages'][-1]['content']) == dict(
            workspace=session.view(), preceding_operation_feedback=adapter.preceding_feedback)
        count = stored(f'calls/{next_tag}-endpoint-response.json')['usage']['prompt_tokens']
        other = session.clone()
        old = other.pairs.pop()
        assert old['response']['action'] == 'work_on' and old['result']['accepted']
        result = copy.deepcopy(old['result'])
        completed = []
        for i, (span, source) in enumerate(zip(old['response']['sources'], result['sources'], strict=True)):
            if span['path'] not in (study.TARGET, study.SECONDARY):
                continue
            full = other.source(span)
            if full['returned_end_line'] == source['returned_end_line']:
                continue
            other.ranges = [r for r in other.ranges if r['path'] != span['path']]
            other.add_source(full)
            result['sources'][i] = full
            completed.append(span['path'])
        assert completed
        other._record(old['response'], result)
        assert other.candidate == session.candidate and other.saved == session.saved
        assert other.pairs[:-1] == session.pairs[:-1] and len(other.pairs) == len(session.pairs)
        assert other.working_account() == session.working_account()
        assert other.view()['allowance'] == session.view()['allowance']
        for before, after in zip(old['result']['sources'], other.pairs[-1]['result']['sources'], strict=True):
            if before['path'] not in completed:
                assert before == after
        rows.append((tag, session, other, adapter, count, completed))
    return rows


def main():
    rows = cases()
    folder = AREA / 'review/sizing-001'
    folder.mkdir(exist_ok=False)
    module, store = study.Task(), ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl', 'requested-small-region-diagnostic', task_module=module)
    bound = {**module.source_identities(), **BOUND,
        (RUN/'RESPONSE_SEAL.json').relative_to(study.ROOT).as_posix(): sha256_file(RUN/'RESPONSE_SEAL.json'),
        Path(__file__).relative_to(study.ROOT).as_posix(): sha256_file(Path(__file__)),
        (Path(__file__).parent/'SIZING_PLAN.md').relative_to(study.ROOT).as_posix(): sha256_file(Path(__file__).parent/'SIZING_PLAN.md')}
    output, error = [], None

    def save(name, value):
        item = store.put(name, canonical_json_bytes(value))
        log.append('qualification_artifact', dict(name=name, completion_sent=False), [item])

    try:
        save('INPUT_BINDINGS.json', BOUND)
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = runner.Loop(folder, store, log, url=url, task_module=rows[0][3],
                source_check=lambda: module.verify_sources(bound))
            for tag, baseline, expanded, adapter, expected, completed in rows:
                loop.task = adapter
                counts = {}
                for label, session in [('actual', baseline), ('completed_requested_regions', expanded)]:
                    counts[label] = loop.measure(session.view())
                    save(f'{tag}-{label}-view.json', session.view())
                    loop.snapshot(session, f'{tag}-{label}')
                assert counts['actual'] == expected
                output.append(dict(after_request=tag, completed_paths=completed, input_tokens=counts,
                    preferred_target=22784, hard_ceiling=23808,
                    fits_preferred=counts['completed_requested_regions'] <= 22784,
                    fits_hard=counts['completed_requested_regions'] <= 23808,
                    other_acquired_bodies_unchanged=True, classification='counterfactual_input_not_actor_behavior'))
            module.verify_sources(bound)
    except BaseException as problem:
        error = problem
        save('FAILED.json', dict(type=type(problem).__name__, message=str(problem)))
    finally:
        save('QUALIFICATION.json', dict(status='failed' if error else 'measured', completion_requests=0,
            cases=output, production_policy_changed=False, memory=RUNTIME.memory_stats(folder/'memory.csv'),
            port_free=RUNTIME.port_free(RUNTIME.PORT)))
        verify_records(folder/'records.jsonl', folder)
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound, completion_requests=0)
    if error:
        raise error
    print(json.dumps(dict(status='measured', cases=output), indent=2))


if __name__ == '__main__':
    main()
