"""CPU-ready original backport adapter; no runtime or model dispatch path."""
from pathlib import Path

import configparser_reports as reports
from working_set_exp import decision_view
from working_set_exp.candidate import Candidate
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.feedback_session import operating_reference as common_reference
from working_set_exp.jsonutil import load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT = Path(__file__).resolve().parents[3]
AREA = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'development/configparser_backport'
PACKAGE = ORIGINAL / 'input-qualification-003'
STARTING_ID = 'f32256765ff11d4a353900e33ec9b503255cd4718ea344f77e17311a84391170'
TASK_SHA = '9ead28afffaad5cd04527d9fdd0f3ae86974e219e9b6a48a6dc4b01098af3717'
CHECKER_SHA = '20906e55f2d2ac0646bc46ec81f42af6b033b1a871d1bb1bbc9dce43f0f1fb19'
FILE_LIMIT = 1_048_576
MAX_REQUESTS, MAX_OPERATIONS = 40, 80
DESCRIPTIONS = {'public': 'Execute the original backport acceptance on this candidate; required for submission. Documentation accuracy and preservation also require direct review.'}
EPISODE_ANNOTATION = (
    'Task-author context: the problem described in task was reported before this repair session. '
    "recent_activity and the retrievable operation history record this repair session's actions and results. "
    'Repetition of task is not a new observation after those actions.')

RUNNER_OLD = '''def run_suite(suite):
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), successful=result.wasSuccessful(),
        details=[dict(test=test.id(), trace=trace) for test, trace in (*result.failures, *result.errors)])
'''
RUNNER_NEW = '''def run_suite(suite):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), successful=result.wasSuccessful(),
        details=[dict(test=test.id(), trace=trace) for test, trace in (*result.failures, *result.errors)],
        runner_output=stream.getvalue())
'''
FORMAT_START = '    # Return bounded useful diagnostics; the host additionally preserves stream\n'
FORMAT_END = '    raise SystemExit(0 if passed else 1)\n'
FORMAT_NEW = '''    # Preserve complete observations; presentation reduction happens after custody.
    report = dict(observation_schema='configparser-original-v1', passed=passed, **result)
    print(json.dumps(report, ensure_ascii=True, separators=(',', ':')), flush=True)
    raise SystemExit(0 if passed else 1)
'''


def task_text():
    raw = (ORIGINAL / 'TASK.txt').read_bytes()
    assert sha256_bytes(raw) == TASK_SHA, 'Original task changed'
    return raw.decode('utf-8')


def starting_candidate():
    value = load_json_strict((PACKAGE / 'candidate.json').read_bytes())
    files = {r['path']: r['content_utf8'].encode('utf-8') for r in value['files']}
    assert len(files) == len(value['files']) == 10, 'Original file inventory differs'
    candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
    assert candidate.candidate_id == value['candidate_id'] == STARTING_ID
    return candidate


def original_checker():
    raw = (PACKAGE / 'PUBLIC_CHECK.py').read_bytes()
    assert sha256_bytes(raw) == CHECKER_SHA, 'Frozen original checker changed'
    return raw


def checker():
    """Change only observation retention and the final presentation boundary."""
    code = original_checker().decode('utf-8')
    assert code.count(RUNNER_OLD) == code.count(FORMAT_START) == code.count(FORMAT_END) == 1
    code = code.replace(RUNNER_OLD, RUNNER_NEW)
    start = code.index(FORMAT_START)
    end = code.index(FORMAT_END, start) + len(FORMAT_END)
    return (code[:start] + FORMAT_NEW + code[end:]).encode('utf-8')


class Session(CoherentDiagnosticSession):
    assessment_api = reports

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['episode_annotation'] = EPISODE_ANNOTATION
        return value


def initial_session(observation_root, *, replay=False):
    code = checker()
    return Session(starting_candidate(), {'public': code}, task_text(),
        edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
        observations=ObservationStore(observation_root, replay=replay),
        check_contracts={'public': {'checker_sha256': sha256_bytes(code),
                                  'original_acceptance_checker_sha256': CHECKER_SHA}})


def reply_schema():
    return decision_view.reply_schema(DESCRIPTIONS)


def operating_reference():
    text = common_reference(DESCRIPTIONS)
    previous = ('Ordinary tests must pass before mutation failures count as detection. '
        'Each declared fault target must be detected by the new tests; normal failure blocks that assessment. '
        'Mutation-run missing paths are not additional requirements.')
    replacement = ('The frozen upstream suite, independent backport contract and current edited tests must pass. '
        'The separate run of current added tests against the original parser must fail or error to detect the original defect. '
        'That expected failure is successful regression detection, not a failure of the current library. '
        'There are no injected fault targets in this public check. The documentation declaration check does not establish accurate prose.')
    assert text.count(previous) == 1
    text = text.replace(previous, replacement)
    previous = ('verification.after_accepted_edit declares which check the host executes after an accepted edit '
        'to each listed path. A rejected edit skips the check; a failing check preserves the saved edit. '
        'The host binds the check to the actual successor and returns the real receipts before your '
        'next decision. Each account update, requested operation and automatic check consumes one '
        'operation; they share one model request when combined. A reply cannot execute an arbitrary '
        'adaptive sequence. The full declared sequence needs operation allowance before it starts. '
        'Account updates, requested operations and automatic checks share the exact archive: EVT stores '
        'action arguments, including account text; RES stores actual receipts.')
    replacement = ('verification.after_accepted_edit is empty: edits do not trigger checks. '
        'Request check public in a later reply using the returned current candidate. A failed check preserves saved work. '
        'Each account update and requested operation consumes one operation; an account and one operation may share '
        'one model request. A reply cannot execute an arbitrary adaptive sequence. EVT stores action arguments, '
        'including account text; RES stores actual receipts.')
    assert text.count(previous) == 1
    text = text.replace(previous, replacement)
    text = text.replace('source refresh and declared successor checks apply.', 'source refresh apply.')
    text = text.replace('Passing examples do not validate all surrounding prose, and passing tests do not prove complete coverage.',
        'The public pass does not establish accurate documentation, complete added coverage or intact preexisting test text; those need direct review.')
    text += ('\nrecent_edit_rejection is historical host feedback for unchanged file bytes, '
        'not an instruction to repeat the rejected request. Its match references are addresses; '
        'read their exact current source before editing. Replacing a selected group does not erase saved work.')
    return text


def source_identities():
    paths = [*AREA.glob('*.py'), *sorted((AREA / 'tests').glob('*.py')),
        AREA / 'PLAN.md', AREA / 'SOURCE_CONTRACT.md', AREA / 'SOURCE_CONTRACT.json',
        ORIGINAL / 'TASK.txt', PACKAGE / 'candidate.json', PACKAGE / 'PUBLIC_CHECK.py',
        ORIGINAL / 'REFERENCE_EDITS.json', ORIGINAL / 'reference-qualification-002/RESULTS.json',
        *sorted((ORIGINAL / 'reference-qualification-002/reference-candidate').rglob('*')),
        *sorted((ROOT / 'src/working_set_exp').rglob('*.py'))]
    return {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths if p.is_file()}
