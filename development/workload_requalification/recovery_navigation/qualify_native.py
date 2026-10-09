"""Exact saved-state/native-input qualification; never sends a completion."""
import argparse
import copy
from pathlib import Path
from types import SimpleNamespace

import fixture
import navigation
import run_dispatch as driver
from manage import RUNTIME, legacy
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

AREA, ROOT = fixture.AREA, fixture.ROOT
CASES = {'C23': 'C22-O01', 'C24': 'C23-O01', 'C26': 'C25-O02',
         'C29': 'C28-O01', 'C31': 'C30-O02', 'C33': 'C32-O01'}


def identities():
    paths = [*AREA.glob('*.py'), *sorted((AREA/'tests').glob('*.py')),
             AREA/'PLAN.md', AREA/'cpu-qualification-003/RESULTS.json',
             fixture.RUN/'RESPONSE_SEAL.json']
    return {**fixture.previous.Task('001').source_identities(),
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


def frames():
    """Check wire equality before occupying the runtime."""
    result = []
    task = fixture.previous.Task('001')
    for tag, stem in CASES.items():
        old, new = fixture.restored(stem, projected=False), fixture.restored(stem)
        original = (fixture.RUN/f'calls/{tag}-wire-request.json').read_bytes()
        adapter = driver.runner.Adapter(task)
        adapter.preceding_feedback = fixture.read(fixture.RUN/f'after/{stem}-preceding-feedback.json')
        assert completion_request_bytes(adapter.request_for(old.view())) == original, tag
        changed = new.view()
        stripped = copy.deepcopy(changed)
        stripped['recent_activity'] = old.view()['recent_activity']
        assert stripped == old.view(), tag
        assert fixture.snapshot(old) == fixture.snapshot(new)
        result.append((tag, stem, adapter, old, new))
    return result


def qualify(version):
    folder = AREA/f'native-qualification-{version}'
    folder.mkdir(exist_ok=False)
    store = ArtifactStore(folder)
    task = fixture.previous.Task('001')
    log = legacy.QualificationLog(folder/'records.jsonl', 'recovery-navigation', task_module=task)
    bound = identities()
    trials, native_forms, error = [], None, None
    try:
        prepared = frames()
        server, model, _ = task.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = driver.Loop(folder, store, log, url=url,
                task_module=prepared[0][2], source_check=lambda: task.verify_sources(bound))
            for tag, stem, adapter, old, new in prepared:
                loop.task = adapter
                before, after = loop.measure(old.view()), loop.measure(new.view())
                assert before <= 23808 and after <= 23808
                store.put(tag+'-original-wire.json', completion_request_bytes(adapter.request_for(old.view())))
                store.put(tag+'-projected-wire.json', completion_request_bytes(adapter.request_for(new.view())))
                loop.snapshot(new, tag+'-restored')
                fallback = new.clone()
                fallback.last = dict(fallback.last, **{navigation.SETTING: -1})
                predecessor = old.clone()
                predecessor.last = dict(predecessor.last, **{navigation.SETTING: -1})
                assert completion_request_bytes(adapter.request_for(fallback.view())) == completion_request_bytes(adapter.request_for(predecessor.view()))
                fallback_count = loop.measure(fallback.view())
                assert fallback_count <= 23808
                restored = task.restore(fixture.snapshot(new), new.candidate, fixture.RUN, replay=True)
                restored.__class__ = fixture.Session
                assert restored.view() == new.view()
                trials.append(dict(case=tag, checkpoint=stem, recovery=new.recovery,
                    old_tokens=before, projected_tokens=after, fallback_tokens=fallback_count,
                    ordinary_unchanged=old.view()==new.view(), fallback_exact=True,
                    state_unchanged=True, serialized_restore_exact=True))
                print(tag, before, after, fallback_count, flush=True)
            # The displayed historical search provides these coordinates. The
            # scripted replacement is engineering qualification, not a model choice.
            loop.task = prepared[1][2]
            session = fixture.restored()
            page = next(r['navigation']['observed_page'] for r in session.view()['recent_activity']
                if r.get('navigation', {}).get('observed_page', {}).get('query') == 'ParsingError')
            hit = page['matches'][0]
            path, line = page['path'], hit['line']
            assert line == 1375  # Observed fixture fact, not supplied task advice.
            operation = dict(action='work_on', sources=[dict(path=path,
                start_line=max(1,line-20), end_line=line+20)], results=[])
            session.mark_delivered(session.view())
            store.put('replacement-basis.json', canonical_json_bytes(dict(
                observed_page=page, operation=operation,
                interpretation='Researcher selects context around an actual delivered hit; no task solution supplied.')))
            outcome = task.process_reply(session, dict(discussion='Engineering qualification.', operation=operation),
                loop.measure, loop.task.preceding_feedback)
            assert all(row['result']['accepted'] for row in outcome['operations']), outcome
            assert not session.recovery and not session.delivery_blocked
            assert session.candidate.candidate_id == prepared[1][4].candidate.candidate_id
            count = loop.measure(session.view())
            assert count <= 23808
            store.put('replacement-outcome.json', canonical_json_bytes(outcome))
            store.put('replacement-wire.json', completion_request_bytes(loop.task.request_for(session.view())))
            loop.snapshot(session, 'replacement')
            trials.append(dict(case='delivered-hit-to-selection', tokens=count,
                candidate_unchanged=True, normal_view_restored=True))
            native_forms = driver.native_forms.qualify(folder/'native-forms', task=task,
                request=loop.task.request_for(session.view()), source_identities=identities)
            task.verify_sources(bound)
    except BaseException as problem:
        error = problem
        store.put('FAILED.json', canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))
    finally:
        store.put('RESULTS.json', canonical_json_bytes(dict(trials=trials,
            native_forms=native_forms, completion_requests=0, new_checker_executions=0,
            memory=RUNTIME.memory_stats(folder/'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT))))
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference',
                    bound, completion_requests=0)
    if error:
        raise error
    print(dict(status='qualified_no_model_inference', trials=len(trials),
               records=len(verify_records(folder/'records.jsonl', folder))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--frames-only', action='store_true')
    args = parser.parse_args()
    if args.frames_only:
        print([row[0] for row in frames()])
    else:
        qualify(args.version)
