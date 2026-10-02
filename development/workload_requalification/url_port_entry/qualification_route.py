"""Evaluator-only URL information paths; never actor entry or reference answers.

Expected behavior is derived from displayed current implementation. Scripted
selection and deliberate wrong expectations are engineering qualification, not
model investigation evidence.
"""
import ast
import copy

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.observations import ObservationStore

TARGET = 'Lib/urllib/parse.py'
TEST = 'Lib/test/test_urlparse.py'
DOC = 'Doc/library/urllib.parse.rst'
TEST_ANCHOR = 'if __name__ == "__main__":\n'
DOC_ANCHOR = 'Structured Parse Results\n------------------------\n'
RANGE_MESSAGE = 'Port out of range 0-65535'


def derive_tests(implementation, *, apis=('urlsplit', 'urlparse'), binary=True,
                 unicode_digits=True, omitted=(), weak=None, wrong_message=False):
    """Require the real property/hostinfo rules before authoring expectations.

    No old actor artifact, checker expected answer or donor reference is read.
    The optional variants are deliberate evaluator faults for acceptance tests.
    """
    tree = ast.parse(implementation)
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    owner = classes.get('_NetlocResultMixinBase')
    if owner is None:
        raise ValueError('displayed implementation lacks the port owner')
    port = next((n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == 'port'), None)
    if port is None:
        raise ValueError('displayed implementation lacks the port property')
    text = ast.get_source_segment(implementation, port)
    required = ('port.isdigit() and port.isascii()', 'port = int(port)',
                '0 <= port <= 65535', 'Port could not be cast to integer value as', RANGE_MESSAGE)
    if not all(item in text for item in required):
        raise ValueError('port rules differ; evaluator expectations need review')
    for name in ('_NetlocResultMixinStr', '_NetlocResultMixinBytes'):
        node = classes.get(name)
        if node is None or 'if not port:' not in ast.get_source_segment(implementation, node):
            raise ValueError('displayed implementation lacks empty-port normalization')
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    if not {'urlsplit', 'urlparse'} <= functions.keys():
        raise ValueError('displayed implementation lacks both public constructors')
    if any('.port' in ast.get_source_segment(implementation, functions[name]) for name in apis):
        raise ValueError('constructor timing changed; expectations need review')
    values = [('', None, 'absent'), (':', None, 'empty'), (':0', 0, 'zero'), (':65535', 65535, 'maximum')]
    values = [(suffix, expected, category) for suffix, expected, category in values if category not in omitted]
    invalid = [('65536', RANGE_MESSAGE, 'too_high'), ('-1', None, 'negative'), ('foo', None, 'noninteger')]
    invalid = [row for row in invalid if row[2] not in omitted]
    if unicode_digits and 'unicode_digits' not in omitted:
        invalid.append(('\u0666', None, 'unicode_digits'))
    api_text = '(' + ', '.join('urllib.parse.' + name for name in apis) + ',)'
    binary_text = '(False, True)' if binary else '(False,)'
    class_assert = '' if weak == 'class' else '                        self.assertIs(type(error), ValueError)\n'
    args_assert = ('                        self.assertTrue(error.args)\n' if weak in ('arguments', 'message') else
                   '                        self.assertEqual(error.args, (message,))\n')
    str_assert = '' if weak in ('arguments', 'message') else '                        self.assertEqual(str(error), message)\n'
    message_line = "                        message = expected or ('Port could not be cast to integer value as ' + repr(raw))\n"
    if wrong_message:
        message_line += "                        if category == 'too_high':\n                            message = 'Port out of range 0-65534'\n"
    construction = ('                        with self.assertRaises(ValueError) as caught:\n'
                    '                            result = parse(url)\n                            result.port\n' if weak == 'timing' else
                    '                        result = parse(url)\n                        with self.assertRaises(ValueError) as caught:\n                            result.port\n')
    return ('\n\nclass PortBoundaryContributionTests(unittest.TestCase):\n'
        '    def test_port_boundaries_both_apis_and_input_types(self):\n'
        f'        for parse in {api_text}:\n'
        f'            for binary in {binary_text}:\n'
        f'                for suffix, expected, category in {values!r}:\n'
        '                    with self.subTest(api=parse.__name__, binary=binary, category=category):\n'
        "                        url = 'http://example.test' + suffix + '/'\n"
        "                        if binary:\n                            url = url.encode('ascii')\n"
        '                        result = parse(url)\n                        actual = result.port\n'
        + (f"                        if category != {weak[5:]!r}:\n                            self.assertEqual(actual, expected)\n" if weak and weak.startswith('skip_') else
           '                        self.assertEqual(actual, expected)\n                        self.assertIs(type(actual), type(expected))\n') +
        '\n    def test_port_errors_exact_state_and_lazy_timing(self):\n'
        f'        for parse in {api_text}:\n'
        f'            for binary in {binary_text}:\n'
        f'                for raw, expected, category in {invalid!r}:\n'
        "                    if binary and category == 'unicode_digits':\n                        continue\n"
        '                    with self.subTest(api=parse.__name__, binary=binary, category=category):\n'
        "                        url = 'http://example.test:' + raw + '/'\n"
        "                        if binary:\n                            url = url.encode('ascii')\n                            raw = raw.encode('ascii')\n"
        + message_line + construction + '                        error = caught.exception\n' +
        class_assert + args_assert + str_assert + '\n')


def derive_documentation(implementation):
    derive_tests(implementation)  # Revalidate the authority used by this prose.
    return '''Port access and validation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The parsing functions create a result before validating its port. Accessing
``port`` returns ``None`` for an absent or empty port and an integer from 0
through 65535 for an ASCII decimal port. An invalid spelling or an out-of-range
value raises :exc:`ValueError` when the property is accessed. This applies to
both parsing functions and their text and ASCII bytes result types. Non-ASCII
decimal digits are not accepted as a text port.

The examples include their imports and distinguish construction from access::

   >>> from urllib.parse import urlsplit, urlparse
   >>> [parse('http://example.test/').port for parse in (urlsplit, urlparse)]
   [None, None]
   >>> [parse(b'http://example.test:/').port for parse in (urlsplit, urlparse)]
   [None, None]
   >>> [urlsplit('http://example.test:0/').port, urlparse(b'http://example.test:65535/').port]
   [0, 65535]
   >>> result = urlsplit('http://example.test:65536/')
   >>> result.port
   Traceback (most recent call last):
   ...
   ValueError: Port out of range 0-65535
   >>> result = urlparse(b'http://example.test:-1/')
   >>> result.port
   Traceback (most recent call last):
   ...
   ValueError: Port could not be cast to integer value as b'-1'
   >>> result = urlparse('http://example.test:foo/')
   >>> result.port
   Traceback (most recent call last):
   ...
   ValueError: Port could not be cast to integer value as 'foo'
   >>> result = urlsplit('http://example.test:\u0666/')
   >>> result.port
   Traceback (most recent call last):
   ...
   ValueError: Port could not be cast to integer value as '\u0666'

'''


def proposed_candidate(module, **variant):
    files = module.checkers.starting_files()
    implementation = files[TARGET].decode()
    tests = derive_tests(implementation, **variant)
    docs = derive_documentation(implementation)
    assert files[TEST].decode().count(TEST_ANCHOR) == files[DOC].decode().count(DOC_ANCHOR) == 1
    files[TEST] = files[TEST].decode().replace(TEST_ANCHOR, tests + TEST_ANCHOR).encode()
    files[DOC] = files[DOC].decode().replace(DOC_ANCHOR, docs + DOC_ANCHOR).encode()
    return Candidate.create(files, max_file_bytes=module.FILE_LIMIT)


def execute_checker(candidate, checker, scope, folder):
    store = ObservationStore(folder)
    record = store.execute(candidate, checker, scope, 'CHK-0001')
    assert record['executed'] and record['capture_complete'], record
    report = load_json_strict((store.directory('CHK-0001') / 'stdout.bin').read_bytes())
    assert report['passed'] == record['passed']
    return record, report, store


def run_equivalence(module, folder):
    """Small contract matrix, with every original/adapted full stream preserved."""
    base = module.starting_candidate()
    good = proposed_candidate(module)
    variants = [('original', base, 'public', False), ('correct', good, 'public', True)]
    for name, options in (
        ('wrong_expected_message', dict(wrong_message=True)),
        ('missing_api', dict(apis=('urlsplit',))),
        ('missing_bytes', dict(binary=False)),
        ('missing_unicode', dict(unicode_digits=False)),
        ('missing_category', dict(omitted=('negative',))),
        ('weak_exact_class', dict(weak='class')),
        ('weak_full_arguments', dict(weak='arguments')),
        ('weak_message', dict(weak='message')),
        ('eager_timing_not_detected', dict(weak='timing')),
        ('empty_boundary_not_detected', dict(weak='skip_empty')),
        ('zero_boundary_not_detected', dict(weak='skip_zero')),
        ('maximum_boundary_not_detected', dict(weak='skip_maximum'))):
        variants.append((name, proposed_candidate(module, **options), 'tests', False))
    files = good.file_map
    files[DOC] = files[DOC].decode().replace('   [0, 65535]\n', '   [0, 65534]\n').encode()
    variants.append(('wrong_example_output', Candidate.create(files, max_file_bytes=module.FILE_LIMIT), 'examples', False))
    files = good.file_map
    files[TARGET] += b'\n# forbidden library change\n'
    variants.append(('library_preservation', Candidate.create(files, max_file_bytes=module.FILE_LIMIT), 'public', False))
    rows = []
    for name, candidate, scope, expected in variants:
        results = []
        for format_name, definition in (('original', module.checkers.original_checker(scope)),
                                         ('preserved', module.checkers.checker(scope))):
            record, report, _ = execute_checker(candidate, definition, scope, folder / name / format_name)
            assert report['passed'] is expected, (name, format_name, report)
            results.append(report)
            rows.append(dict(case=name, capture=format_name, candidate_id=candidate.candidate_id,
                scope=scope, passed=record['passed'], checker_sha256=record['checker_sha256'],
                observation=record, stdout_sha256=record['streams']['stdout']['sha256']))
        for key in ('passed', 'tests_passed', 'existing_work_preserved', 'documentation_preserved'):
            assert results[0].get(key) == results[1].get(key), (name, key)
        if scope != 'examples':
            assert {name: result['successful'] for name, result in results[0]['fault_sensitivity'].items()} == {
                name: result['successful'] for name, result in results[1]['fault_sensitivity'].items()}
    return rows


def qualify_contribution(module, session, measure, preceding, record=None):
    rows = []

    def act(action, basis, *, accepted=True, account=None):
        before = copy.deepcopy(session.view())
        count = measure(before)
        assert count <= 23808
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis, operation=action)
        if account is not None:
            reply['account'] = account
        outcome = module.process_reply(session, reply, measure, preceding)
        result = outcome['operations'][0 if account is None else 1]['result']
        assert result.get('accepted') is accepted, result
        after = copy.deepcopy(session.view())
        following = measure(after)
        assert following <= 23808 and not session.delivery_blocked
        row = dict(before_view=before, reply=reply, outcome=copy.deepcopy(outcome), after_view=after,
            input_tokens=count, next_input_tokens=following,
            classification='researcher-selected engineering information-path qualification')
        rows.append(row)
        if record:
            record(row, session)
        return result, outcome

    regions = []
    owners, _ = act(dict(action='search', path=TARGET, query='class _Netloc', offset=0, limit=16),
        'Locate the actual owner classes so the delivered property and hostinfo methods are connected to their text and bytes result types.')
    assert len(owners['matches']) == 3
    regions.extend(r['region_ref'] for r in owners['regions'])
    for query, path, names in (('def port', TARGET, {'port'}), ('def _hostinfo', TARGET, {'_hostinfo'}),
            ('def urlsplit', TARGET, {'urlsplit'}), ('def urlparse', TARGET, {'urlparse'})):
        result, _ = act(dict(action='search', path=path, query=query, offset=0, limit=16),
            'The named task authority is the current implementation; locate the actual property, result splitting and public constructors.')
        found = [r['region_ref'] for r in result['regions'] if r.get('name') in names]
        assert found
        regions.extend(found)
    result, _ = act(dict(action='read', path=TEST, start_line=1, end_line=8),
        'The task names the test file; read its existing imports before adding an independent test class.')
    regions.append(result['source']['region_ref'])
    for query, path in (('if __name__', TEST), ('Structured Parse Results', DOC)):
        result, _ = act(dict(action='search', path=path, query=query, offset=0, limit=16),
            'Find a unique actual insertion location without replacing existing tests or documentation.')
        assert len(result['matches']) == 1
        regions.append(next(r['region_ref'] for r in result['regions'] if r.get('extent_kind') != 'enclosing Python function'))
    act(dict(action='work_on_exact', regions=list(dict.fromkeys(regions)), results=[]),
        'The returned reusable addresses identify the complete governing functions, imports and insertion anchors; inspect those bodies together.')
    view = session.view()
    shown = view['working_set']['sources']
    # The full source is used only to locate AST nodes; every premise consumed
    # by the evaluator must occur in the explicitly delivered current excerpts.
    # Unseen donor/reference artifacts and historical actor answers are absent.
    full = session.candidate.file_map[TARGET].decode()
    tree = ast.parse(full)
    needed = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in
        ('port', '_hostinfo', 'urlsplit', 'urlparse')]
    for node in needed:
        assert any(s['path'] == TARGET and s['returned_start_line'] <= node.lineno and
            s['returned_end_line'] >= node.end_lineno for s in shown), node.name
    for name in ('_NetlocResultMixinBase', '_NetlocResultMixinStr', '_NetlocResultMixinBytes'):
        assert any(('class ' + name + '(') in s['content'] for s in shown if s['path'] == TARGET), name
    good = derive_tests(full)
    bad = derive_tests(full, wrong_message=True)
    docs = derive_documentation(full)
    assert any(TEST_ANCHOR in s['content'] for s in shown if s['path'] == TEST)
    assert any(DOC_ANCHOR in s['content'] for s in shown if s['path'] == DOC)
    initial = session.candidate

    def patch(path, old, new):
        return dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(path))

    _, bad_outcome = act(patch(TEST, TEST_ANCHOR, bad + TEST_ANCHOR),
        'Deliberately save one incorrect range message to qualify actual successor-check feedback; this is an evaluator fault, not source-supported work.',
        account='Port property and both constructors inspected. This test proposal is not execution evidence; consume its declared tests check next.')
    failed = bad_outcome['operations'][-1]['result']
    assert failed['executed'] and not failed['passed']
    report = failed['report']
    assert RANGE_MESSAGE in str(report) and '0-65534' in str(report), report
    bad_candidate = session.candidate
    stale = patch(TEST, bad, good)
    stale['expected_candidate_id'] = initial.candidate_id
    stale['expected_file_sha256'] = initial.file_sha256(TEST)
    _, stale_outcome = act(stale, 'The earlier candidate binding is deliberately stale; no edit or automatic check may execute.', accepted=False)
    assert session.candidate.candidate_id == bad_candidate.candidate_id and len(stale_outcome['operations']) == 1
    _, corrected = act(patch(TEST, bad, good),
        'The delivered real assertion diagnostic disagrees with the provisional range message; replace that message using the independently inspected property.',
        account='The previous ordinary check failed on the wrong range diagnostic. Correct the authored expectation; documentation has not yet been changed.')
    check = corrected['operations'][-1]['result']
    assert check['executed'] and check['passed']
    assert not session.verification_view()['submission']['eligible']
    # Preserve saved tests but change the supporting group for documentation.
    doc_ref = next(s['region_ref'] for s in session.view()['working_set']['sources'] if s['path'] == DOC)
    port_ref = next(s['region_ref'] for s in session.view()['working_set']['sources'] if s['path'] == TARGET and 'def port' in s['content'])
    act(dict(action='work_on_exact', regions=[port_ref, doc_ref], results=[]),
        'The actual scoped tests pass applies to saved tests. Release test-authoring source and retain the inspected property and documentation anchor for the next contribution.',
        account='The corrected new tests passed their declared scope on the saved successor. Documentation is still pending; this tests pass does not establish examples or prose.')
    tested = session.candidate
    _, completed = act(patch(DOC, DOC_ANCHOR, docs + DOC_ANCHOR),
        'The visible property establishes these exact outputs and lazy exceptions; add self-contained examples without changing existing documentation.')
    public = completed['operations'][-1]['result']
    assert public['executed'] and public['passed'] and session.verification_view()['submission']['eligible']
    assert session.candidate.file_map[TEST] == tested.file_map[TEST]
    assert all(session.candidate.file_map[p] == initial.file_map[p] for p in initial.file_map if p not in (TEST, DOC))
    act(dict(action='submit', expected_candidate_id=session.candidate.candidate_id),
        'The actual public check passed on this current candidate; submit the preserved tests and documentation.',
        account='Tests and examples completed; the actual public check passed on the current candidate. No check is inferred from account text.')
    assert session.submitted and session.requests_used <= module.MAX_REQUESTS
    return rows


def qualify_capacity(module, session, measure, preceding, record=None):
    """Acquire real broad pages independently, then test their exact union.

    This is a plausible broad-source diagnostic branch, not an actor route or
    original stopped-state continuation. No allowance or archive is reset.
    """
    rows = []

    def act(action, basis, accepted=True):
        before = copy.deepcopy(session.view())
        n = measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = dict(discussion=basis, operation=action)
        output = module.process_reply(session, reply, measure, preceding)
        result = output['operations'][-1]['result']
        assert result.get('accepted') is accepted, result
        after = copy.deepcopy(session.view())
        m = measure(after)
        assert max(n, m) <= 23808 and not session.delivery_blocked
        row = dict(before_view=before, reply=reply, outcome=output, after_view=after,
            input_tokens=n, next_input_tokens=m,
            classification='researcher-selected broad-source capacity diagnostic')
        rows.append(row)
        if record:
            record(row, session)
        return result

    broad = []
    for path in (TEST, TARGET, DOC):
        result = act(dict(action='work_on', sources=[dict(path=path, start_line=1, end_line=0)], results=[]),
            'The task names this actual file; qualify a broad independent page without filler or hidden source.')
        assert len(result['sources']) == 1
        broad.append(result['sources'][0]['region_ref'])
    prior_candidate, prior_ranges, prior_account = session.candidate, copy.deepcopy(session.ranges), session.working_account()
    rejection = act(dict(action='work_on_exact', regions=broad, results=[]),
        'Previously delivered broad-page addresses identify their exact union. If it exceeds the ordinary ceiling, preserve designation and deliver control feedback.', accepted=False)
    assert session.recovery and session.candidate is prior_candidate and session.ranges == prior_ranges
    assert session.working_account() == prior_account
    assert session.view()['presentation']['selected_bodies_omitted'] and 'fit' in rejection['error'].lower()
    located = act(dict(action='search', path=TARGET, query='def port', offset=0, limit=16),
        'The task requires port behavior; use a real search in recovery to obtain reusable governing coordinates.')
    port = next(r['region_ref'] for r in located['regions'] if r.get('name') == 'port')
    inventory = act(dict(action='selection_page', offset=0),
        'The recovery view declares stored selections; inspect their returned exact addresses without treating the inventory as source.')
    doc = next(r for r in inventory['entries'] if r['kind'] == 'source' and r['path'] == DOC)
    # The full broad doc page is irrelevant to this narrow governing-code
    # decision; replacement selects the actual search's complete port function.
    result = act(dict(action='work_on_exact', regions=[port], results=[]),
        'The actual search identified the complete governing property. Select that exact region to return to ordinary presentation; this narrowing is evaluator-selected.')
    assert not session.recovery and result['sources'][0]['region_ref'] == port
    assert 'def port' in session.view()['working_set']['sources'][0]['content']
    assert session.candidate.candidate_id == prior_candidate.candidate_id
    return rows


def qualify(module, loop, adapter, store, folder):
    trials = []
    for label, route in (('contribution', qualify_contribution), ('broad_capacity', qualify_capacity)):
        session = module.initial_session()
        module.attach_observations(session, folder / ('scripted/' + label), loop.log)
        adapter.preceding_feedback.clear()
        def record(row, current):
            stem = f'scripted/{label}/steps/{len([t for t in trials if t["branch"] == label])+1:02d}'
            store.put(stem + '.json', canonical_json_bytes(row))
            store.put(stem + '-state.json', canonical_json_bytes(module.snapshot(current)))
            store.put(stem + '-candidate.json', module.candidate_bytes(current.candidate))
            restored = module.restore(load_json_strict(canonical_json_bytes(module.snapshot(current))),
                current.candidate, folder / ('scripted/' + label), replay=True)
            assert canonical_json_bytes(module.snapshot(restored)) == canonical_json_bytes(module.snapshot(current))
            assert restored.view() == current.view()
            trials.append(dict(branch=label, input_tokens=row['input_tokens'], next_input_tokens=row['next_input_tokens'],
                action=row['reply']['operation']['action'], accepted=row['outcome']['operations'][-1]['result']['accepted']))
        route(module, session, loop.measure, adapter.preceding_feedback, record)
    return dict(trials=trials, checks=dict(contribution=True, broad_capacity_recovery=True,
        original_entry_unchanged=True, scripted_choices_are_assisted=True, exact_checkpoint_restore=True))
