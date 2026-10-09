"""Replay public acquisitions from crowded E18 states; zero model completions."""
import argparse
import copy
import json
from functools import lru_cache
from pathlib import Path
import sys
from types import SimpleNamespace

AREA = Path(__file__).resolve().parent
sys.path.insert(0, str(AREA.parent / 'evolving_observation_entry'))
import observation_task as study
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.decision_session import DecisionSession
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

ROOT, RUN = study.ROOT, study.AREA / 'run-001'
runner = load_helper('group_native_runner', 'scripts/run_uncoached_contribution.py')
BOUND = {}
TAGS = ('C02', 'C17', 'C19', 'C20', 'C22', 'C26', 'C10', 'C11')
MIXED = TAGS[:5]


@lru_cache(maxsize=None)
def stored(name):
    seal_path = RUN / 'RESPONSE_SEAL.json'
    seal = study.read(seal_path)
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    row, = [r for r in seal['files'] if r['path'] == name]
    path = RUN / name
    assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256']
    BOUND[path.relative_to(ROOT).as_posix()] = row['sha256']
    BOUND[seal_path.relative_to(ROOT).as_posix()] = sha256_file(seal_path)
    return study.read(path)


def restored(tag):
    prior = f'C{int(tag[1:])-1:02d}'
    ops = stored(f'calls/{prior}-host-result.json')['operations']
    stem = f'after/{prior}-O{len(ops):02d}'
    session = study.restore(stored(stem+'-state.json'), stored(stem+'-candidate.json'), RUN, replay=True)
    feedback = copy.deepcopy(stored(stem+'-preceding-feedback.json'))
    reply = copy.deepcopy(stored(f'calls/{tag}-reply.json'))
    return session, feedback, reply


class ProportionalOnly(study.Session):
    """Diagnostic comparator with the same new reporting, not a production mode."""
    _fit_pages = DecisionSession._fit_pages


def cases(module, loop, adapter, store):
    rows = []
    def save(name, value):
        artifact = store.put(name, canonical_json_bytes(value))
        if loop.log is not None:
            loop.log.append('saved_state_qualification', dict(name=name, completion_sent=False), [artifact])

    for tag in TAGS:
        outcomes = {}
        for mode in (('proportional_only', 'completed_regions') if tag in MIXED else ('completed_regions',)):
            session, feedback, reply = restored(tag)
            adapter.preceding_feedback[:] = feedback
            if mode == 'proportional_only':
                session.__class__ = ProportionalOnly
            prefix = f'{tag}/{mode}'
            original = canonical_json_bytes(session.pairs)
            candidate, ranges = session.candidate, copy.deepcopy(session.ranges)
            raw = loop.measure(session.view())
            # New truthful history fields may require the existing presentation
            # fallback at a restored old near-limit state. No selection is lost.
            if raw > 23808:
                assert session._fits_feedback(loop.measure)
            before = loop.measure(session.view())
            input_mode = session.view()['presentation']['mode']
            assert before <= 23808 and session.ranges == ranges and session.candidate == candidate
            assert canonical_json_bytes(session.pairs) == original
            save(prefix+'-input.json', dict(view=session.view(), preceding=adapter.preceding_feedback,
                snapshot=module.snapshot(session), candidate=json.loads(module.candidate_bytes(session.candidate))))
            session.mark_delivered(session.view())
            session.begin_request()
            result = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
            following = loop.measure(session.view())
            assert following <= 23808 and not session.delivery_blocked
            assert session.candidate == candidate and canonical_json_bytes(session.pairs[:len(json.loads(original))]) == original
            reloaded = study.restore(module.snapshot(session), session.candidate, RUN, replay=True)
            assert reloaded.view() == session.view()
            save(prefix+'-after.json', dict(view=session.view(), preceding=adapter.preceding_feedback,
                snapshot=module.snapshot(session), reply=reply, outcome=result))
            row = dict(case=tag, variant=mode, raw_input_tokens=raw, admitted_input_tokens=before,
                following_input_tokens=following, input_mode=input_mode, following_mode=session.view()['presentation']['mode'],
                returned_sources=[{k:v for k,v in source.items() if k!='content'}
                    for source in result['operations'][-1]['result'].get('sources', [])],
                action=reply['operation']['action'], accepted=result['operations'][-1]['result'].get('accepted'),
                candidate_unchanged=True, exact_restoration=True)
            rows.append(row)
            outcomes[mode] = session
        if tag in MIXED:
            base, completed = outcomes['proportional_only'], outcomes['completed_regions']
            old, new = base.pairs[-1]['result']['sources'], completed.pairs[-1]['result']['sources']
            assert base.pairs[:-1] == completed.pairs[:-1] and base.saved == completed.saved
            assert base.working_account() == completed.working_account()
            for previous, current in zip(old, new, strict=True):
                assert current['returned_start_line'] == previous['returned_start_line']
                assert current['returned_end_line'] >= previous['returned_end_line']
                assert current['content'].startswith(previous['content'])
                if current['path'] in study.REQUIRED_INSPECTION_PATHS:
                    assert current == previous, 'completion took back or changed a bulk page'
            small = [s for s in new if s['path'] in (study.TARGET,study.SECONDARY)]
            assert small and all(s['requested_extent_complete'] for s in small)
    adapter.preceding_feedback.clear()
    return rows


def main(version):
    for tag in TAGS:
        restored(tag)  # Authenticate every inherited input before runtime ownership.
    folder = AREA / ('qualification-' + version)
    folder.mkdir(exist_ok=False)
    module, store = study.Task(), ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl', 'group-acquisition-qualification', task_module=module)
    bound = {**module.source_identities(), **BOUND,
        **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in AREA.glob('*.py')},
        **{(ROOT/'tests'/name).relative_to(ROOT).as_posix(): sha256_file(ROOT/'tests'/name)
           for name in ('test_group_acquisition.py','test_acquisition_feedback.py')},
        (AREA/'IMPLEMENTATION_NOTES.md').relative_to(ROOT).as_posix(): sha256_file(AREA/'IMPLEMENTATION_NOTES.md')}
    rows, route, error = [], None, None
    def save(name, value):
        item = store.put(name, canonical_json_bytes(value))
        log.append('qualification_artifact', dict(name=name,completion_sent=False), [item])
    try:
        save('INPUT_BINDINGS.json', BOUND)
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            adapter = runner.Adapter(module)
            loop = runner.Loop(folder,store,log,url=url,task_module=adapter,
                source_check=lambda: module.verify_sources(bound))
            rows = cases(module,loop,adapter,store)
            # Reuse the existing evidence-supported edit/check/submission route
            # and actual capacity-rejection/replacement route, without new tools.
            route = qualification_route.qualify(module,loop,adapter,store,folder)
            module.verify_sources(bound)
    except BaseException as problem:
        error = problem
        save('FAILED.json',dict(type=type(problem).__name__,message=str(problem)))
    finally:
        save('QUALIFICATION.json',dict(status='failed' if error else 'qualified',completion_requests=0,
            cases=rows,route=route,policy='reported historical ranges plus bounded requested-region completion',
            memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT),
            classification='scripted mechanical and information-path qualification; no actor behavior'))
        verify_records(folder/'records.jsonl',folder)
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:
        raise error
    print(json.dumps(dict(status='qualified',cases=[{k:v for k,v in row.items() if k!='returned_sources'} for row in rows],
        route_steps=len(route['trials']),crowded_steps=route['crowded_transition']['steps'],completion_requests=0),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    assert len(args.version)==3 and args.version.isascii() and args.version.isdecimal()
    main(args.version)
