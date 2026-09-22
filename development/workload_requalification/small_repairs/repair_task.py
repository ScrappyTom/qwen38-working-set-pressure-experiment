"""Original small investigations, with common repaired host and exact checkers."""
import copy
import importlib
import importlib.util
from functools import lru_cache
from pathlib import Path

import diagnostic_task as host
import case_reports
import repair_qualification
from working_set_exp import decision_view
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.feedback_session import operating_reference
from working_set_exp.jsonutil import sha256_bytes,sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT,AREA=host.ROOT,Path(__file__).resolve().parent
ACTOR,SEED=host.ACTOR,host.SEED
MAX_REQUESTS,MAX_OPERATIONS=24,72
DESCRIPTIONS={'public':'Execute the unchanged original task acceptance check on this candidate; required for submission.'}
MODULES={'artifact_map':'prepare_investigation_loop', 'shift':'prepare_shift_investigation',
         'receipts':'prepare_correction_investigation'}
EPISODE_ANNOTATION=('Task-author context: the problem described in task was reported before this repair session. '
    'recent_activity and the retrievable operation history record this repair session\'s actions and results. '
    'Repetition of task is not a new observation after those actions.')


class Session(CoherentDiagnosticSession):
    assessment_api=case_reports

    def view(self, **kwargs):
        value=super().view(**kwargs)
        value['episode_annotation']=EPISODE_ANNOTATION
        return value


@lru_cache(maxsize=1)
def response_constraints():
    path=ROOT/'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path)=='ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec=importlib.util.spec_from_file_location('repair_schema_converter',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return dict(grammar=with_thinking(decision_view.reply_grammar(DESCRIPTIONS,module.SchemaConverter)))


def expected_native(request):
    assert request['grammar']==response_constraints()['grammar'] and 'response_format' not in request
    envelope=copy.deepcopy(request)
    # The actual decoder grammar remains saved/qualified separately. It is not
    # rendered by this template, so reuse the exact qualified message verification.
    envelope['grammar']=host.response_constraints()['grammar']
    return host.expected_native(envelope)


class Task:
    def __init__(self,case,version='001',replay_folder=None):
        self.case,self.legacy=case,importlib.import_module(MODULES[case])
        self.AREA=AREA/case
        self.PACKAGE,self.RUN=self.AREA/f'preparation-{version}',self.AREA/f'run-{version}'
        self.MANIFEST=self.AREA/f'EXECUTION_MANIFEST-{version}.json'
        self.replay_folder=replay_folder

    def initial_session(self):
        fixture=self.legacy.constructed_fixture()
        assert not fixture.required_inspection_paths and not fixture.observations
        return Session(fixture.initial,{'public':fixture.public_checker},fixture.task,
            edit_checks={},call_limit=MAX_OPERATIONS,request_limit=MAX_REQUESTS,
            observations=ObservationStore((self.replay_folder or self.AREA/'unexecuted')/'observations',
                                          replay=self.replay_folder is not None),
            check_contracts={'public':dict(checker_sha256=sha256_bytes(fixture.public_checker))})

    def reply_schema(self):
        return decision_view.reply_schema(DESCRIPTIONS)

    def operating_reference(self):
        marker='\nrecent_edit_rejection is historical host feedback'
        text=operating_reference(DESCRIPTIONS)+marker+host.operating_reference().split(marker,1)[1]
        # These unchanged checkers have no mutation component.
        previous=('Ordinary tests must pass before mutation failures count as detection. '
                  'Each declared fault target must be detected by the new tests; normal failure blocks that assessment. '
                  'Mutation-run missing paths are not additional requirements.')
        assert text.count(previous)==1, 'Shared contract wording changed; review the task-specific reference'
        text=text.replace(previous,'The original public checker must pass; there are no injected fault tests in this task.')
        automatic=('verification.after_accepted_edit declares which check the host executes after an accepted edit '
            'to each listed path. A rejected edit skips the check; a failing check preserves the saved edit. '
            'The host binds the check to the actual successor and returns the real receipts before your '
            'next decision. Each account update, requested operation and automatic check consumes one '
            'operation; they share one model request when combined. A reply cannot execute an arbitrary '
            'adaptive sequence. The full declared sequence needs operation allowance before it starts. '
            'Account updates, requested operations and automatic checks share the exact archive: EVT stores '
            'action arguments, including account text; RES stores actual receipts.')
        assert text.count(automatic)==1, 'Automatic-check reference changed; review task policy'
        text=text.replace(automatic,
            'verification.after_accepted_edit is empty in this task: edits do not trigger checks. '
            'After an accepted edit, request check public in a later reply using the returned current candidate. '
            'A failed check preserves the saved edit. Each account update and requested operation consumes '
            'one operation; an account and one operation may share a model request. A reply cannot execute '
            'an arbitrary adaptive sequence. Account updates and requested operations share the exact archive: '
            'EVT stores action arguments, including account text; RES stores actual receipts.')
        text=text.replace('source refresh and declared successor checks apply.', 'source refresh apply.')
        text=text.replace('Passing examples do not validate all surrounding prose, and passing tests do not prove complete coverage.',
            'Passing the public check establishes its reported cases; it does not verify every untested behavior or endorse the account.')
        return text

    def implementation_identities(self):
        paths=[*AREA.glob('*.py'),AREA/'SPEC.md',self.AREA/'SYSTEM.txt',self.AREA/'SPEC.md',
               self.legacy.AREA/'TASK.txt',self.legacy.AREA/'PUBLIC_CHECK.py',
               *sorted((AREA/'tests').glob('*.py'))]
        return {**host.source_identities(),**self.legacy.source_identities(),
                **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}

    def source_identities(self):
        return {**self.implementation_identities(),**prerequisite_bindings()}

    def __getattr__(self,name):
        return globals()[name] if name in globals() else getattr(host,name)


def __getattr__(name):
    return getattr(host,name)


def prerequisite_bindings():
    cpu={}
    for case in MODULES:
        cpu.update(Task(case).implementation_identities())
    native=Task('artifact_map').implementation_identities()
    return {**repair_qualification.verify(ROOT,AREA/'checker-qualification-005',cpu,'checker'),
            **repair_qualification.verify(ROOT,AREA/'native-005',native,'native')}
