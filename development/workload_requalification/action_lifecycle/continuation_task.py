"""Exact receipt checkpoint with a required operational final reply.

The five original dispatches/operations remain consumed. Restoring this checkpoint
does not select source, execute an operation, rewrite an account or renew a limit.
"""
import copy
import importlib.util
from functools import lru_cache
from pathlib import Path

import bootstrap  # noqa: F401
import navigation_task as previous
import operational_reply
from working_set_exp.candidate import Candidate
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore
from working_set_exp.thinking_grammar import with_thinking

ROOT, AREA = previous.ROOT, Path(__file__).resolve().parent
OLD = previous.AREA / 'receipts' / 'run-001'
ORIGINAL_REPLAY = previous.AREA / 'receipts' / 'review' / 'VERIFICATION.json'
ACTOR, SEED = previous.ACTOR, previous.SEED
DESCRIPTIONS = previous.DESCRIPTIONS
MAX_REQUESTS, MAX_OPERATIONS = 24, 72
INHERITED_REQUESTS, INHERITED_OPERATIONS = 5, 5
MAXIMUM_NEW_REQUESTS, MAXIMUM_NEW_OPERATIONS = 19, 67
ACCOUNTING = dict(inherited_requests=INHERITED_REQUESTS, inherited_operations=INHERITED_OPERATIONS,
                  maximum_new_requests=MAXIMUM_NEW_REQUESTS, maximum_new_operations=MAXIMUM_NEW_OPERATIONS,
                  original_request_limit=MAX_REQUESTS, original_operation_limit=MAX_OPERATIONS,
                  request_numbering='cumulative; first new invocation is C06',
                  original_disposition='actor_stopped_without_operation')
snapshot = previous.snapshot


def checkpoint_bindings():
    """Verify every sealed original artifact and its already-completed replay."""
    seal_path = OLD / 'RESPONSE_SEAL.json'
    seal = load_json_strict(seal_path.read_bytes())
    assert seal['disposition'] == 'actor_stopped_without_operation'
    assert seal['sent_requests'] == seal['returned_responses'] == seal['processed_invocations'] == INHERITED_REQUESTS
    assert seal['actual_operations'] == INHERITED_OPERATIONS and seal['port_free']
    assert seal['actor'] == ACTOR
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    bindings = {seal_path.relative_to(ROOT).as_posix(): sha256_file(seal_path)}
    names = []
    for row in seal['files']:
        path = OLD / row['path']
        assert path.resolve().is_relative_to(OLD.resolve()), 'Checkpoint artifact leaves its run'
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
        bindings[path.relative_to(ROOT).as_posix()] = row['sha256']
        names.append(row['path'])
    assert len(names) == len(set(names))
    assert not any(name.startswith('observations/') for name in names), 'Unexpected inherited observation'
    for suffix in ('state', 'candidate', 'preceding-feedback'):
        assert f'final-{suffix}.json' in names
    records = verify_records(OLD / 'records.jsonl', OLD)
    assert len(records) == seal['record_count']
    assert sum(r['record_type'] == 'invocation_started' for r in records) == INHERITED_REQUESTS
    replay = load_json_strict(ORIGINAL_REPLAY.read_bytes())
    assert replay['status'] == 'replayed_exactly' and replay['case'] == 'receipts'
    assert replay['requests_used'] == replay['completed_replies'] == INHERITED_REQUESTS
    assert replay['actual_operations'] == INHERITED_OPERATIONS and not replay['submitted']
    assert replay['owned_runtime_closed'] and replay['no_additional_checker_execution']
    assert replay['observations_replayed_without_execution'] == 0
    bindings[ORIGINAL_REPLAY.relative_to(ROOT).as_posix()] = sha256_file(ORIGINAL_REPLAY)
    return bindings


def initial_preceding_feedback():
    checkpoint_bindings()
    value = load_json_strict((OLD / 'final-preceding-feedback.json').read_bytes())
    assert value == [], 'Receipt checkpoint feedback changed'
    return value


class Session(previous.Session):
    def reply_schema(self):
        return operational_reply.reply_schema(DESCRIPTIONS)


def restore(replay_folder=None):
    checkpoint_bindings()
    assert initial_preceding_feedback() == []
    state = load_json_strict((OLD / 'final-state.json').read_bytes())
    raw = load_json_strict((OLD / 'final-candidate.json').read_bytes())
    session = previous.Task('receipts', replay_folder=replay_folder).initial_session()
    session.candidate = Candidate.create({r['path']: r['content_utf8'].encode('utf-8') for r in raw['files']},
                                         max_file_bytes=raw['max_file_bytes'])
    for key, value in state.items():
        if key != 'candidate_id':
            setattr(session, key, copy.deepcopy(value))
    session.diffs = {int(key): value for key, value in session.diffs.items()}
    session.restored_control_fields = tuple(session.restored_control_fields)
    session.parked_source_regions = tuple(tuple(row) for row in session.parked_source_regions)
    session.versions[session.candidate.candidate_id] = session.candidate
    session.__class__ = Session
    # All original state, including prior actual delivery and request provenance,
    # remains exact. New delivery is recorded only by the ordinary request loop.
    assert canonical_json_bytes(snapshot(session)) == canonical_json_bytes(state)
    assert previous.candidate_bytes(session.candidate) == (OLD / 'final-candidate.json').read_bytes()
    assert session.candidate.candidate_id == state['candidate_id']
    assert session.requests_used == INHERITED_REQUESTS and session.calls_used == INHERITED_OPERATIONS
    assert session.request_limit == MAX_REQUESTS and session.call_limit == MAX_OPERATIONS
    assert session.starting_archive_length == 0 and not session.submitted and not session.delivery_blocked
    assert session.ranges == [] and session.saved == {} and session.delivered_sources == []
    assert session.working_account()['written_during_request'] == 3
    assert not session.edit_checks and session.check_state() is None
    session.observations = ObservationStore((replay_folder or AREA / 'unexecuted') / 'observations',
                                          replay=replay_folder is not None)
    return session


@lru_cache(maxsize=1)
def response_constraints():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert sha256_file(path) == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('operational_schema_converter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(grammar=with_thinking(operational_reply.reply_grammar(DESCRIPTIONS, module.SchemaConverter)))


def expected_native(request):
    assert request['grammar'] == response_constraints()['grammar'] and 'response_format' not in request
    envelope = copy.deepcopy(request)
    # Grammar is a decoder constraint, not text rendered by the native template.
    # Adjust only that constraint to reuse the parent's exact template verification.
    envelope['grammar'] = previous.response_constraints()['grammar']
    return previous.expected_native(envelope)


def decode_reply(content):
    return operational_reply.decode_reply(content, DESCRIPTIONS)


def implementation_identities():
    inherited = previous.Task('receipts').source_identities()
    original = load_json_strict((OLD / 'RESPONSE_SEAL.json').read_bytes())['source_sha256']
    assert all(inherited.get(name) == digest for name, digest in original.items()), 'Original source closure changed'
    paths = [ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/NATIVE_GBNF_ORDER_PROBE.json',
             *AREA.glob('*.py'), AREA / 'PLAN.md', AREA / 'SPEC.md', AREA / 'SYSTEM.txt',
             AREA / 'DESIGN_REVIEW.md', *sorted((AREA / 'tests').glob('*.py')),
             *sorted(AREA.glob('*TESTS*.log'))]
    return {**inherited, **checkpoint_bindings(),
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


class Task(previous.Task):
    def __init__(self, version='001', replay_folder=None):
        if not isinstance(version, str) or len(version) != 3 or not version.isdigit():
            raise ValueError('version must be three decimal digits')
        super().__init__('receipts', version, replay_folder)
        self.AREA = AREA
        self.PACKAGE, self.RUN = AREA / f'preparation-{version}', AREA / f'run-{version}'
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{version}.json'

    def initial_session(self):
        return restore(self.replay_folder)

    def initial_preceding_feedback(self):
        return initial_preceding_feedback()

    def reply_schema(self):
        return operational_reply.reply_schema(DESCRIPTIONS)

    def operating_reference(self):
        return operational_reply.operating_reference(super().operating_reference())

    def response_constraints(self):
        return response_constraints()

    def expected_native(self, request):
        return expected_native(request)

    def implementation_identities(self):
        return implementation_identities()

    def source_identities(self):
        return implementation_identities()

    def __getattr__(self, name):
        return globals()[name] if name in globals() else super().__getattr__(name)


def __getattr__(name):
    return getattr(previous, name)
