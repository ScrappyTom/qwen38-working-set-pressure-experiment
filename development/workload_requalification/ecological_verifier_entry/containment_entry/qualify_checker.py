"""Offline prospective checker qualification; no model calls or candidate writes."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import checker

AREA = Path(__file__).resolve().parent
TARGET = 'src/addressable_information_layer/verifiers.py'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def reference_source(source):
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_safe_relative_path')
    replacement = '''def _safe_relative_path(path_or_name: str) -> PurePosixPath | None:
    normalized = path_or_name.replace("\\\\", "/")
    path = PurePosixPath(normalized)
    if (path.is_absolute() or ".." in path.parts or not path.parts
            or any(re.match(r"^[A-Za-z]:", part) for part in path.parts)):
        return None
    return path'''
    old = ast.get_source_segment(source, fn)
    assert source.count(old) == 1
    return source.replace(old, replacement, 1)


def main():
    folder = AREA / 'checker-cpu-001'
    folder.mkdir(exist_ok=False)
    saved = checker.saved_candidate()
    files = {r['path']: r['content_utf8'] for r in saved['files']}
    original = files[TARGET]
    reference = reference_source(original)
    # Reference text is evaluation assistance, never an actor input or saved work.
    (folder/'REFERENCE-verifiers.py').write_text(reference, encoding='utf-8', newline='\n')
    variants = (
        ('saved_candidate', original, False),
        ('evaluator_reference', reference, True),
        ('reference_bad_timeout', reference.replace(
            'return max(1, min(timeout, MAX_COMMAND_TIMEOUT_SECONDS))',
            'return max(1, max(timeout, MAX_COMMAND_TIMEOUT_SECONDS))'), False),
        ('reference_rejects_valid_paths', reference.replace(
            '    return path\n', '    return None\n'), False),
    )
    program = checker.public_checker()
    (folder/'DECLARED_PUBLIC_CHECK.py').write_bytes(program)
    rows = []
    for name, source, expected_pass in variants:
        assert name == 'saved_candidate' or source != original
        with tempfile.TemporaryDirectory(prefix='verifier_contract_') as temp:
            root = Path(temp)
            for path, content in files.items():
                target = root/path
                assert target.resolve().is_relative_to(root.resolve())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source if path == TARGET else content, encoding='utf-8', newline='\n')
            path = root/'_qualified_check.py'
            path.write_bytes(program)
            start = time.monotonic()
            observed = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(path)], cwd=root,
                capture_output=True, timeout=90)
            for label, raw in (('stdout', observed.stdout), ('stderr', observed.stderr)):
                (folder/f'{name}-{label}.bin').write_bytes(raw)
            row = dict(name=name, source_sha256=digest(source.encode()), expected_pass=expected_pass,
                passed=observed.returncode == 0, returncode=observed.returncode,
                stdout_utf8=observed.stdout.decode('utf-8'), stderr_utf8=observed.stderr.decode('utf-8'),
                elapsed_seconds=time.monotonic()-start)
            rows.append(row)
            assert row['passed'] == expected_pass, row
    assert 'unsafe path component survived normalization' in rows[0]['stderr_utf8']
    assert './C:/outside.py' in rows[0]['stderr_utf8']
    assert rows[0]['stdout_utf8'].splitlines() == ['public passed', 'expanded verifier contract passed']
    assert 'path composition contract passed' in rows[1]['stdout_utf8']
    proof = dict(status='qualified_offline_no_model_inference', checker_sha256=digest(program),
        parent_checker_sha256=checker.PARENT_SHA, parent_seal_sha256=checker.OLD_SEAL,
        saved_candidate_id=saved['candidate_id'], original_saved_work_unchanged=checker.saved_candidate()==saved,
        unsafe_spellings=20, relative_controls=6, native_join_control_comparisons=12,
        rows=rows, model_requests=0, runtime_launches=0,
        source_sha256={p.name:digest(p.read_bytes()) for p in AREA.glob('*.py')},
        environment=dict(interpreter=sys.executable, cwd='fresh candidate root', imports='candidate src'),
        limits=['Reference repair is evaluator-authored and unexposed.',
                'No candidate artifact materialization or candidate command runs for unsafe paths.',
                'No live continuation, native model-input qualification or task completion is established.'])
    (folder/'RESULTS.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
