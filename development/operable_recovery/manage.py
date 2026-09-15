"""Native information-path qualification and one separately frozen uncoached run."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import operable_task as study
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

RUNTIME = study.base.base
IMPL = 'Lib/urllib/parse.py'
TEST_ANCHOR = 'if __name__ == "__main__":\n    unittest.main()\n'
DOC_ANCHOR = 'URL Parsing\n-----------\n'


def load_helper(name, relative):
    spec = importlib.util.spec_from_file_location(name, study.ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load_helper('operable_qualification_support', 'development/working_set_continuation/manage.py')


def scripted_reply(module, view, number):
    """Use only this input plus declared reference work; audit every dependency.

    The reference code is researcher-authored qualification, never model input.
    Addresses must come from actual feedback/account, not reference coordinates.
    """
    latest = view['latest_feedback']['result']
    text = view['working_account']['text'] if view.get('working_account') and 'text' in view['working_account'] else '{}'
    account = json.loads(text)
    refs = account.get('references', {})
    evidence = []

    def reply(operation, explanation):
        return dict(discussion='Researcher-scripted information-path qualification.',
                    account=json.dumps(dict(references=refs, understanding=explanation), ensure_ascii=False),
                    operation=operation), evidence

    def search(path, query):
        return dict(action='search', path=path, query=query, offset=0, limit=8)

    def exact(names):
        return dict(action='work_on_exact', regions=[refs[n] for n in names], results=[])

    def remember(name, row):
        refs[name] = row['region_ref']
        evidence.append(dict(use='copy returned region reference', name=name, returned=row))

    def patch(path, old, new):
        # Editing coordinates are not borrowed from the researcher's checkout.
        sources = list(view['working_set']['sources'])
        sources += ([latest['source']] if 'source' in latest else latest.get('sources', []))
        source, = [s for s in sources if s['path']==path and old in s['content']]
        evidence.append(dict(use='exact current insertion/replacement text is delivered',
                             region_ref=source['region_ref'], old=old))
        return dict(action='patch', path=path, old=old, new=new,
                    expected_candidate_id=view['candidate_id'], expected_file_sha256=source['file_sha256'])

    if number == 1:
        evidence.append(dict(use='task identifies port behavior; selected inventory identifies implementation path',
                             path=IMPL, query_is_hypothesis=True))
        assert IMPL in [r.get('path') for r in view['selection']['entries']]
        return reply(search(IMPL, 'def port'), 'Locate the governing accessor; do not assume its behavior yet.')
    if number == 2:
        row, = [r for r in latest['regions'] if latest['matches'][0]['line']==r['match_line']]
        remember('port', row)
        return reply(exact(['port']), 'Read the returned accessor region; source is not established by its search snippet.')
    if number == 3:
        source, = latest['sources']
        assert 'port = self._hostinfo[1]' in source['content'] and 'Port out of range 0-65535' in source['content']
        evidence.append(dict(use='accessor names the dependency', exact='_hostinfo', source=source['region_ref']))
        return reply(search(IMPL, 'def _hostinfo'), 'The accessor validates ASCII digits and range at access; inspect how no/empty ports are represented.')
    if number == 4:
        assert len(latest['regions'])==2
        for index, row in enumerate(latest['regions']):
            remember('hostinfo'+str(index), row)
        return reply(exact(['port','hostinfo0','hostinfo1']), 'Compare the actual string/bytes host-info paths with the accessor.')
    if number == 5:
        assert all('if not port:' in s['content'] and 'port = None' in s['content'] for s in latest['sources'][1:])
        evidence.append(dict(use='both delivered paths normalize absent/empty port to None', sources=[s['region_ref'] for s in latest['sources']]))
        return reply(dict(action='read', path=study.TEST, start_line=1, end_line=5),
                     'Inspected paths normalize absent/empty ports to None; accessor validates digits/range. Proposed construction-timing expectations still need execution. Inspect test imports.')
    if number == 6:
        source = latest['source']
        assert 'import unittest' in source['content'] and 'import urllib.parse' in source['content']
        remember('header', source)
        evidence.append(dict(use='search for conventional module-level insertion boundary; not presumed found', query='if __name__'))
        return reply(search(study.TEST, 'if __name__'), 'Required imports are present; find a module-level place for additive regression work.')
    if number == 7:
        row, = latest['regions']
        remember('test_anchor', row)
        return reply(exact(['port','hostinfo0','hostinfo1','header','test_anchor']),
                     'Keep governing implementation, imports and the returned test boundary together; proposed assertions still need execution.')
    if number == 8:
        code = (study.prior.AREA/'REFERENCE_TEST.py').read_text(encoding='utf-8')
        if module.scenario=='correction':
            code = code.replace("('Port out of range 0-65535'", "('WRONG RANGE MESSAGE'")
        evidence.append(dict(use='researcher-authored test proposal; deliberately wrong expectation only in correction qualification',
                             supplied_to_model_run=False, correctness_not_assumed=True))
        return reply(patch(study.TEST, TEST_ANCHOR, code+'\n\n'+TEST_ANCHOR),
                     'These assertions are proposed work. Consume the actual triggered tests check before using them as confirmation.')
    if module.scenario=='correction':
        if number == 9:
            failure = latest['report']['primary_real_failure']
            diagnostic = failure['diagnostic']['text']
            assert not latest['passed'] and 'WRONG RANGE MESSAGE' in diagnostic and 'Port out of range 0-65535' in diagnostic
            evidence.append(dict(use='actual displayed failed-test diagnostic supplies the mismatch', observation=latest['observation'], diagnostic=diagnostic))
            return reply(patch(study.TEST, "('WRONG RANGE MESSAGE'", "('Port out of range 0-65535'"),
                         'The actual failed-test diagnostic contradicts the proposed range message. Correct it; documentation remains unfinished.')
        number -= 1
    if number == 9:
        assert latest['executed'] and latest['passed'] and latest['check_id']=='tests'
        evidence.append(dict(use='actual tests-scope pass; documentation remains unchecked', observation=latest['observation']))
        return reply(search(study.DOC, 'URL Parsing'), 'The saved tests pass their scope on the current candidate. Locate the documentation section without discarding saved tests.')
    if number == 10:
        match, = [m for m in latest['matches'] if m['text']=='URL Parsing']
        row, = [r for r in latest['regions'] if r['match_line']==match['line']]
        evidence.append(dict(use='select the returned exact heading match, not the other prose matches', match=match))
        remember('doc_anchor', row)
        return reply(exact(['doc_anchor']), 'Change the supporting group to the returned documentation section. Saved tests remain in the candidate; public check is still required.')
    if number == 11:
        code = (study.prior.AREA/'REFERENCE_DOC.txt').read_text(encoding='utf-8')
        return reply(patch(study.DOC, DOC_ANCHOR, code+'\n'+DOC_ANCHOR),
                     'These examples must execute in the triggered public check; the earlier tests pass is not documentation verification.')
    if number == 12:
        assert latest['passed'] and latest['executed'] and latest['checked_candidate_id']==view['candidate_id'] and latest['check_id']=='public'
        evidence.append(dict(use='actual public result on current candidate permits closure', observation=latest['observation']))
        return reply(dict(action='submit', expected_candidate_id=view['candidate_id']),
                     'Tests and executable documentation passed the current public check. Prose still receives separate review.')
    raise AssertionError('undeclared qualification transition')


def verify(module, folder):
    verifier = load_helper('operable_exact_replay', 'development/working_set_continuation/review/verify.py')
    replay_task = study.Task(module.scenario, replay_folder=folder)
    verifier.task = replay_task
    result = verifier.verify(folder)
    records = verify_records(folder/'records.jsonl', folder)
    observed = [r for r in records if r['record_type']=='check_observation_preserved']
    from working_set_exp.observations import ObservationStore
    store = ObservationStore(folder/'observations', replay=True)
    for record in observed:
        saved = store.read(record['payload']['observation'])
        assert {k:record['payload'][k] for k in saved}==saved
        assert set(record['payload'])-set(saved) <= {'qualification_only','completion_sent'}
    closed = [r['payload'] for r in records if r['record_type']=='runtime_closed']
    assert len(closed)==1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    return {**result, 'observations_replayed_without_reexecution':len(observed), 'owned_runtime_closed':True}


def control_screen(session, adapter, loop, store):
    initial = loop.measure(session.view())
    rows = [dict(case='actual_broad_recovery', tokens=initial)]
    worst = session.clone()
    worst.task = 'Control-task boundary. '*370  # 8,140 supported task bytes.
    worst.ranges = [dict(path=study.TEST, start_line=i, end_line=i) for i in range(1,800,2)]
    worst._record(dict(action='record_account', text='Provisional. '*60000),
                  dict(accepted=True, input_candidate_id=worst.candidate.candidate_id, written_during_request=0))
    worst._record(dict(action='selection_page', offset=0), dict(accepted=False, error='Recorded obstacle. '*50000))
    worst.enter_recovery('synthetic supported control boundary; not task material')
    assert worst._fits_feedback(loop.measure)
    count = loop.measure(worst.view())
    rows.append(dict(case='large_account_error_and_400_designated_regions', tokens=count,
                     account_retained_bytes=len(worst.working_account()['text'].encode()),
                     shown_account_bytes=len(worst.view()['working_account']['text_prefix'].encode())))
    result = worst.execute(dict(action='work_on', sources=[], results=[]), loop.measure)
    assert not result['accepted']  # Full large account cannot fit ordinary mode.
    assert not worst.delivery_blocked and worst.recovery
    from working_set_exp.accounted_contribution import process_reply
    worst.mark_delivered(worst.view())
    worst.begin_request()
    outcome = process_reply(worst, dict(discussion='Synthetic control qualification.', account='Narrowed account.',
        operation=dict(action='work_on_exact', regions=[], results=[])), loop.measure, adapter.preceding_feedback)
    assert all(o['result']['accepted'] for o in outcome['operations']) and not worst.recovery
    rows.append(dict(case='account_and_empty_replacement_exit', tokens=loop.measure(worst.view())))
    adapter.preceding_feedback.clear()
    store.put('CONTROL_PATH.json', canonical_json_bytes(rows))


def prepare(module):
    folder = module.PACKAGE
    folder.mkdir(parents=True, exist_ok=False)
    bound = module.source_identities()
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl', 'operable-qualification-'+module.scenario, task_module=module)
    session, adapter = module.initial_session(), runner.Adapter(module)
    study.attach_observations(session, folder, log)
    server, model, _ = study.runtime_paths()
    error, initial, outcome = None, None, None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            def scripted(url, route, wire, timeout):
                assert route=='/v1/chat/completions'
                request = json.loads(wire)
                count = loop.cache[sha256_bytes(canonical_json_bytes(request))]['prompt_tokens']
                actual_view = json.loads(request['messages'][1]['content'])['workspace']
                reply, justification = scripted_reply(module, actual_view, loop.sent)
                store.put(f'information-path/C{loop.sent:02d}.json', canonical_json_bytes(justification))
                return canonical_json_bytes(dict(choices=[dict(finish_reason='stop', message=dict(reasoning_content='', content=json.dumps(reply)))],
                    usage=dict(prompt_tokens=count, completion_tokens=1, total_tokens=count+1, prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter, post=scripted,
                source_check=lambda:module.verify_sources(bound))
            loop.measure(session.view())
            initial = {k:next(iter(loop.cache.values()))[k] for k in ('prompt_tokens','request_sha256','native_sha256','wire_request_sha256')}
            store.put('initial-wire-request.json', completion_request_bytes(adapter.request_for(session.view())))
            if module.scenario=='complete':
                control_screen(session, adapter, loop, store)
            outcome = loop.execute(session)
            assert outcome['submitted']
            checks = [p['result']['passed'] for p in session.pairs[5:] if p['response']['action']=='check']
            assert checks == ([False,True,True] if module.scenario=='correction' else [True,True])
            assert all(not r['payload'].get('completion_sent') for r in verify_records(folder/'records.jsonl',folder))
    except BaseException as problem:
        error = problem
        study.save(folder,'FAILED.json',dict(type=type(problem).__name__,message=str(problem)))
    finally:
        study.save(folder,'QUALIFICATION.json',dict(initial=initial, scripted_outcome=outcome, completion_requests=0,
            scenario=module.scenario, memory=RUNTIME.memory_stats(folder/'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference',bound,completion_requests=0)
    if error:
        raise error
    checked = verify(module,folder)
    study.save(study.AREA,folder.name+'-VERIFICATION.json',checked)
    print(json.dumps(checked),flush=True)


def publish(module, correction):
    for package in (module.PACKAGE, correction.PACKAGE):
        assert study.read(package/'SEAL.json')['status']=='qualified_no_model_inference'
        verify(module if package==module.PACKAGE else correction,package)
    report = study.read(module.PACKAGE/'QUALIFICATION.json')
    study.save(study.AREA,module.MANIFEST.name,dict(actor=study.ACTOR,seed=study.SEED,
        maximum_requests=study.MAX_REQUESTS,maximum_operations=study.MAX_OPERATIONS,
        source_sha256=study.source_identities(),preparation_seal_sha256=sha256_file(module.PACKAGE/'SEAL.json'),
        correction_package=correction.PACKAGE.name,correction_seal_sha256=sha256_file(correction.PACKAGE/'SEAL.json'),
        preparation_package=module.PACKAGE.name,initial=report['initial'],
        starting_candidate=study.starting_candidate().candidate_id, inherited_operations=5,
        checkpoint_sha256=sha256_file(study.SOURCE_STATE), initial_selection='recorded broad designation; temporary recovery presentation',
        no_live_coaching=True,automatic_retry=False,
        owner_direction='Proceed to implement the observation and recovery plan, including one separately frozen uncoached contribution.'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','publish','run','verify'))
    parser.add_argument('--scenario',default='complete',choices=('complete','correction'))
    parser.add_argument('--version',default='001')
    parser.add_argument('--correction-version',default='001')
    args=parser.parse_args()
    module=study.Task(args.scenario,args.version)
    if args.mode=='prepare':
        prepare(module)
    elif args.mode=='publish':
        publish(module,study.Task('correction',args.correction_version))
    elif args.mode=='verify':
        print(json.dumps(verify(module,module.RUN),indent=2))
    else:
        manifest=study.read(module.MANIFEST)
        module.PACKAGE=study.AREA/manifest['preparation_package']
        assert sha256_file(study.AREA/manifest['correction_package']/'SEAL.json')==manifest['correction_seal_sha256']
        runner.run_once(SimpleNamespace(owner_direction=manifest['owner_direction'],manifest_sha256=sha256_file(module.MANIFEST)),module)
