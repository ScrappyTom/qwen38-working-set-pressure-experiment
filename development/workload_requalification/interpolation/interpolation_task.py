"""Original interpolation workload on the qualified exact-work host."""
import copy
from functools import lru_cache
from pathlib import Path

import diagnostic_task as host
import interpolation_contribution as legacy
import reporting
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.feedback_session import operating_reference as reference
from working_set_exp.jsonutil import sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = host.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = host.ACTOR, host.SEED
MAX_REQUESTS, MAX_OPERATIONS = 32, 96
OWNER_DIRECTION = "Repeat the repair/qualify/run process until the previously tested workloads pass."
TEST, DOC = 'Lib/test/test_configparser.py', 'Doc/library/configparser.rst'
DESCRIPTIONS = dict(public='Original acceptance, saved-work preservation, requested tests, restoration faults and executable documentation; required for submission.',
    tests='Saved suite, independent backport contract, new lookup/transport paths and restoration faults; excludes documentation completion.',
    examples='Execute the newly added documentation examples against the current library; does not verify surrounding prose.')
FAULTS = {n:'Restore a changed '+n+' value.' for n in ('option','section','raw_value','reference')}
FAULTS.update(restored_class='Return a subclass after one declared mode/transport while keeping constructor state.',
    restored_diagnostic='Change the restored diagnostic after one declared mode/transport, leaving the original error unchanged.')


class Session(CoherentDiagnosticSession):
    assessment_api = reporting


@lru_cache(maxsize=3)
def checker(scope='public'):
    assert scope in DESCRIPTIONS
    code = legacy.checker().decode()
    boundary = '\nfor part in parts + list(report["restoration_faults"].values()):\n'
    assert code.count(boundary) == 1
    exact_computation = code.split(boundary)[0] + '\n'
    # The old calculation and complete in-memory observations precede the destructive
    # formatter. Keep them verbatim; add declared interpretation/checking afterward.
    examples = (ROOT/'development/operable_recovery/examples.py').read_text(encoding='utf-8')
    examples = examples.replace('doctest.DocTestRunner()', 'doctest.DocTestRunner(verbose=False)')
    prefix = '_SCOPE = '+repr(scope)+'\n_EXAMPLES_HELPER = '+repr(examples)+'\n'
    if scope == 'examples':
        before = exact_computation.split('\ndef suite(')[0]
        return (prefix+before+"\nnamespace = {}\nexec(_EXAMPLES_HELPER, namespace)\n"+
            "value = namespace['check_added_examples'](_SAVED_FILES[doc_path], Path(doc_path).read_text(encoding='utf-8'), doc_path)\n"+
            "print(json.dumps(dict(observation_schema='contribution-check-v2', scope='examples', examples=value, passed=value['successful'])))\n"+
            "raise SystemExit(0 if value['successful'] else 1)\n").encode()
    return (prefix+exact_computation+(AREA/'EXTRA_CHECKS.py').read_text(encoding='utf-8')).encode()


def operating_reference():
    # Same tested operation contracts, with this task's truthful scope descriptions.
    marker = '\nrecent_edit_rejection is historical host feedback'
    return reference(DESCRIPTIONS) + marker + host.operating_reference().split(marker, 1)[1]


snapshot = host.snapshot


def source_identities():
    paths = [*AREA.glob('*.py'),AREA/'TASK.txt',AREA/'SYSTEM.txt',AREA/'SPEC.md',
             AREA.parent/'PLAN.md', legacy.AREA/'REFERENCE_TEST.py',legacy.AREA/'REFERENCE_DOC.txt']
    return {**host.source_identities(), **legacy.source_identities(),
            **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


class Task:
    def __init__(self, version='001', replay_folder=None):
        self.PACKAGE, self.RUN = AREA/f'preparation-{version}', AREA/f'run-{version}'
        self.MANIFEST = AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder = replay_folder

    def initial_session(self):
        old = legacy.initial_session()
        checkers = {s:checker(s) for s in DESCRIPTIONS}
        session = Session(old.candidate, checkers, (AREA/'TASK.txt').read_text(encoding='utf-8'),
            edit_checks={TEST:'tests',DOC:'public'}, pairs=old.pairs,
            call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
            observations=ObservationStore((self.replay_folder or AREA/'unexecuted-observations')/'observations',
                                          replay=self.replay_folder is not None),
            check_contracts={s:dict(checker_sha256=sha256_bytes(c),fault_changes=FAULTS) for s,c in checkers.items()})
        for k in ('ranges','saved','diffs','last'):
            setattr(session,k,copy.deepcopy(getattr(old,k)))
        assert session.candidate.candidate_id == legacy.STARTING_ID
        return session

    def __getattr__(self,name):
        return globals()[name] if name in globals() else getattr(host,name)


def __getattr__(name):
    return getattr(host,name)
