"""Exact constructed closure entries over the existing prior-work/capture host.

The task instance owns its entry; no shared host or other task globals change.
Construction imports recorded bytes. It never reruns a historical operation.
"""
import copy
import importlib.util
import re
from pathlib import Path

import bootstrap
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

ROOT, AREA = bootstrap.ROOT, Path(__file__).resolve().parent
CORE_PATH = ROOT / 'development/workload_requalification/ecological_observation_entry/ecological_task.py'
spec = importlib.util.spec_from_file_location('closure_entry_shared_api', CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
host, bridge = core.host, core.capture_bridge
CASES = {
    'E14-CLOSURE-MINT': 'c63cd2d3aa1aa7e9111b74d5a6a1a9fd104d2d7fc3c1acd3a44637f2d7167868',
    'E14-STALE-SABLE': '502e49db84876bc73ae5683e6e63003e6d22f2ab48cf1ded9a6d3b3e8ff4d77e',
}
MAX_REQUESTS, MAX_OPERATIONS, FILE_LIMIT, SEED = 8, 24, 24000, 173205
ACTOR = dict(host.ACTOR)
DESCRIPTIONS = {'public': 'Execute the original active Phase B public checker on the current candidate. A current pass is required for submission; its scope does not expand to every task obligation.'}


class Session(bridge.Session):
    assessment_api = core.case_reports

    def __init__(self, *args, entry_case, original_observations, active_step, **kwargs):
        self.entry_case = entry_case
        self.active_step = active_step
        self._original_observations = tuple(canonical_json_bytes(r) for r in original_observations)
        super().__init__(*args, retain_imported_captures=True, **kwargs)

    def summary(self, sequence):
        row = super().summary(sequence)
        # Original receipts store extents at the result root. The current host
        # stores them under `source`; project the old mechanical facts without
        # rewriting history or granting authority from absent source bodies.
        if sequence <= self.starting_archive_length:
            pair = self.pairs[sequence - 1]
            result = pair['result']
            if pair['response']['action'] == 'read' and result.get('accepted'):
                first, last = result.get('returned_start_line'), result.get('returned_end_line')
                if type(first) is int and type(last) is int:
                    row['returned_range'] = dict(start_line=first, end_line=last)
                    row['historical_acquisition'] = dict(
                        reached_file_end=result.get('complete') is True and result.get('next_start_line') is None,
                        whole_file_returned=first == 1 and result.get('complete') is True and result.get('next_start_line') is None,
                        does_not_establish_current_visibility=True)
        return row

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['active_user_authored_step'] = self.active_step
        value['episode_annotation'] = (
            'This is the original constructed Phase B entry. Phase A is complete. '
            'The five prior_work actions are recorded setup before this contribution, not new actions. '
            'The current candidate is their saved successor. The full task is preserved; the active '
            'Phase B assignment defines the work now. Historical checks and observations retain '
            'their original bindings. Retrieval does not rerun them. No prior conversation, thinking, '
            'source body or result body is present unless explicitly displayed. The allowance '
            'counts only new requests and operations in this contribution.')
        value['imported_observations']['scope'] = (
            'Original constructed-entry observations; immutable historical evidence, not newly executed checks.')
        return value


class Task:
    ACTOR, SEED = ACTOR, SEED
    MAX_REQUESTS, MAX_OPERATIONS = MAX_REQUESTS, MAX_OPERATIONS
    AREA = AREA
    OWNER_DIRECTION = 'Continue the authorized original-workload requalification with the two constructed closure entries.'
    read = staticmethod(core.read)
    candidate_bytes = staticmethod(host.candidate_bytes)
    process_reply = staticmethod(host.process_reply)
    present_receipts = staticmethod(core.navigation.present_receipts)
    operating_reference = staticmethod(core.operating_reference)
    # Argument forms do not depend on prose descriptions. Preserve the qualified
    # converter and decoder rather than introducing another reply format.
    reply_schema = staticmethod(core.reply_schema)
    decode_reply = staticmethod(core.decode_reply)
    response_constraints = staticmethod(core.response_constraints)
    expected_native = staticmethod(core.expected_native)

    def __init__(self, case, version='001', replay_folder=None):
        if case not in CASES or re.fullmatch(r'[0-9]{3}', version) is None:
            raise ValueError('Unknown closure entry or noncanonical version')
        self.CASE, self.STARTING_ID, self.version = case, CASES[case], version
        self.entry = AREA / 'entries' / case
        self.PACKAGE, self.RUN = (AREA / f'{prefix}-{case}-{version}' for prefix in ('preparation', 'run'))
        self.MANIFEST = AREA / f'EXECUTION_MANIFEST-{case}-{version}.json'
        self.replay_folder = Path(replay_folder) if replay_folder is not None else None
        self.proof = self.read(self.entry / 'RECONCILIATION.json')
        if self.proof['status'] != 'exact_consumed_boundary_reconciled' or self.proof['candidate_id'] != self.STARTING_ID:
            raise ValueError('Closure entry reconciliation differs')
        self.PUBLIC_SHA = sha256_bytes(self.public_checker())

    def exact(self, relative):
        path = (self.entry / relative).resolve()
        if not path.is_relative_to(self.entry.resolve()) or relative not in self.proof['files']:
            raise ValueError('Unrecorded closure entry address')
        raw = path.read_bytes()
        if sha256_bytes(raw) != self.proof['files'][relative]:
            raise ValueError('Reconciled entry bytes changed: ' + relative)
        return raw

    def starting_files(self):
        value = load_json_strict(self.exact('candidate.json'))
        files = {r['path']: self.exact('candidate/' + r['path']) for r in value['files']}
        if files != {r['path']: r['content_utf8'].encode() for r in value['files']}:
            raise ValueError('Entry snapshot and exact files differ')
        return files

    def starting_candidate(self):
        value = Candidate.create(self.starting_files(), max_file_bytes=FILE_LIMIT)
        if value.candidate_id != self.STARTING_ID:
            raise ValueError('Entry candidate differs')
        return value

    def inherited_pairs(self):
        pairs = load_json_strict(self.exact('pairs.json'))
        if len(pairs) != 5 or sha256_bytes(canonical_json_bytes(pairs)) != self.proof['binding']['event_prefix_sha256']:
            raise ValueError('Original five-operation prefix differs')
        return pairs

    def public_checker(self):
        return self.exact('public.py')

    def hidden_checker(self):
        return self.exact('hidden.py')

    def task_text(self):
        return self.exact('TASK.txt').decode()

    def imports(self):
        original = load_json_strict(self.exact('observations.json'))
        transport, bodies = {}, {}
        for row in original:
            raw = self.exact('observations/' + row['handle'] + '.json')
            if len(raw) != row['size_bytes'] or sha256_bytes(raw) != row['sha256'] or canonical_json_bytes(load_json_strict(raw)) != raw:
                raise ValueError('Original observation extent or bytes differ')
            # Checks use checked_candidate_id, probes use candidate_id. Their
            # original manifest/body are already reconciled, never rebound here.
            transport[row['handle']] = {**row, 'action': 'capture'}
            bodies[row['handle']] = raw
        return original, transport, bodies

    def original_observation_state(self, session=None):
        original = self.imports()[0]
        if session is not None and tuple(canonical_json_bytes(r) for r in original) != session._original_observations:
            raise ValueError('Original observation provenance changed')
        return dict(schema='constructed-closure-observations-v1', entry_case=self.CASE,
            rows=original, transport_normalization=dict(changed_fields=['action'], transport_action='capture',
            effect='Transport classification only; exact original records and bindings are unchanged.'))

    original_observation_snapshot = original_observation_state

    def initial_session(self):
        original, transport, bodies = self.imports()
        folder = self.replay_folder or AREA / 'unexecuted' / self.CASE
        session = Session(self.starting_candidate(), {'public': self.public_checker()}, self.task_text(),
            pairs=self.inherited_pairs(), edit_checks={}, call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS,
            observations=ObservationStore(folder / 'observations', replay=self.replay_folder is not None),
            check_contracts={'public': {'checker_sha256': self.PUBLIC_SHA}}, entry_case=self.CASE,
            original_observations=original, active_step=self.exact('ACTIVE_STEP.txt').decode(),
            imported_observations=transport, imported_bodies=bodies)
        assert session.starting_archive_length == 5 and session.calls_used == session.requests_used == 0
        assert not session.ranges and not session.saved and not session.delivered_sources and not session.last
        assert session.working_account() is None and not session.submitted
        return session

    def initial_preceding_feedback(self):
        return []

    def snapshot(self, session):
        return {**host.snapshot(session), 'source_versions': [load_json_strict(host.candidate_bytes(v))
            for _, v in sorted(session.versions.items())], 'imported_capture_state': bridge.capture_snapshot(session),
            'original_observation_state': self.original_observation_state(session)}

    def candidate_from_snapshot(self, value):
        if set(value) != {'candidate_id', 'max_file_bytes', 'files'} or value['max_file_bytes'] != FILE_LIMIT:
            raise ValueError('Checkpoint candidate shape differs')
        files = {r['path']: r['content_utf8'].encode() for r in value['files']}
        candidate = Candidate.create(files, max_file_bytes=FILE_LIMIT)
        if (len(files) != len(value['files']) or set(files) != set(self.starting_files())
                or candidate.candidate_id != value['candidate_id'] or host.candidate_bytes(candidate) != canonical_json_bytes(value)):
            raise ValueError('Checkpoint candidate identity or inventory differs')
        return candidate

    def restore(self, state, candidate, replay_folder=None, replay=False):
        if not isinstance(candidate, Candidate):
            candidate = self.candidate_from_snapshot(candidate)
        task = Task(self.CASE, self.version, replay_folder if replay else None)
        session = task.initial_session()
        if (set(state) != set(self.snapshot(session)) or state['candidate_id'] != candidate.candidate_id
                or state['starting_archive_length'] != 5 or state['pairs'][:5] != self.inherited_pairs()
                or not 5 <= len(state['pairs']) <= 5 + MAX_OPERATIONS
                or (state['request_limit'], state['call_limit']) != (MAX_REQUESTS, MAX_OPERATIONS)
                or type(state['requests_used']) is not int or not 0 <= state['requests_used'] <= MAX_REQUESTS
                or state['original_observation_state'] != self.original_observation_state(session)):
            raise ValueError('Checkpoint ancestry, opportunity or provenance differs')
        bridge.restore_capture_state(session, state['imported_capture_state'])
        versions = [self.candidate_from_snapshot(v) for v in state['source_versions']]
        version_map = {v.candidate_id: v for v in versions}
        if (len(versions) != len(version_map) or self.STARTING_ID not in version_map
                or host.candidate_bytes(version_map[self.STARTING_ID]) != host.candidate_bytes(self.starting_candidate())
                or candidate.candidate_id not in version_map
                or host.candidate_bytes(version_map[candidate.candidate_id]) != host.candidate_bytes(candidate)):
            raise ValueError('Checkpoint source versions differ')
        for key, value in state.items():
            if key not in ('candidate_id', 'source_versions', 'imported_capture_state', 'original_observation_state'):
                setattr(session, key, copy.deepcopy(value))
        session.candidate, session.versions = candidate, version_map
        expected = {str(i): p['result']['applied_diff'] for i, p in enumerate(session.pairs, 1)
            if i > 5 and p['response']['action'] in ('patch', 'replace_region') and p['result'].get('accepted')}
        if {str(k): v for k, v in session.diffs.items()} != expected:
            raise ValueError('Checkpoint new-operation diffs differ')
        session.diffs = {int(k): v for k, v in expected.items()}
        session.restored_control_fields = tuple(session.restored_control_fields)
        session.parked_source_regions = tuple(tuple(r) for r in session.parked_source_regions)
        if canonical_json_bytes(self.snapshot(session)) != canonical_json_bytes(state):
            raise ValueError('Checkpoint exact reconstruction differs')
        return session

    def attach_observations(self, session, folder, log):
        target, custody = Path(folder).resolve(), Path(log.path).parent.resolve()
        if not target.is_relative_to(custody):
            raise ValueError('Observation custody outside run')
        prefix = target.relative_to(custody).as_posix()
        prefix = '' if prefix == '.' else prefix + '/'
        original, transport, bodies = self.imports()
        assert bridge.capture_snapshot(session)['inventory'] == list(transport.values())
        store = ArtifactStore(custody)
        artifacts = [store.put(prefix + 'imported-captures/' + n, canonical_json_bytes(v)) for n, v in (
            ('original-rows.json', original), ('transport-inventory.json', transport),
            ('original-provenance.json', self.original_observation_state(session)))]
        artifacts += [store.put(prefix + 'imported-captures/' + h + '.json', b) for h, b in bodies.items()]
        log.append('imported_capture_custody', dict(records=len(bodies), actor_acquisitions=0,
            retrieval_only=True, source_edit_authority=False, applicable_check_authority=False), artifacts)
        def preserved(record, artifacts):
            log.append('check_observation_preserved', record,
                [{**r, 'path': prefix + 'observations/' + r['path']} for r in artifacts])
        session.observations = ObservationStore(target / 'observations', on_preserved=preserved)

    def source_identities(self):
        paths = [CORE_PATH, *AREA.glob('*.py'), *(AREA/'tests').glob('*.py'), *(AREA/'review').glob('*.py'),
            *AREA.glob('*TESTS*.log'), *(AREA/n for n in ('PLAN.md', 'SPEC.md', 'SYSTEM.txt')),
            self.entry/'RECONCILIATION.json']
        for name in ('compiler_entry', 'ecological_observation_entry', 'action_lifecycle', 'navigation_continuity', 'search_continuity', 'small_repairs'):
            paths.extend((ROOT/'development/workload_requalification'/name).glob('*.py'))
        result = {**host.source_identities(), **self.proof['original_sources'],
            **{(self.entry/n).relative_to(ROOT).as_posix(): h for n, h in self.proof['files'].items()},
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}
        host.verify_sources(result)
        return result

    implementation_identities = source_identities

    def __getattr__(self, name):
        return getattr(host, name)
