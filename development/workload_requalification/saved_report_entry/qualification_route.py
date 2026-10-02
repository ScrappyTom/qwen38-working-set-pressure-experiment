"""Evaluator-only phase information paths; reference work never enters live inputs."""
import ast
import copy

from manage import load_helper
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

capture_reader = load_helper('saved_report_capture_reader',
    'development/workload_requalification/compiler_entry/qualification_route.py')


def derive_entry(view, handle):
    """Derive only the requested emitted entry from actually displayed operands."""
    bodies = capture_reader.delivered_capture_bodies(view)
    if handle not in ('OBS-0002','OBS-0003') or not {'OBS-0001',handle} <= set(bodies):
        raise ValueError('Requested comparison operands are not displayed')
    original = capture_reader.decode_tree(load_json_strict(bodies['OBS-0001'])['ast_dump'])
    emitted = capture_reader.decode_tree(load_json_strict(bodies[handle])['ast_dump'])
    functions = [node for node in original.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))]
    successors = {node.name:node for node in emitted.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
    changed = [node for node in functions if ast.dump(node) != ast.dump(successors[node.name])]
    first = None
    for node in changed:
        difference = capture_reader.first_changed_expression(node,successors[node.name])
        if difference:
            first = dict(function=node.name,**difference)
            break
    if first is None:
        raise ValueError('No changed expression in delivered capture')
    return dict(capture=handle,changed_functions=[node.name for node in changed],first_change=first)


def setup_support(session, phase):
    view = session.view()
    sources = capture_reader.delivered_sources(view)
    for path in ('README.md','reports/incident.json'):
        assert sources[path]['content'].encode() == session.candidate.file_map[path]
        assert sources[path]['candidate_id'] == session.candidate.candidate_id
    expected = {'OBS-0001', 'OBS-0002' if phase == 1 else 'OBS-0003'}
    assert set(capture_reader.delivered_capture_bodies(view)) == expected
    assert all(n==1 for n in capture_reader.displayed_capture_counts(view).values())
    if phase == 2:
        sequence = session.phase_start_archive_length
        receipt = session.pairs[sequence-1]['result']
        saved = view['working_set']['saved_results']
        page = next(row for row in saved if row.get('handle') == f'RES-{sequence:04d}')
        assert page['offset'] == 0 and page['next_offset'] is None
        assert page['exact_utf8'].encode() == canonical_json_bytes(receipt)
    return dict(phase=phase, current_candidate=session.candidate.candidate_id,
        complete_sources=sorted(sources), complete_captures=sorted(expected),
        phase_counters=session.phase_counters(), check_delivered=phase==2)


def qualify(module, loop, adapter, store, folder):
    routes = []
    for name, malformed in (('valid_partial',False), ('malformed_then_corrected',True)):
        prefix = f'scripted/{name}'
        session = module.initial_session()
        module.attach_observations(session, folder/prefix, loop.log)
        adapter.preceding_feedback.clear()
        rows = []

        def record_setup(sequence, action, result):
            store.put(f'{prefix}/setup/O{sequence:03d}.json', canonical_json_bytes(dict(
                sequence=sequence, action=action, result=result, model_action=False)))

        module.setup(session, 1, loop.measure, adapter.preceding_feedback, record_setup)
        support1 = setup_support(session,1)
        assert session.requests_used == session.actor_operations_used() == 0

        def act(action, basis, account=None, accepted=True):
            before = copy.deepcopy(session.view())
            count = loop.measure(before)
            assert count <= 23808 and session.phase_budget_available()
            session.mark_delivered(before)
            session.begin_request()
            reply = dict(discussion=basis,operation=action)
            if account is not None:
                reply['account'] = account
            host = module.process_reply(session,reply,loop.measure,adapter.preceding_feedback)
            result = host['operations'][-1]['result']
            assert result.get('accepted') is accepted, result
            after = session.view()
            following = loop.measure(after)
            assert following <= 23808 and not session.delivery_blocked
            row = dict(before_view=before, reply=reply, outcome=host,
                after_view=copy.deepcopy(after), input_tokens=count, next_input_tokens=following,
                basis=basis, classification='researcher-selected engineering qualification')
            rows.append(row)
            store.put(f'{prefix}/steps/{len(rows):02d}.json',canonical_json_bytes(row))
            store.put(f'{prefix}/states/{len(rows):02d}.json',canonical_json_bytes(module.snapshot(session)))
            return result

        first = derive_entry(session.view(),'OBS-0002')
        partial = canonical_json_bytes(dict(builds=[first])).decode()
        proposed = (partial[:-1] if malformed else partial)+'\n'
        act(dict(action='patch',path='reports/incident.json',
            old=session.candidate.file_map['reports/incident.json'].decode(),new=proposed,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256('reports/incident.json')),
            'The displayed report guard and original/BUILD-A trees support this first entry; BUILD-B remains for phase2.',
            account='Compared displayed original and BUILD-A trees. First report contribution is saved next; no execution yet.')
        first_candidate = session.candidate
        failed = act(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
            'The actual accepted report edit supplies this successor; original phase rule requests its public check.')
        assert failed['executed'] is True and failed['passed'] is False and session.transition_ready()
        boundary = module.snapshot(session)
        store.put(f'{prefix}/transition-state.json',canonical_json_bytes(boundary))
        store.put(f'{prefix}/transition-candidate.json',module.candidate_bytes(session.candidate))
        old_account = session.working_account()
        module.setup(session,2,loop.measure,adapter.preceding_feedback,record_setup)
        assert session.candidate is first_candidate and session.working_account() == old_account
        support2 = setup_support(session,2)
        assert session.phase_counters()['phase_requests_used'] == 0
        # The public report offers exact raw observation access. Obtain it before
        # attributing a malformed correction to the missing diagnostic.
        diagnostic = act(dict(action='inspect_observation',observation=failed['observation'],stream='stdout',offset=0),
            'The executed failed check supplies this exact CHK address; inspect actual stdout without rerunning it.')
        assert diagnostic.get('accepted') is True
        diagnostic_bytes = session.observations.directory(failed['observation']).joinpath('stdout.bin').read_bytes()
        assert diagnostic_bytes and diagnostic['content'].encode() == diagnostic_bytes
        assert diagnostic['offset'] == 0 and diagnostic['next_offset'] is None
        act(dict(action='reopen_observation',handle='OBS-0002'),
            'Restart inventory identifies BUILD-A as absent. Acquire its preserved body before independently validating the saved first entry.')
        assert set(capture_reader.delivered_capture_bodies(session.view())) == {'OBS-0001','OBS-0002','OBS-0003'}
        # Derive both entries anew only after all actual operands have arrived.
        report = dict(builds=[derive_entry(session.view(),handle) for handle in ('OBS-0002','OBS-0003')])
        if malformed:
            assert b'JSONDecodeError' in diagnostic_bytes
        else:
            assert b'cover each emitted capture' in diagnostic_bytes
        stale = act(dict(action='patch',path='reports/incident.json',old=proposed,
            new=canonical_json_bytes(report).decode()+'\n',
            expected_candidate_id=module.compiler.STARTING_ID,
            expected_file_sha256=session.candidate.file_sha256('reports/incident.json')),
            'Engineering stale-guard regression: reject a historical candidate guard without altering the saved contribution.',accepted=False)
        assert session.candidate is first_candidate and session.phase_counters()['phase'] == 2
        act(dict(action='patch',path='reports/incident.json',old=session.candidate.file_map['reports/incident.json'].decode(),
            new=canonical_json_bytes(report).decode()+'\n',expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256('reports/incident.json')),
            'The delivered saved report/current guards, actual failed observation and all three acquired trees support correction and extension.',
            account='The actual check failed; reviewed its preserved diagnostic. The next edit includes both delivered build comparisons; final execution remains pending.')
        passed = act(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),
            'The accepted corrected report receipt identifies the actual current candidate to execute.')
        assert passed['executed'] is True and passed['passed'] is True
        act(dict(action='submit',expected_candidate_id=session.candidate.candidate_id),
            'The actual applicable public pass concerns this unchanged candidate and permits submission.')
        assert session.submitted and session.requests_used == 8
        initial = module.initial_session().candidate
        assert all(session.candidate.file_map[path] == data for path,data in initial.file_map.items()
                   if path != 'reports/incident.json')
        state = module.snapshot(session)
        restored = module.restore(state,session.candidate,folder/prefix,replay=True)
        assert canonical_json_bytes(module.snapshot(restored)) == canonical_json_bytes(state)
        summary = dict(name=name, completed=True, malformed_saved_artifact=malformed,
            initial_support=support1,restart_support=support2,scripted_decision_slots=session.requests_used,
            actual_operations=session.calls_used, archival_operations=len(session.pairs),
            phase_counters=session.phase_counters(), final_candidate=session.candidate.candidate_id,
            peak_input_tokens=max(max(row['input_tokens'],row['next_input_tokens']) for row in rows),
            checks_executed=2, source_preservation=True, checkpoint_roundtrip=True,
            scripted_decisions=len(rows),model_completion_requests=0)
        store.put(f'{prefix}/RESULTS.json',canonical_json_bytes(summary))
        routes.append(summary)
    assert loop.sent == 0
    return routes
