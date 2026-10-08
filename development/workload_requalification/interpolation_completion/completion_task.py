"""Declared completion of actual unfinished work using the current common host."""
import copy
import importlib.util
from functools import lru_cache
from pathlib import Path

import bootstrap
import dispatch_task as runtime
import interpolation_task as original
import completion_reports
import navigation
import operational_reply
from search_navigation import SearchNavigationMixin, REFERENCE_ADDITION
from working_set_exp.candidate import Candidate
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.current_job_view import render
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
INHERITED = AREA.parent / 'interpolation_revision/run-002'
ACTOR, SEED = original.ACTOR, original.SEED
TEST, DOC, DESCRIPTIONS = original.TEST, original.DOC, original.DESCRIPTIONS
FAULTS = {**original.FAULTS,
    'restored_arguments': 'Change only the restored original argument tuple at one mode/transport.',
    **{'restored_' + name: 'Change only the restored ' + name + ' attribute at one mode/transport.'
       for name in ('option', 'section', 'reference')}}
REQUIRED_INSPECTION_PATHS = (TEST, DOC, 'Lib/configparser.py', 'LICENSE')  # decoder specimens only
TITLE = 'Complete missing-interpolation tests and documentation'
OWNER_DIRECTION = 'Proceed with the declared current-host completion of unfinished interpolation work.'
read, save, candidate_bytes = runtime.read, runtime.save, runtime.candidate_bytes


@lru_cache(maxsize=3)
def checker(scope='public'):
    code = original.checker(scope).decode()
    # The frozen checker remains unchanged. Replace its embedded example helper
    # prospectively, with an explicit ordinary standalone namespace.
    lines = code.splitlines(keepends=True)
    assert lines[1].startswith('_EXAMPLES_HELPER = ')
    import ast
    helper = ast.literal_eval(lines[1].split('=', 1)[1])
    helper = helper.replace('get_doctest(after, {},', "get_doctest(after, {'__name__': '__main__'},")
    helper = helper.replace('doctest.DocTest(selected, {},', "doctest.DocTest(selected, {'__name__': '__main__'},")
    helper = helper.replace("return dict(examples=", "return dict(environment={'__name__': '__main__', 'scope': 'changed examples in document order'}, examples=")
    lines[1] = '_EXAMPLES_HELPER = ' + repr(helper) + '\n'
    code = ''.join(lines)
    if scope != 'examples':
        before = "for fault in ('restored_class', 'restored_diagnostic'):"
        assert code.count(before) == 1
        code = code.replace(before, "for fault in ('restored_class', 'restored_diagnostic', 'restored_arguments', 'restored_option', 'restored_section', 'restored_reference'):")
        before = "                        value.message += ' [injected diagnostic fault]'"
        assert code.count(before) == 1
        code = code.replace(before, """                        if fault == 'restored_arguments':
                            args = list(value.args)
                            args[2] += ' [injected argument fault]'
                            value.args = tuple(args)
                        elif fault in ('restored_option', 'restored_section', 'restored_reference'):
                            name = fault.removeprefix('restored_')
                            setattr(value, name, getattr(value, name) + ' [injected attribute fault]')
                        else:
                            value.message += ' [injected diagnostic fault]'""")
        before = "and all(faults[n]['all_targets_detected'] for n in ('restored_class','restored_diagnostic')))"
        assert code.count(before) == 1
        code = code.replace(before, "and all(value['all_targets_detected'] for key,value in faults.items() if key.startswith('restored_')))")
    return code.encode()


def reply_schema(): return operational_reply.reply_schema(DESCRIPTIONS)
def decode_reply(content): return operational_reply.decode_reply(content, DESCRIPTIONS)
def operating_reference():
    return (operational_reply.operating_reference(original.operating_reference()) + '\n\n'
            + navigation.REFERENCE_ADDITION + '\n\n' + REFERENCE_ADDITION)


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('interpolation_completion_converter', path)
    converter = importlib.util.module_from_spec(spec); spec.loader.exec_module(converter)
    return {'grammar': with_thinking(operational_reply.reply_grammar(DESCRIPTIONS, converter.SchemaConverter))}


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and request['seed'] == SEED
    envelope = copy.deepcopy(request)
    envelope['grammar'] = original.host.response_constraints()['grammar']
    return original.host.expected_native(envelope)


def candidate_from_snapshot(value):
    candidate = Candidate.create({r['path']: r['content_utf8'].encode() for r in value['files']},
                                 max_file_bytes=value['max_file_bytes'])
    assert candidate_bytes(candidate) == canonical_json_bytes(value)
    return candidate


@lru_cache(maxsize=1)
def inherited_material():
    seal = read(INHERITED / 'RESPONSE_SEAL.json')
    assert seal['disposition'] == 'request_allowance_exhausted'
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files']:
        raw = (INHERITED / row['path']).read_bytes()
        assert len(raw) == row['size_bytes'] and sha256_bytes(raw) == row['sha256'], row['path']
    state = read(INHERITED / 'final-state.json')
    candidate = candidate_from_snapshot(read(INHERITED / 'final-candidate.json'))
    assert candidate.candidate_id == original.legacy.STARTING_ID == state['candidate_id']
    assert len(state['pairs']) == 101 and state['requests_used'] == 10
    return state, candidate


class Session(SearchNavigationMixin, navigation.NavigationMixin, CoherentDiagnosticSession):
    assessment_api = completion_reports
    def reply_schema(self): return reply_schema()
    @property
    def calls_used(self): return len(self.pairs)
    def view(self, **kwargs):
        return render(super().view(**kwargs), title=TITLE, pairs=self.pairs,
                      boundary=self.starting_archive_length, submitted=self.submitted)


def snapshot(session):
    return {**original.snapshot(session),
            'source_versions': [read_bytes(candidate_bytes(v)) for _,v in sorted(session.versions.items())]}


def read_bytes(raw):
    from working_set_exp.jsonutil import load_json_strict
    return load_json_strict(raw)


class Task(runtime.Task):
    def __init__(self, version='001'):
        self.phase, self.version, self.AREA, self.inherited = 'interpolation_completion', version, AREA, INHERITED
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'
        self.inherited_state, self.inherited_candidate = inherited_material()
        self.INHERITED_REQUESTS, self.INHERITED_OPERATIONS = 32, 101
        self.MAX_REQUESTS, self.MAX_OPERATIONS = 64, 197

    def initial_session(self, folder=None, replay=False):
        checks = {scope: checker(scope) for scope in DESCRIPTIONS}
        session = Session(self.inherited_candidate, checks, (AREA / 'TASK.txt').read_text(encoding='utf-8'),
            edit_checks={TEST: 'tests', DOC: 'public'}, pairs=copy.deepcopy(self.inherited_state['pairs']),
            call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS,
            observations=ObservationStore((Path(folder) if folder else INHERITED) / 'observations',
                                          replay=replay or folder is None),
            check_contracts={scope: dict(checker_sha256=sha256_bytes(code), fault_changes=FAULTS)
                             for scope,code in checks.items()})
        session.requests_used, session.starting_archive_length = self.INHERITED_REQUESTS, self.INHERITED_OPERATIONS
        session.diffs = {int(k): copy.deepcopy(v) for k,v in self.inherited_state['diffs'].items()}
        session.last, session.ranges, session.saved, session.delivered_sources = None, [], {}, []
        return session

    def restore(self, state, candidate, replay_folder=None, replay=False):
        if not isinstance(candidate, Candidate): candidate = candidate_from_snapshot(candidate)
        session = self.initial_session(replay_folder, replay)
        assert set(state) == set(snapshot(session)), 'Checkpoint shape differs'
        assert state['candidate_id'] == candidate.candidate_id
        assert (state['request_limit'], state['call_limit']) == (self.MAX_REQUESTS, self.MAX_OPERATIONS)
        assert self.INHERITED_REQUESTS <= state['requests_used'] <= self.MAX_REQUESTS
        assert state['pairs'][:self.INHERITED_OPERATIONS] == self.inherited_state['pairs']
        for key,value in state.items():
            if key not in ('candidate_id', 'source_versions'):
                setattr(session, key, copy.deepcopy(value))
        session.candidate = candidate
        session.versions = {v.candidate_id:v for v in map(candidate_from_snapshot, state['source_versions'])}
        assert candidate.candidate_id in session.versions
        session.diffs = {int(k):v for k,v in session.diffs.items()}
        session.restored_control_fields = tuple(session.restored_control_fields)
        session.parked_source_regions = tuple(tuple(r) for r in session.parked_source_regions)
        assert canonical_json_bytes(snapshot(session)) == canonical_json_bytes(state)
        return session

    def implementation_identities(self):
        paths = [*AREA.glob('*.py'), AREA/'SYSTEM.txt', AREA/'TASK.txt', AREA/'PLAN.md', AREA/'SPEC.md',
                 *sorted((AREA/'tests').glob('*.py')), INHERITED/'RESPONSE_SEAL.json']
        paths += [INHERITED/r['path'] for r in read(INHERITED/'RESPONSE_SEAL.json')['files']]
        helpers = ('dispatch_continuity/bootstrap.py', 'dispatch_continuity/dispatch_task.py',
            'dispatch_continuity/run_dispatch.py', 'current_job_presentation/contract_completion/run_contract.py',
            'ecological_import_entry/native_forms.py', 'action_lifecycle/native_forms.py',
            'action_lifecycle/operational_reply.py', 'navigation_continuity/navigation.py',
            'search_continuity/search_navigation.py', 'interpolation_revision/report_projection.py')
        paths += [AREA.parent/name for name in helpers]
        paths += [ROOT/'src/working_set_exp/current_job_view.py', AREA/'CPU_QUALIFICATION.json']
        for qualification in sorted(AREA.glob('cpu-*')):
            if qualification.is_dir(): paths += [p for p in qualification.rglob('*') if p.is_file()]
        return {**original.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}

    source_identities = implementation_identities
    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(original, name)


process_reply, present_receipts = runtime.process_reply, navigation.present_receipts
