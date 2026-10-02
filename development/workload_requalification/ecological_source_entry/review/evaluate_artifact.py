"""Post-seal evaluator execution; never enters the actor or changes sealed work."""
import ast
import difflib
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import ecological_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.observations import ObservationStore


def signatures(body):
    return [(node.name, ast.dump(node.args, include_attributes=False))
            for node in ast.walk(ast.parse(body.decode('utf-8')))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def main():
    run = AREA / 'run-002'
    seal = run / 'RESPONSE_SEAL.json'
    seal_before = seal.read_bytes()
    before = study.starting_candidate()
    candidate_raw = (run / 'final-candidate.json').read_bytes()
    candidate = study.candidate_from_snapshot(study.read(run / 'final-candidate.json'))
    assert study.candidate_bytes(candidate) == candidate_raw
    original, final = dict(before.files), dict(candidate.files)
    changed = [path for path in original if original[path] != final[path]]
    assert set(changed) == {study.TARGET, study.REOPEN}
    assert len(original) == len(final) == 25
    assert all(signatures(original[path]) == signatures(final[path]) for path in changed)
    out = AREA / 'review/evaluation-002'
    out.mkdir(exist_ok=False)
    diffs = {}
    for path in changed:
        diff = ''.join(difflib.unified_diff(original[path].decode().splitlines(keepends=True),
            final[path].decode().splitlines(keepends=True), fromfile=path, tofile=path))
        diffs[path] = diff
        (out / (Path(path).name + '.patch')).write_bytes(diff.encode())
    hidden = study.hidden_checker()
    store = ObservationStore(out / 'observations')
    observation = store.execute(candidate, hidden, 'hidden', 'CHK-0001')
    assert store.read('CHK-0001') == observation
    assert observation['passed'] and observation['capture_complete']
    assert seal.read_bytes() == seal_before
    assert (run / 'final-candidate.json').read_bytes() == candidate_raw
    result = dict(status='post_seal_hidden_pass_and_exact_artifact_comparison',
        evaluator_executed=True, actor_feedback=False, additional_model_or_native_calls=False,
        response_seal_sha256=sha256_bytes(seal_before), candidate_id=candidate.candidate_id,
        original_candidate_id=before.candidate_id, hidden_checker_sha256=sha256_bytes(hidden),
        changed_paths=changed, untouched_files=23, public_function_signatures_unchanged=True,
        diffs=diffs, observation=observation,
        limits=['Hidden adds one-line extraction to the public boundary checks; it does not establish every preservation clause.',
                'Inline/hash-block/identifier preservation requires source review; semantic conclusions are not inferred from fingerprints.'])
    (out / 'RESULT.json').write_bytes(canonical_json_bytes(result))
    inventory = [dict(path=p.relative_to(out).as_posix(), size_bytes=p.stat().st_size,
                      sha256=sha256_bytes(p.read_bytes())) for p in sorted(out.rglob('*')) if p.is_file()]
    (out / 'SEAL.json').write_bytes(canonical_json_bytes(dict(
        response_seal_sha256=sha256_bytes(seal_before), artifacts=inventory)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
