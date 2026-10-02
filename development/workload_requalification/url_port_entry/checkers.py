"""Exact original URL acceptance with observations preserved before reduction.

Only the capture/report boundary changes. The ordinary suites, required paths,
seven injected faults, preservation and doctest predicates remain original.
"""
from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import load_json_strict, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[3]
AREA = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'development/working_account/url_ports'
FACTORY = ORIGINAL.parent / 'task.py'
HELPER = ORIGINAL.parent / 'examples.py'
FACTORY_SHA = '85034732668bd53c882c78ef2b8426517add089a8ebada205ad8e490490a9b40'
TAIL_SHA = 'd7fc455c3c9c6722790990f6e12c18ff0f983014c67cc3aacfe9caf442d0301e'
HELPER_SHA = '120b790115ce99fc0a0e70473a57283b580ddd7613c79f322cae455bae0670f6'
SOURCE_SHA = 'a80f1f80f9228b15d6b2a32513d791eae995ec4c0e93792052ab4ec7ebcc3548'
STARTING_ID = '2921cbc8a115c86871a11f8eaea929c3d48a8e4d2bb2ca03bf48971c36cf15cd'
FILES = ('Lib/urllib/__init__.py', 'Lib/urllib/parse.py', 'Lib/test/__init__.py',
    'Lib/test/test_urlparse.py', 'Doc/library/urllib.parse.rst', 'LICENSE')
SCOPES = ('tests', 'examples', 'public')
FAULTS = ('error_class', 'error_arguments', 'error_message', 'eager_validation',
    'empty_port', 'zero_port', 'maximum_port')
ORIGINAL_CHECKER_SHA = dict(
    tests='feb620566b116cba4e542d929f92fbcbd8a25a42656f41d8773d30583314d2cf',
    examples='63d69f2458f46c39bf35a7567f3cc8e2b203db3050f0e7add4be8939af422c25',
    public='f68215eea0ca2421f56b28023ea51702b59c6faa3ae5b6e2a023450786543627')
FAULT_CHANGES = dict(
    error_class='Replace the real ValueError with a subclass of ValueError.',
    error_arguments='Append an unexpected second argument to the real ValueError.',
    error_message='Replace the real ValueError diagnostic with incorrect port diagnostic.',
    eager_validation='Access port while constructing the otherwise valid URL result.',
    empty_port='Return 0 instead of None for an empty port.',
    zero_port='Return None instead of 0 for port zero.',
    maximum_port='Return 65534 instead of 65535 for the maximum port.')

RUN_SUITE_OLD = '''def run_suite(suite):
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), successful=result.wasSuccessful(),
                details=[dict(test=t.id(), trace=text[-700:]) for t, text in
                         [*result.failures, *result.errors]][:1])
'''
RUN_SUITE_NEW = '''def run_suite(suite):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), successful=result.wasSuccessful(),
                details=[dict(test=t.id(), trace=text) for t, text in
                         [*result.failures, *result.errors]], runner_output=stream.getvalue())
'''
CUT = 'if len(encode().encode()) > 6500:\n'
EXAMPLE_CUT = 'details=output.getvalue()[-2200:])'


@lru_cache(maxsize=1)
def _starting_files():
    if sha256_file(ORIGINAL / 'SOURCE.json') != SOURCE_SHA:
        raise ValueError('Original URL source manifest differs')
    rows = {row['path']: row for row in load_json_strict((ORIGINAL / 'SOURCE.json').read_bytes())['files']}
    files = {path: (ORIGINAL / 'world' / path).read_bytes() for path in FILES}
    if any(sha256_bytes(body) != rows[path]['sha256'] for path, body in files.items()):
        raise ValueError('Original URL source body differs')
    if Candidate.create(files, max_file_bytes=1_048_576).candidate_id != STARTING_ID:
        raise ValueError('Original six-file URL candidate differs')
    return tuple(sorted(files.items()))


def starting_files():
    """Return a fresh map; candidate variants cannot mutate the frozen baseline."""
    return dict(_starting_files())


def _inputs():
    if (sha256_file(FACTORY), sha256_file(ORIGINAL / 'CHECK.py'), sha256_file(HELPER)) != (
            FACTORY_SHA, TAIL_SHA, HELPER_SHA):
        raise ValueError('Original URL checker factory, tail or example helper differs')
    return (ORIGINAL / 'CHECK.py').read_text(encoding='utf-8'), HELPER.read_text(encoding='utf-8')


def _assemble(scope, tail, helper):
    if scope not in SCOPES:
        raise ValueError('Unknown original URL check scope')
    values = dict(_BASELINE_FILES={path: body.decode() for path, body in
        Candidate.create(starting_files(), max_file_bytes=1_048_576).files},
        _SCOPE=scope, _EXAMPLES_HELPER=helper)
    return (''.join(key + ' = ' + repr(value) + '\n' for key, value in values.items()) + tail).encode()


@lru_cache(maxsize=3)
def original_checker(scope='public'):
    tail, helper = _inputs()
    result = _assemble(scope, tail, helper)
    if sha256_bytes(result) != ORIGINAL_CHECKER_SHA[scope]:
        raise ValueError('Original generated URL checker differs')
    return result


def _acceptance_functions(source):
    names = {'methods', 'load', 'cases', 'category', 'added_suite', 'exercise', 'assess'}
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name in names}


@lru_cache(maxsize=3)
def checker(scope='public'):
    original_checker(scope)  # Prove the exact baseline generated definition first.
    tail, helper = _inputs()
    if tail.count(RUN_SUITE_OLD) != 1 or tail.count(CUT) != 1 or helper.count(EXAMPLE_CUT) != 1:
        raise ValueError('Original observation-reduction boundary changed')
    revised_helper = helper.replace(EXAMPLE_CUT, 'details=output.getvalue())')
    revised = tail.replace(RUN_SUITE_OLD, RUN_SUITE_NEW).split(CUT, 1)[0]
    revised += ("# Preserve complete observations before deriving a bounded model-facing report.\n"
        "report['observation_schema'] = 'contribution-check-v2'\n"
        "print(encode(), flush=True)\n"
        "raise SystemExit(0 if report['passed'] else 1)\n")
    if _acceptance_functions(tail) != _acceptance_functions(revised):
        raise ValueError('Original URL acceptance functions changed')
    return _assemble(scope, revised, revised_helper)


def contracts():
    return {scope: dict(checker_sha256=sha256_bytes(checker(scope)),
        original_acceptance_checker_sha256=ORIGINAL_CHECKER_SHA[scope],
        fault_changes=dict(FAULT_CHANGES) if scope in ('tests', 'public') else {}) for scope in SCOPES}


check_contracts = contracts


def source_identities():
    paths = [Path(__file__), AREA / 'url_reports.py', FACTORY, HELPER, ORIGINAL / 'CHECK.py',
        ORIGINAL / 'SOURCE.json', *(ORIGINAL / 'world' / path for path in FILES)]
    return {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}
