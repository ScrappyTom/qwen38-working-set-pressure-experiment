"""One declared assisted two-phase continuation; no live semantic coaching."""
import argparse
import json
import time
from types import SimpleNamespace

import bootstrap
import saved_report_task as study
import qualification_route
from manage import RUNTIME, legacy, load_helper
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

runner = load_helper('saved_report_common_runner', 'scripts/run_uncoached_contribution.py')
INITIAL_KEYS = ('prompt_tokens', 'request_sha256', 'native_sha256', 'wire_request_sha256')


class PhaseLoop(runner.Loop):
    def setup(self, session, phase):
        before = study.snapshot(session)
        self.log.append('assisted_phase_setup_started', dict(phase=phase, completion_sent=False),
            [self.store.put(f'setup/P{phase}-before-state.json', canonical_json_bytes(before))])

        def record(sequence, action, result):
            self.log.append('assisted_acquisition', dict(phase=phase, sequence=sequence,
                model_action=False, completion_sent=False),
                [self.store.put(f'setup/P{phase}-O{sequence:03d}.json',
                    canonical_json_bytes(dict(action=action, result=result)))])
            self.snapshot(session, f'setup/P{phase}-O{sequence:03d}')

        rows = study.setup(session, phase, self.measure, self.task.preceding_feedback, record)
        self.snapshot(session, f'setup/P{phase}')
        self.log.append('assisted_phase_setup_completed', dict(phase=phase,
            sequences=rows, phase_counters=session.phase_counters(), completion_sent=False), [])
        return rows

    def execute(self, session):
        started = time.monotonic()
        self.snapshot(session, 'starting')
        self.setup(session, 1)
        disposition = 'phase_request_allowance_exhausted'
        while self.sent < self.task.MAX_REQUESTS:
            if self.stop_requested():
                disposition = 'operator_stopped'
                break
            if session.delivery_blocked:
                disposition = 'feedback_capacity_denied'
                break
            if not session.phase_budget_available():
                disposition = 'phase_request_or_operation_allowance_exhausted'
                break
            self.invoke(session)
            if session.submitted:
                disposition = 'checked_submission'
                break
            if session.early_phase_one_submit:
                disposition = 'phase_one_early_submission_attempt'
                break
            if self.no_operation:
                disposition = 'actor_stopped_without_operation'
                break
            if session.transition_ready():
                self.snapshot(session, 'transition/P1')
                self.log.append('declared_working_context_restart', dict(
                    candidate_id=session.candidate.candidate_id, phase_counters=session.phase_counters(),
                    preceding_check_sequence=len(session.pairs), semantic_assessment_used=False,
                    assisted=True, prior_thinking_reintroduced=False), [])
                self.setup(session, 2)
        self.snapshot(session, 'final')
        result = dict(disposition=disposition, sent_requests=self.sent,
            actual_operations=session.calls_used, archival_operations=len(session.pairs),
            phase_counters=session.phase_counters(), candidate_id=session.candidate.candidate_id,
            current_check=session.check_state(), submitted=session.submitted,
            task_loop_seconds=time.monotonic()-started,
            classification='assisted two-phase saved-work continuation; no live coaching')
        self.log.append('task_loop_completed', result, [])
        return result


def verify_package(module):
    manifest = module.read(module.MANIFEST)
    seal = module.read(module.PACKAGE/'SEAL.json')
    assert seal['status'] == 'qualified_no_model_inference' and seal['completion_requests'] == 0
    assert sha256_file(module.PACKAGE/'SEAL.json') == manifest['preparation_seal_sha256']
    assert sha256_bytes(canonical_json_bytes(seal['files'])) == seal['aggregate_sha256']
    for row in seal['files']:
        path = module.PACKAGE/row['path']
        assert path.stat().st_size == row['size_bytes'] and sha256_file(path) == row['sha256'], row['path']
    module.verify_sources(manifest['source_sha256'])
    assert manifest['source_sha256'] == module.source_identities() == seal['source_sha256']
    assert manifest['actor'] == module.ACTOR and manifest['seed'] == module.SEED
    assert manifest['maximum_requests'] == module.MAX_REQUESTS
    assert manifest['maximum_operations'] == module.MAX_OPERATIONS
    assert manifest['phase_request_limit'] == study.PHASE_REQUESTS
    assert manifest['phase_actor_operation_limit'] == study.PHASE_ACTOR_OPERATIONS
    assert (module.PACKAGE/'starting-candidate.json').read_bytes() == module.candidate_bytes(module.initial_session().candidate)
    assert sha256_file(module.PACKAGE/'initial-wire-request.json') == manifest['initial']['wire_request_sha256']
    return manifest


def prepare(module):
    folder = module.PACKAGE
    folder.mkdir(exist_ok=False)
    bound = module.source_identities()
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder/'records.jsonl', 'saved-report-preparation', task_module=module)
    session, adapter = module.initial_session(), runner.Adapter(module)
    initial, routes, error = None, None, None
    try:
        module.attach_observations(session, folder, log)
        server, model, _ = module.runtime_paths()
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = PhaseLoop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(bound))
            loop.snapshot(session, 'starting')
            loop.setup(session, 1)
            request = adapter.request_for(session.view())
            count = loop.measure(session.view())
            assert count <= 23808
            selected = loop.cache[sha256_bytes(canonical_json_bytes(request))]
            initial = {key: selected[key] for key in INITIAL_KEYS}
            store.put('initial-wire-request.json', completion_request_bytes(request))
            loop.snapshot(session, 'initial')
            # Decoder/template/effort are inherited byte-identically. This port
            # changes phase semantics, not reply forms; bind the actual prior proof.
            previous = study.compiler.AREA/'preparation-003'
            assert module.response_constraints() == study.compiler.response_constraints()
            store.put('INHERITED_REPLY_QUALIFICATION.json', canonical_json_bytes(dict(
                grammar_sha256=sha256_bytes(module.response_constraints()['grammar'].encode()),
                prior_seal_sha256=sha256_file(previous/'SEAL.json'),
                prior_cases=study.read(previous/'QUALIFICATION.json')['native_forms'],
                new_reply_forms=False)))
            routes = qualification_route.qualify(module, loop, adapter, store, folder)
            assert session.requests_used == 0 and session.candidate.candidate_id == study.STARTING_ID
            module.verify_sources(bound)
    except BaseException as exc:
        error = exc
        study.save(folder, 'FAILED.json', dict(type=type(exc).__name__, message=str(exc)))
    finally:
        study.save(folder, 'QUALIFICATION.json', dict(initial=initial, routes=routes,
            completion_requests=0, actor=module.ACTOR, maximum_requests=module.MAX_REQUESTS,
            maximum_operations=module.MAX_OPERATIONS, classification='assisted saved-work port qualification',
            memory=RUNTIME.memory_stats(folder/'memory.csv'), port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound, completion_requests=0)
    if error:
        raise error
    study.save(module.AREA, module.MANIFEST.name, dict(actor=module.ACTOR, seed=module.SEED,
        maximum_requests=module.MAX_REQUESTS, maximum_operations=module.MAX_OPERATIONS,
        phase_request_limit=study.PHASE_REQUESTS, phase_actor_operation_limit=study.PHASE_ACTOR_OPERATIONS,
        maximum_archival_operations=44, supplied_operations=12, source_sha256=bound,
        preparation_seal_sha256=sha256_file(folder/'SEAL.json'), initial=initial,
        owner_direction=study.OWNER_DIRECTION, no_live_coaching=True, automatic_retry=False,
        classification='assisted two-phase saved-work continuation'))
    verify_package(module)
    print(json.dumps(dict(status='qualified', initial=initial, routes=routes, completion_requests=0)), flush=True)


def run_once(module):
    manifest = verify_package(module)
    assert not module.RUN.exists(), 'Attempt exists; no retry'
    module.RUN.mkdir()
    store = ArtifactStore(module.RUN)
    log = runner.RunLog(module.RUN/'records.jsonl', 'saved-report-current-host', task_module=module)
    log.append('attempt_reserved', dict(owner_direction=study.OWNER_DIRECTION,
        manifest_sha256=sha256_file(module.MANIFEST)),
        [store.put('EXECUTION_MANIFEST.json', module.MANIFEST.read_bytes()),
         store.put('SPEC.md', (module.AREA/'SPEC.md').read_bytes())])
    session, adapter = module.initial_session(), runner.Adapter(module)
    module.attach_observations(session, module.RUN, log)
    server, model, _ = module.runtime_paths()
    args = SimpleNamespace(server=server, model=model, output=module.RUN)
    outcome, error = None, None
    try:
        with RUNTIME.owned_runtime(args, store, log) as url:
            loop = PhaseLoop(module.RUN, store, log, url=url, task_module=adapter,
                source_check=lambda: module.verify_sources(manifest['source_sha256']), initial=manifest['initial'])
            outcome = loop.execute(session)
            loop.health()
    except BaseException as exc:
        error = exc
        log.append('attempt_stopped', dict(type=type(exc).__name__, message=str(exc)), [])
        for name, value in (('stopped-state.json', module.snapshot(session)),
                            ('stopped-candidate.json', module.candidate_bytes(session.candidate)),
                            ('stopped-preceding-feedback.json', adapter.preceding_feedback)):
            store.put(name, value if isinstance(value, bytes) else canonical_json_bytes(value))
    finally:
        records = verify_records(module.RUN/'records.jsonl', module.RUN)
        files = RUNTIME.file_inventory(module.RUN)
        seal = dict(disposition='stopped_without_retry' if error else outcome['disposition'],
            actor=module.ACTOR, source_sha256=manifest['source_sha256'], files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), record_count=len(records),
            sent_requests=sum(row['record_type']=='invocation_started' for row in records),
            returned_responses=sum(row['record_type']=='response_received' for row in records),
            processed_invocations=sum(row['record_type']=='invocation_completed' for row in records),
            actual_operations=session.calls_used, archival_operations=len(session.pairs),
            phase_counters=session.phase_counters(), memory=RUNTIME.memory_stats(module.RUN/'memory.csv'),
            runtime=RUNTIME.runtime_evidence(module.RUN/'private-runtime/server.stderr.log'),
            port_free=RUNTIME.port_free(RUNTIME.PORT),
            private_runtime_files_local_only={p.name:sha256_file(p)
                for p in (module.RUN/'private-runtime').glob('*') if p.is_file()})
        store.put('RESPONSE_SEAL.json', canonical_json_bytes(seal))
    if error:
        raise error
    print('Closed: '+outcome['disposition'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare','run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = study.Task(args.version)
    prepare(module) if args.mode == 'prepare' else run_once(module)
