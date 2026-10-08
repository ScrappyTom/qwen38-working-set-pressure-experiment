"""Source-supported engineering transitions; no model or task assistance."""
import completion_task as entry
import engineering_reference as reference
from working_set_exp.jsonutil import canonical_json_bytes


def qualify(module, loop, adapter, store, folder):
    session = module.initial_session(folder / 'scripted')
    module.attach_observations(session, folder / 'scripted', loop.log)
    adapter.preceding_feedback = []
    trace = []

    def act(operation, support):
        before = session.view()
        count = loop.measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=support, operation=operation)
        outcome = module.process_reply(session, reply, loop.measure, adapter.preceding_feedback)
        after = session.view()
        following = loop.measure(after)
        index = len(trace) + 1
        for suffix,value in (('input',before),('reply',reply),('host',outcome),('following',after),('state',module.snapshot(session))):
            store.put(f'route/{index:02d}-{suffix}.json', canonical_json_bytes(value))
        trace.append(dict(step=index, support=support, action=operation['action'],
                          input_tokens=count, following_tokens=following,
                          operations=[r['action']['action'] for r in outcome['operations']]))
        assert following <= 23808 and not session.delivery_blocked
        assert all(r['result']['accepted'] for r in outcome['operations']), outcome
        return outcome

    check=act(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
        'The task is unfinished and the older observation has a different checker. Inspect the actual current outstanding work.')
    assert not check['operations'][-1]['result']['passed']
    header=act(dict(action='read',path=entry.TEST,start_line=1,end_line=70),
        'The task names the target test file. Its imports and testing conventions are needed to add a test.')
    header_source=header['operations'][0]['result']['source']
    assert 'import configparser' in header_source['content']
    tree=act(dict(action='tree',path='Lib',offset=0,limit=16),
        'The acquired tests import configparser. Locate its exact library path through the available directory operation.')
    assert 'Lib/configparser.py' in str(tree)
    outline=act(dict(action='p0_page',path='Lib/configparser.py',offset=0),
        'The task names the policies and exception. The library outline identifies their exact current definitions without guessing coordinates.')
    found={r['name']:r['region_ref'] for r in outline['operations'][0]['result'].get('regions',[])}
    needed=('Error','InterpolationError','InterpolationMissingOptionError','BasicInterpolation','ExtendedInterpolation')
    while any(name not in found for name in needed):
        offset=outline['operations'][0]['result']['next_offset']
        assert offset is not None
        outline=act(dict(action='p0_page',path='Lib/configparser.py',offset=offset),
            'The preceding outline explicitly supplies this continuation; finish locating the requested definitions.')
        found.update({r['name']:r['region_ref'] for r in outline['operations'][0]['result'].get('regions',[])})
    source=act(dict(action='work_on_exact',regions=[found[n] for n in needed]+[header_source['region_ref']],results=[]),
        'Acquire the definitions identified by the outline, including exception bases used by the constructor and diagnostic.')
    assert len(source['operations'][0]['result']['sources'])==len(needed)+1
    search=act(dict(action='search',path=entry.TEST,query='if __name__',offset=0,limit=8),
        'Locate the test module entry guard as an insertion boundary for an independent new TestCase; no existing method needs alteration.')
    region=next(r for r in search['operations'][0]['result']['regions'] if r['extent_kind']=='search context')
    anchor_result=act(dict(action='read',path=entry.TEST,start_line=region['start_line'],end_line=region['end_line']),
        'The exact returned search context identifies the insertion boundary; obtain those current bytes for the guarded edit.')
    shown=anchor_result['operations'][0]['result']['source']['content']
    anchor=shown[shown.index('if __name__'):]
    assert session.candidate.file_map[entry.TEST].decode().count(anchor)==1
    addition=reference.test_addition()
    # Deliberate engineering negative: the acquired constructor and policy raise
    # sites establish main as the requesting section. This wrong expectation is
    # used only to qualify the actual diagnostic-to-correction route.
    weak=addition.replace("expected_args = ('value', 'main', raw, reference)",
                          "expected_args = ('value', 'other', raw, reference)")
    edited=act(dict(action='patch',path=entry.TEST,old=anchor,new=weak+'\n\n'+anchor,
        expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(entry.TEST)),
        'Engineering negative only: save one explicitly incorrect requesting-section expectation to exercise the real triggered failure, with source and insertion anchor visible.')
    failed=edited['operations'][-1]['result']
    assert edited['operations'][-1]['action']['action']=='check' and not failed['passed']
    assert any(row.get('diagnostics') for row in failed['report']['criteria'])
    corrected=act(dict(action='patch',path=entry.TEST,
        old="expected_args = ('value', 'other', raw, reference)",
        new="expected_args = ('value', 'main', raw, reference)",
        expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(entry.TEST)),
        'The actual failure shows the requesting section differs from the authored expectation; current refreshed test and acquired constructor/raise path support correcting that tuple.')
    assert corrected['operations'][-1]['result']['passed']
    checked_test=next(s for s in session.view()['working_set']['sources']
        if s['path']==entry.TEST and 'class MissingInterpolationTransportTests' in s['content'])
    retained=dict(path=entry.TEST,start_line=checked_test['returned_start_line'],end_line=checked_test['returned_end_line'])
    first=1
    while True:
        result=act(dict(action='work_on',sources=[retained,dict(path=entry.DOC,start_line=first,end_line=0)],results=[]),
            'Tests have passed. Keep the actual checked new test with the document so example behavior is supported in this input; subsequent document pages follow only returned coordinates.')
        doc_source=next(s for s in result['operations'][0]['result']['sources'] if s['path']==entry.DOC)
        test_source=next(s for s in result['operations'][0]['result']['sources'] if s['path']==entry.TEST)
        assert 'class MissingInterpolationTransportTests' in test_source['content'] and "'supplied'" in test_source['content']
        if doc_source['next_start_line'] is None: break
        first=doc_source['next_start_line']
    anchor=''.join(doc_source['content'].splitlines(keepends=True)[-5:])
    assert anchor and session.candidate.file_map[entry.DOC].decode().count(anchor)==1
    doc=act(dict(action='patch',path=entry.DOC,old=anchor,new=anchor+'\n\n'+reference.doc_addition(),
        expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(entry.DOC)),
        'The source-derived lookup behavior has an actual passing test observation. Preserve the current document and append runnable examples covering the same missing/raw/resolved distinction.')
    assert doc['operations'][-1]['action']['action']=='check' and doc['operations'][-1]['result']['passed']
    act(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
        'The public check has actually passed on the current successor and the prior library/work is preserved. Submit that unchanged candidate.')
    assert session.submitted
    assert all(session.candidate.file_map[p]==raw for p,raw in module.inherited_candidate.file_map.items() if p not in (entry.TEST,entry.DOC))
    return dict(decisions=len(trace),trace=trace,submitted=True,failed_then_corrected=True,
        candidate_id=session.candidate.candidate_id,
        assistance='researcher-selected engineering sequence; negative expectation explicitly injected only offline; not actor capability')
