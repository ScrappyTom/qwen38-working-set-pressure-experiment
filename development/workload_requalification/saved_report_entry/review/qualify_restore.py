"""Prospective checkpoint qualification over the unchanged sealed live execution.

The original execution Task and verifier are loaded separately. Their operations,
native requests and snapshot serialization remain original; only reconstruction
is qualified through the prospective restorer. No source is represented as having
its former hash after it changes: frozen providers are explicit and authenticated.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import socket
import sys
from types import ModuleType
from unittest.mock import patch
import urllib.request

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import bootstrap  # noqa: F401
import saved_report_task as prospective
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ROOT = prospective.ROOT
REVIEW = AREA / 'review'
FROZEN = REVIEW / 'restore-qualification-001/frozen-sources'
ORIGINAL_VERIFIER = REVIEW / 'verify_run.py'
ORIGINAL_VERIFIER_SHA = '993656862a0e5c623c1b6fdf1b9bbaec8fddfec1665904d39756f2abf65fea64'
EXPECTED_FAILURE = 'checkpoint phase accounting or exact reconstruction differs'
TASK_PATH = (AREA / 'saved_report_task.py').relative_to(ROOT).as_posix()


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _source_sets(run):
    seal = prospective.read(run / 'RESPONSE_SEAL.json')
    manifest = prospective.read(run / 'EXECUTION_MANIFEST.json')
    original = seal['source_sha256']
    assert manifest['source_sha256'] == original
    index = prospective.read(FROZEN / 'INDEX.json')
    assert TASK_PATH in index and set(index) <= set(original)
    providers, identities = {}, {}
    for name, expected in original.items():
        if name in index:
            row = index[name]
            provider = (FROZEN / row['path']).resolve()
            assert provider.is_relative_to(FROZEN.resolve())
            assert row['sha256'] == expected
            role = 'archived_original'
        else:
            provider = (ROOT / name).resolve()
            assert provider.is_relative_to(ROOT.resolve())
            role = 'unchanged_current'
        actual = sha256_file(provider)
        assert actual == expected, ('Original execution provider differs', name)
        identities[name] = actual
        providers[name] = dict(role=role, path=provider.relative_to(ROOT).as_posix(), sha256=actual)
    assert identities == original
    current = prospective.Task('001').source_identities()
    assert set(current) == set(original), 'Prospective closure changes the source inventory'
    changed = {name: dict(original=original[name], prospective=current[name])
        for name in original if original[name] != current[name]}
    assert TASK_PATH in changed, 'No prospective Task repair is present'
    assert set(changed) <= set(index), 'An unqualified execution dependency changed'
    for name, digest in current.items():
        assert sha256_file(ROOT / name) == digest
    return seal, providers, identities, current, changed


def qualify(version='001'):
    if version != '001':
        raise ValueError('This qualification binds only the original closed run 001')
    run = AREA / 'run-001'
    if not (run / 'RESPONSE_SEAL.json').is_file():
        raise ValueError('Do not qualify an open run')
    assert sha256_file(ORIGINAL_VERIFIER) == ORIGINAL_VERIFIER_SHA, 'Original verifier changed'
    seal, providers, original_sources, prospective_sources, changed = _source_sets(run)
    old_raw = (ROOT / providers[TASK_PATH]['path']).read_bytes()
    frozen = ModuleType('saved_report_original_execution_task')
    # Keep the logical artifact boundary used by the original code, while binding
    # its actual executable bytes to the distinct archived provider below.
    frozen.__file__ = str(ROOT / TASK_PATH)
    sys.modules[frozen.__name__] = frozen
    exec(compile(old_raw, str(FROZEN / 'task.py'), 'exec'), frozen.__dict__)
    original_task = frozen.Task
    verifier = _load('saved_report_original_closed_verifier', ORIGINAL_VERIFIER)
    failures, checkpoints = [], {}

    def verified_original_identities():
        actual = {name: sha256_file(ROOT / row['path']) for name, row in providers.items()}
        assert actual == original_sources, 'Original execution provider changed during qualification'
        return actual

    class ExecutionTask(original_task):
        """Original execution plus an explicitly separate reconstruction audit."""
        def source_identities(self):
            return verified_original_identities()

        def implementation_identities(self):
            return verified_original_identities()

        def verify_sources(self, expected):
            assert expected == verified_original_identities()

        def restore(self, state, candidate, replay_folder=None, replay=False):
            assert replay is True and Path(replay_folder).resolve() == run.resolve()
            checkpoint = run / ('final-state.json' if (run / 'final-state.json').exists() else 'stopped-state.json')
            checkpoint_raw = checkpoint.read_bytes()
            assert load_json_strict(checkpoint_raw) == state
            try:
                frozen.restore(state, candidate, replay_folder, replay)
            except ValueError as error:
                assert str(error) == EXPECTED_FAILURE
                failures.append(dict(type=type(error).__name__, message=str(error),
                    frozen_task_sha256=sha256_bytes(old_raw),
                    checkpoint_path=checkpoint.relative_to(run).as_posix(),
                    checkpoint_raw_sha256=sha256_bytes(checkpoint_raw),
                    loaded_state_canonical_sha256=sha256_bytes(canonical_json_bytes(state))))
            else:
                raise AssertionError('Original reconstruction failure was not reproduced')
            # This is not an operation replay or an assertion bypass. The
            # prospective restorer must satisfy the verifier's subsequent
            # model-view equality and all observation/runtime assertions.
            return prospective.restore(state, candidate, replay_folder, replay)

    frozen.Task = ExecutionTask

    def qualify_checkpoint(frame):
        local = frame.f_locals
        stem, session = local['stem'], local['session']
        assert Path(local['run']).resolve() == run.resolve()
        path = run / (stem + '-state.json')
        raw = path.read_bytes()
        assert canonical_json_bytes(frozen.snapshot(session)) == raw
        state = load_json_strict(raw)
        restored = prospective.restore(state, session.candidate, run, replay=True)
        assert restored.observations.replay is True
        # Preserve the old physical serialization, not merely normalized map
        # equality, while comparing every reconstructed field and model view.
        assert canonical_json_bytes(frozen.snapshot(restored)) == raw
        assert canonical_json_bytes(prospective.snapshot(restored)) == raw
        assert frozen.candidate_bytes(restored.candidate) == frozen.candidate_bytes(session.candidate)
        assert canonical_json_bytes(restored.view()) == canonical_json_bytes(session.view())
        assert restored.phase_counters() == session.phase_counters()
        assert restored.working_account() == session.working_account()
        assert restored.diffs == session.diffs and all(type(key) is int for key in restored.diffs)
        assert restored.pairs == session.pairs
        for sequence in range(1, len(session.pairs)+1):
            for kind in ('EVT', 'RES'):
                handle = f'{kind}-{sequence:04d}'
                assert restored.payload(handle) == session.payload(handle), (stem, handle)
        row = dict(path=path.relative_to(run).as_posix(), sha256=sha256_bytes(raw),
            candidate_id=session.candidate.candidate_id, archived_operations=len(session.pairs),
            diff_addresses=sorted(session.diffs), phase_counters=session.phase_counters(),
            account_action_handle=(restored.working_account() or {}).get('action_handle'),
            exact_old_snapshot_bytes=True, model_view_equal=True,
            candidate_equal=True, account_equal=True, phase_counters_equal=True,
            every_archived_action_and_result_payload_equal=True)
        if stem in checkpoints:
            assert checkpoints[stem] == row
        checkpoints[stem] = row

    def profile(frame, event, arg):
        if (event == 'return' and frame.f_code.co_name == 'state_only'
                and Path(frame.f_code.co_filename).resolve() == ORIGINAL_VERIFIER.resolve()):
            qualify_checkpoint(frame)

    if sys.getprofile() is not None:
        raise ValueError('Do not replace an existing profiler during qualification')
    prohibited = AssertionError('No subprocess, model, checker or native endpoint during qualification')
    with patch.object(verifier, 'study', frozen), \
            patch('subprocess.Popen', side_effect=prohibited), \
            patch.object(urllib.request, 'urlopen', side_effect=prohibited), \
            patch.object(socket.socket, 'connect', side_effect=prohibited), \
            patch.object(socket.socket, 'connect_ex', side_effect=prohibited):
        sys.setprofile(profile)
        try:
            replay = verifier.verify(version)
        finally:
            sys.setprofile(None)

    assert len(failures) == 1 and replay['status'] == 'replayed_exactly'
    assert {row['path'] for row in checkpoints.values()} == {
        path.relative_to(run).as_posix() for path in run.rglob('*-state.json')}
    assert verified_original_identities() == original_sources
    assert prospective.Task(version).source_identities() == prospective_sources
    assert sha256_file(ORIGINAL_VERIFIER) == ORIGINAL_VERIFIER_SHA
    log = AREA / 'private-runtime/VERIFY-001.log'
    if log.is_file():
        assert EXPECTED_FAILURE.encode() in log.read_bytes()
    return dict(status='prospective_restorer_qualified_against_original_execution',
        classification='Offline apparatus repair qualification; not a new model run or original-source verification success',
        original_restore_failed=failures[0], prospective_restore_passed=True,
        original_failed_verifier_log_sha256=sha256_file(log) if log.is_file() else None,
        original_response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        original_response_file_inventory_aggregate=seal['aggregate_sha256'],
        frozen_source_index_sha256=sha256_file(FROZEN / 'INDEX.json'),
        original_execution_source_sha256=original_sources,
        original_execution_source_providers=providers,
        prospective_reconstruction_source_sha256=prospective_sources,
        changed_source_bindings=changed,
        original_verifier_source_sha256=ORIGINAL_VERIFIER_SHA,
        qualification_source_sha256=sha256_file(Path(__file__)),
        original_execution_replay=replay,
        checked_checkpoint_count=len(checkpoints),
        checkpoints=[checkpoints[stem] for stem in sorted(checkpoints)],
        original_execution_functions_replayed=True,
        original_snapshot_serialization_preserved=True,
        original_failure_preserved=True,
        no_original_source_or_run_mutation=True,
        no_additional_checker_execution=True, no_additional_model_inference=True,
        no_additional_native_requests=True, no_subprocess_execution=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = qualify(args.version)
    output = args.output or REVIEW / 'restore-qualification-001/QUALIFICATION.json'
    raw = canonical_json_bytes(value)
    if output.exists():
        assert output.read_bytes() == raw, 'Preserve the preceding qualification outcome'
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
    print(canonical_json_bytes(dict(status=value['status'],
        checked_checkpoints=value['checked_checkpoint_count'],
        original_restore_failure=value['original_restore_failed']['message'],
        prospective_restore_passed=value['prospective_restore_passed'])).decode())
