"""Evaluator-only correction of the exact saved URL-port failed contribution.

This route never supplies an actor entry, model call or reviewer correction.
Only root-owned preparation may execute it. Each operation is justified by the
actual prior input, and new checks execute on independent scripted successors.
"""
import ast
import copy
import importlib.util
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

TARGET = 'Lib/urllib/parse.py'
TEST = 'Lib/test/test_urlparse.py'
DOC = 'Doc/library/urllib.parse.rst'
INITIAL_ID = '83d8704c0a98ca6b201c991c56951d2e95bc060af33523531aa0b7789bf304ef'
ORIGINAL_ID = '2921cbc8a115c86871a11f8eaea929c3d48a8e4d2bb2ca03bf48971c36cf15cd'
METHOD = '    def test_port_boundary_and_errors(self):\n'
DOC_ANCHOR = 'Structured Parse Results\n------------------------\n'
CLASSIFICATION = 'evaluator-authored engineering continuation; no model inference'


def _fixture():
    """Reuse the published evaluator fixture, never an old model draft."""
    path = Path(__file__).resolve().parent.parent / 'url_port_entry/qualification_route.py'
    spec = importlib.util.spec_from_file_location('url_continuation_documentation_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shown_method(view):
    sources = [source for source in view['working_set']['sources']
        if source['path'] == TEST and METHOD in source['content']]
    if len(sources) != 1:
        raise ValueError('exact current contribution method is not uniquely displayed')
    content = sources[0]['content']
    start = content.index(METHOD)
    end = content.find('\n    def ', start + len(METHOD))
    if end < 0:
        raise ValueError('displayed source does not establish the complete method boundary')
    return content[start:end + 1]


def _correction(view):
    """Strengthen the displayed assertions, preserving Qwen's saved test."""
    latest = view['latest_feedback']
    if (latest['sequence'] != 30 or latest['result']['observation'] != 'CHK-0030'
            or latest['result']['checked_candidate_id'] != INITIAL_ID
            or latest['result']['passed'] is not False):
        raise ValueError('starting input does not contain the actual saved failed check')
    criteria = latest['result']['report']['criteria']
    if (len(criteria) != 1 or criteria[0]['criterion'] != 'detect.error_class'
            or criteria[0]['met'] is not False or criteria[0]['fault_detected'] is not False
            or criteria[0]['injected_change'] != 'Replace the real ValueError with a subclass of ValueError.'):
        raise ValueError('actual starting failure differs from the qualified correction')
    old = _shown_method(view)
    lines = old.splitlines(keepends=True)
    new, assertions = [], 0
    for number, line in enumerate(lines):
        new.append(line)
        if (number > 0 and 'self.assertEqual(ctx.exception.args,' in lines[number - 1]
                and line.strip().endswith(',))')):
            # The task requires the exact class, argument tuple and diagnostic
            # string. The existing tuple remains unchanged; the actual failed
            # sensitivity criterion independently establishes why subclasses
            # must not be accepted. No mutation-path requirements are invented.
            indent = lines[number - 1][:len(lines[number - 1]) - len(lines[number - 1].lstrip())]
            new.append(indent + 'self.assertIs(type(ctx.exception), ValueError)\n')
            new.append(indent + 'self.assertEqual(str(ctx.exception), ctx.exception.args[0])\n')
            assertions += 1
    if assertions != 7:
        raise ValueError('displayed saved contribution no longer has its seven exact argument assertions')
    replacement = ''.join(new)
    ast.parse('class VisibleContribution:\n' + replacement)
    return old, replacement


def _require_authority_shown(session):
    """The fixture cannot consume unseen implementation premises."""
    shown = [source for source in session.view()['working_set']['sources'] if source['path'] == TARGET]
    prefixes = [source for source in shown if source['returned_start_line'] == 1
        and source['returned_end_line'] == 508 and source['returned_extent_complete']]
    if len(prefixes) != 1:
        raise ValueError('complete governing implementation prefix is not uniquely displayed')
    content = prefixes[0]['content']
    exact = ''.join(session.candidate.file_map[TARGET].decode('utf-8').splitlines(keepends=True)[:508])
    if content != exact:
        raise ValueError('displayed implementation prefix differs from current exact bytes')
    tree = ast.parse(content)
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not {'_NetlocResultMixinBase', '_NetlocResultMixinStr', '_NetlocResultMixinBytes'} <= classes.keys():
        raise ValueError('displayed prefix lacks complete port-owner/result definitions')
    if not {'urlparse', 'urlsplit', '_coerce_args', '_decode_args', '_encode_result', '_checknetloc'} <= functions.keys():
        raise ValueError('displayed prefix lacks complete constructors/coercion definitions')
    if not any(isinstance(node, ast.FunctionDef) and node.name == 'port'
            for node in classes['_NetlocResultMixinBase'].body):
        raise ValueError('displayed port owner lacks its actual property')
    for name in ('_NetlocResultMixinStr', '_NetlocResultMixinBytes'):
        if not any(isinstance(node, ast.FunctionDef) and node.name == '_hostinfo'
                for node in classes[name].body):
            raise ValueError('displayed result type lacks its actual host/port splitting')
    return content


def qualify_contribution(module, session, measure, preceding, record=None, request_for=None):
    """Use CHK-0030, preserve its work, check correction, then finish docs."""
    rows = []
    initial = session.candidate
    inherited_pairs = copy.deepcopy(session.pairs)
    inherited_account = copy.deepcopy(session.working_account())
    assert initial.candidate_id == INITIAL_ID
    assert session.requests_used == 20 and session.calls_used == 30
    assert session.request_limit == 36 and session.call_limit == 60
    initial_view = copy.deepcopy(session.view())
    old, new = _correction(initial_view)
    assert initial.file_map[TEST].decode('utf-8').count(old) == 1

    def act(action, basis, *, accepted=True, account=None):
        before = copy.deepcopy(session.view())
        before_receipts = copy.deepcopy(preceding)
        before_request = copy.deepcopy(request_for(before)) if request_for else None
        count = measure(before)
        assert count <= 23808 and not session.delivery_blocked
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis, operation=action)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, measure, preceding)
        requested = outcome['operations'][0 if account is None else 1]['result']
        assert requested.get('accepted') is accepted, requested
        assert session.pairs[:30] == inherited_pairs
        after = copy.deepcopy(session.view())
        following = measure(after)
        assert following <= 23808 and not session.delivery_blocked
        assert all(session.candidate.file_map[path] == initial.file_map[path]
            for path in initial.file_map if path not in (TEST, DOC))
        row = dict(before_view=before, preceding_before=before_receipts,
            before_request=before_request, reply=reply, outcome=copy.deepcopy(outcome),
            after_view=after, preceding_after=copy.deepcopy(preceding),
            input_tokens=count, next_input_tokens=following,
            information_path_justification=basis, classification=CLASSIFICATION)
        rows.append(row)
        if record:
            record(row, session)
        return requested, outcome

    def patch(path, previous, replacement):
        return dict(action='patch', path=path, old=previous, new=replacement,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(path))

    stale = patch(TEST, old, new)
    stale['expected_candidate_id'] = ORIGINAL_ID
    stale['expected_file_sha256'] = session.versions[ORIGINAL_ID].file_sha256(TEST)
    _, rejected = act(stale,
        'The input names the saved successor, while archived edit EVT-0029 names the original predecessor. Deliberately use that predecessor guard to qualify truthful rejection without editing or checking.',
        accepted=False)
    assert len(rejected['operations']) == 1 and session.candidate is initial
    assert session.working_account() == inherited_account
    _, corrected = act(patch(TEST, old, new),
        'Actual CHK-0030 reports that a ValueError subclass escaped the new test. The visible test uses subclass-permitting assertRaises and already checks exact argument tuples. Add exact-type and diagnostic-string assertions while preserving those tuples and all saved normal cases.',
        account='The actual tests observation failed detect.error_class: the injected subclass was not detected. Strengthen the saved test; its new successor must receive the declared tests check. Documentation is still unchanged.')
    check = corrected['operations'][-1]['result']
    assert len(corrected['operations']) == 3
    assert check['executed'] and check['capture_complete'] and check['passed']
    assert check['check_id'] == 'tests' and check['checked_candidate_id'] == session.candidate.candidate_id
    assert not session.verification_view()['submission']['eligible']
    corrected_candidate = session.candidate
    assert corrected_candidate.file_map[TEST] == initial.file_map[TEST].decode('utf-8').replace(old, new).encode('utf-8')
    assert corrected_candidate.file_map[DOC] == initial.file_map[DOC]

    implementation, _ = act(dict(action='read', path=TARGET, start_line=350, end_line=508),
        'The visible port property and result classes govern values and diagnostics. The task names urlparse and urlsplit; extend the displayed implementation through their actual constructor definitions before authoring construction-versus-access examples.')
    assert implementation['source']['returned_extent_complete']
    assert implementation['source']['returned_start_line'] == 350
    assert implementation['source']['returned_end_line'] == 508
    located, _ = act(dict(action='search', path=DOC, query='Structured Parse Results', offset=0, limit=16),
        'The original documentation is named in the task and has not changed. Locate its real section heading to append a self-contained explanation while preserving existing prose; this placement is an evaluator choice.')
    assert len(located['matches']) == 1
    doc_ref = next(region['region_ref'] for region in located['regions']
        if region.get('extent_kind') != 'enclosing Python function')
    implementation_ref = next(source['region_ref'] for source in session.view()['working_set']['sources']
        if source['path'] == TARGET and source['returned_start_line'] == 1
        and source['returned_end_line'] >= 507)
    act(dict(action='work_on_exact', regions=[implementation_ref, doc_ref], results=[]),
        'The actual read and search returned reusable exact regions. Select the complete governing implementation and unique documentation heading together for the next contribution; this is evaluator-selected engineering evidence, not a supplied actor group.',
        account='The corrected test received an actual passing tests check on its saved successor. That scope does not validate documentation. Inspect the complete governing implementation and actual documentation anchor before writing the remaining contribution.')
    assert not session.recovery
    authority = _require_authority_shown(session)
    docs = _fixture().derive_documentation(authority)
    assert any(source['path'] == DOC and DOC_ANCHOR in source['content']
        for source in session.view()['working_set']['sources'])
    assert session.candidate.file_map[DOC].decode('utf-8').count(DOC_ANCHOR) == 1
    _, completed = act(patch(DOC, DOC_ANCHOR, docs + DOC_ANCHOR),
        'The displayed property establishes absent/empty ports, ASCII decimal boundaries and exact invalid-value messages; the displayed constructors establish lazy port access. Append the published evaluator-selected self-contained examples from that authority, retaining all original documentation.')
    public = completed['operations'][-1]['result']
    assert public['executed'] and public['capture_complete'] and public['passed']
    assert public['check_id'] == 'public' and public['checked_candidate_id'] == session.candidate.candidate_id
    assert session.verification_view()['submission']['eligible']
    assert session.candidate.file_map[TEST] == corrected_candidate.file_map[TEST]
    assert session.candidate.file_map[DOC] == initial.file_map[DOC].decode('utf-8').replace(DOC_ANCHOR, docs + DOC_ANCHOR).encode('utf-8')
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual complete public check passes on this current candidate. Submit the preserved corrected tests and newly checked documentation.',
        account='The saved test was corrected using actual failed feedback. The resulting tests and documentation received an actual public pass on the current candidate; submit. This account is authored interpretation, not check authority.')
    assert session.submitted and session.requests_used <= 36 and session.calls_used <= 60
    return rows


def _qualify(module, loop, adapter, store, folder):
    """Root-owned native preparation only; the prospective entry is separate."""
    label = 'contribution'
    branch = Path(folder) / 'scripted' / label
    session = module.initial_session()
    module.attach_observations(session, branch, loop.log)
    preceding = module.initial_preceding_feedback()
    adapter.preceding_feedback[:] = copy.deepcopy(preceding)
    initial_state = canonical_json_bytes(module.snapshot(session))
    initial_view = copy.deepcopy(session.view())
    initial_candidate = module.candidate_bytes(session.candidate)
    initial_account = copy.deepcopy(session.working_account())
    store.put('scripted/contribution/inherited-state.json', initial_state)
    store.put('scripted/contribution/inherited-candidate.json', initial_candidate)
    store.put('scripted/contribution/inherited-account.json', canonical_json_bytes(initial_account))
    store.put('scripted/contribution/inherited-preceding-feedback.json', canonical_json_bytes(preceding))
    store.put('scripted/contribution/INFORMATION_PATH.md', (
        '# Scripted continuation boundary\n\n'
        'This is evaluator-authored engineering qualification on an independent clone. '
        'The prospective actor entry is not changed. The sole initial failure is the actual preserved '
        'CHK-0030; it is not rerun. The existing public test, account and earlier archive are preserved '
        'separately. Every following decision records its exact prior view and presented receipts.\n\n'
        'Correction follows the actual subclass sensitivity failure and the task-required exact '
        'class/arguments/diagnostic contract. Documentation is a separate evaluator-selected fixture, '
        'revalidated from displayed property/result classes and constructors after real source acquisition. '
        'No private draft, checker expected answer or reference answer is supplied to the actor. '
        'Scripted feasibility is not autonomous selection or model feedback-use evidence.\n'
    ).encode('utf-8'))
    trials = []

    def record(row, current):
        stem = f'scripted/{label}/steps/{len(trials) + 1:02d}'
        state_bytes = canonical_json_bytes(module.snapshot(current))
        candidate_bytes = module.candidate_bytes(current.candidate)
        store.put(stem + '.json', canonical_json_bytes(row))
        store.put(stem + '-state.json', state_bytes)
        store.put(stem + '-candidate.json', candidate_bytes)
        restored = module.restore(load_json_strict(state_bytes), current.candidate, branch, replay=True)
        assert canonical_json_bytes(module.snapshot(restored)) == state_bytes
        assert restored.view() == current.view()
        assert module.candidate_bytes(restored.candidate) == candidate_bytes
        assert restored.working_account() == current.working_account()
        assert restored.pairs == current.pairs
        for sequence in range(1, len(current.pairs) + 1):
            for kind in ('EVT', 'RES'):
                handle = f'{kind}-{sequence:04d}'
                assert restored.payload(handle) == current.payload(handle)
        checks = [operation['result'] for operation in row['outcome']['operations']
            if operation['result'].get('executed')]
        for check in checks:
            observed = current.observations.read(check['observation'])
            assert observed['capture_complete'] and observed['candidate_id'] == check['checked_candidate_id']
            assert observed['streams'] == check['streams']
            for stream in ('stdout', 'stderr'):
                raw = (current.observations.directory(check['observation']) / (stream + '.bin')).read_bytes()
                assert len(raw) == observed['streams'][stream]['captured_bytes']
                assert sha256_bytes(raw) == observed['streams'][stream]['sha256']
        trials.append(dict(branch=label, input_tokens=row['input_tokens'],
            next_input_tokens=row['next_input_tokens'], action=row['reply']['operation']['action'],
            accepted=row['outcome']['operations'][0 if 'account' not in row['reply'] else 1]['result']['accepted'],
            archived_operations=len(current.pairs), requests_used=current.requests_used,
            actual_checks=[dict(observation=check['observation'], scope=check['check_id'],
                candidate_id=check['checked_candidate_id'], passed=check['passed'],
                capture_complete=check['capture_complete']) for check in checks],
            snapshot_sha256=sha256_bytes(state_bytes), candidate_sha256=sha256_bytes(candidate_bytes),
            information_path_justification=row['information_path_justification']))

    # Qualify the initial exact restored checkpoint as well as later mixed-digit
    # edit/check/account addresses. ObservationStore restoration is replay-only.
    restored = module.restore(load_json_strict(initial_state), session.candidate, branch, replay=True)
    assert canonical_json_bytes(module.snapshot(restored)) == initial_state
    assert restored.view() == initial_view
    assert module.candidate_bytes(restored.candidate) == initial_candidate
    qualify_contribution(module, session, loop.measure, adapter.preceding_feedback, record,
        request_for=adapter.request_for)
    checks_executed = sum(len(row['actual_checks']) for row in trials)
    assert checks_executed == 2
    return dict(trials=trials, classification=CLASSIFICATION, completion_requests=0,
        submitted=session.submitted, checks_executed=checks_executed,
        new_scripted_checks=checks_executed, requests_used=session.requests_used,
        operations_used=session.calls_used,
        checks=dict(actual_initial_failure_reused_without_execution=True,
            stale_original_guard_rejected=True, saved_test_preserved_and_corrected=True,
            documentation_acquired_before_authoring=True, actual_successor_tests_public_pass=True,
            exact_checkpoint_restore=True, original_archive_prefix_preserved=True,
            evaluator_choices_not_prospective_entry=True, checked_submission=True))


def qualify(module, loop, adapter, store, folder):
    """Preserve the prospective entry's receipt presentation even on failure."""
    entry_receipts = copy.deepcopy(adapter.preceding_feedback)
    try:
        return _qualify(module, loop, adapter, store, folder)
    finally:
        adapter.preceding_feedback[:] = entry_receipts
