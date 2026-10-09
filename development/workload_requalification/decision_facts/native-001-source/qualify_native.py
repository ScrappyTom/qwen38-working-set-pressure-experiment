"""Measure real ORBIT projections and its saved recovery choice; no completion."""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

AREA = Path(__file__).resolve().parent
sys.path.insert(0, str(AREA.parent / 'recurrent_entries'))
import recurrent_task as original
import recurrent_session
import run_recurrent
from current_facts import CurrentFactsMixin, operating_reference
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


class Session(CurrentFactsMixin, recurrent_session.Session):
    pass


class Task(original.Task):
    def operating_reference(self):
        return operating_reference(super().operating_reference())


def qualify(version):
    folder = AREA / ('native-' + version)
    folder.mkdir(exist_ok=False)
    control = run_recurrent.configure()
    task, revised = original.Task(), Task()
    assert sha256_file(task.RUN / 'RESPONSE_SEAL.json') == '51caf0c0916c410df4fb5e2ba484f37a04ad5b009b4fa4ec6792df62ebe0abcc'
    bound = {**task.source_identities(), **{p.relative_to(task.ROOT).as_posix(): sha256_file(p)
        for p in [*AREA.glob('*.py'), *(AREA / 'tests').glob('*.py'), AREA / 'PLAN.md']}}
    store = ArtifactStore(folder)
    log = control.legacy.QualificationLog(folder / 'records.jsonl', 'decision-facts-native', task_module=task)
    log.append('qualification_initialized', dict(completion_requests=0,
        original_seal_sha256=sha256_file(task.RUN / 'RESPONSE_SEAL.json')), [])
    rows, error = [], None
    try:
        server, model, _ = task.runtime_paths()
        with control.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = control.runner.Loop(folder, store, log, url=url,
                task_module=control.runner.Adapter(task), source_check=lambda: task.verify_sources(bound))
            def restore(stem):
                return task.restore(task.read(task.RUN / (stem + '-state.json')),
                    task.read(task.RUN / (stem + '-candidate.json')), task.RUN, replay=True)
            for stem in ('after/C03-O01', 'after/C04-O01', 'after/C13-O01', 'after/C20-O01'):
                old = restore(stem)
                new = old.clone(); new.__class__ = Session
                before = canonical_json_bytes(task.snapshot(new))
                trial = dict(checkpoint=stem, counterfactual_only=True)
                for name, source, session in (('historical', task, old), ('projected', revised, new)):
                    adapter = control.runner.Adapter(source)
                    adapter.preceding_feedback[:] = task.read(task.RUN / (stem + '-preceding-feedback.json'))
                    loop.task = adapter
                    tokens = loop.measure(session.view())
                    trial[name] = dict(input_tokens=tokens, within_input_ceiling=tokens <= 23808,
                        required_source_delivery=session.view()['phase']['required_source_delivery'])
                assert canonical_json_bytes(task.snapshot(new)) == before
                rows.append(trial)
                if stem == 'after/C04-O01':
                    # Replay the actor's already-public C05 choice, not a new
                    # supplied route or claim about prospective model behavior.
                    assert trial['projected']['within_input_ceiling']
                    new.mark_delivered(new.view()); new.begin_request()
                    reply = task.read(task.RUN / 'calls/C05-reply.json')
                    outcome = revised.process_reply(new, reply, loop.measure, adapter.preceding_feedback)
                    count = loop.measure(new.view())
                    assert all(o['result']['accepted'] for o in outcome['operations'])
                    assert count <= 23808 and not new.recovery and not new.delivery_blocked
                    assert new.candidate.candidate_id == old.candidate.candidate_id
                    artifact = store.put('saved-recovery-choice.json', canonical_json_bytes(dict(reply=reply,
                        outcome=outcome, resulting_view=new.view(), input_tokens=count)))
                    log.append('saved_recovery_choice_replayed', dict(completion_sent=False), [artifact])
            task.verify_sources(bound)
    except BaseException as problem:
        error = problem
        log.append('qualification_failed', dict(type=type(problem).__name__, message=str(problem)), [])
    finally:
        artifacts = [store.put('RESULTS.json', canonical_json_bytes(dict(status='failed' if error else 'qualified',
            completion_requests=0, trials=rows, memory=control.RUNTIME.memory_stats(folder / 'memory.csv'),
            port_free=control.RUNTIME.port_free(control.RUNTIME.PORT))))]
        log.append('qualification_closed', dict(completion_requests=0), artifacts)
        verify_records(folder / 'records.jsonl', folder)
        control.legacy.seal(folder, 'failed_preserved' if error else 'qualified_no_model_inference', bound,
            completion_requests=0)
    if error:
        raise error
    print(canonical_json_bytes(dict(status='qualified', trials=rows)).decode(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    qualify(parser.parse_args().version)
