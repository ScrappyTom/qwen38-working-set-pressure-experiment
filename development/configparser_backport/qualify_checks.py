"""Qualify actual baseline checks in the host's isolated subprocess; no inference."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import configparser_backport as task
from working_set_exp.candidate import Candidate
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file

OUTPUT = task.AREA / "baseline-checks-001"


def main():
    if OUTPUT.exists():
        raise FileExistsError("preserve existing baseline qualification")
    OUTPUT.mkdir()
    status = "incomplete"
    try:
        candidate = Candidate.create(task.verified_files(), max_file_bytes=task.FILE_LIMIT)
        for label, upstream in (("upstream", True), ("complete", False)):
            checker = task.checker(upstream_only=upstream)
            (OUTPUT / (label + "-checker.py")).write_bytes(checker)
            result = run_checker(candidate, checker)
            (OUTPUT / (label + "-result.json")).write_bytes(canonical_json_bytes(result))
            assert not result["streams_truncated"], "baseline diagnostic exceeded the output allowance"
            body = load_json_strict(result["stdout"].encode())
            assert body["upstream"]["successful"] and body["upstream"]["tests"] > 0, result
            if upstream:
                assert result["passed"], result
            else:
                assert not result["passed"] and not body["contract"]["successful"]
                assert body["candidate_tests"]["successful"] and not body["added_tests"]
                assert not body["documentation_directive_present"]
            print(label, {"passed":result["passed"], "upstream_tests":body["upstream"]["tests"],
                          "upstream_skips":body["upstream"]["skipped"]}, flush=True)
        inventory = [dict(path=name, size_bytes=len(raw), sha256=sha256_file(
            (task.AREA / "donor-001" if (task.AREA / "donor-001" / name).is_file() else task.AREA / "test-support-001") / name))
            for name, raw in candidate.files]
        (OUTPUT / "RESULTS.json").write_bytes(canonical_json_bytes(dict(status="baseline_qualified",
            completion_requests=0, candidate_id=candidate.candidate_id, selected_file_limit=candidate.max_file_bytes,
            candidate_files=len(candidate.files), candidate_bytes=sum(len(raw) for _, raw in candidate.files),
            inventory=inventory, exact_upstream_support=True, support_stubs=False,
            doc_semantics_automatically_established=False)))
        status = "baseline_qualified"
    except BaseException as error:
        (OUTPUT / "FAILED.json").write_bytes(canonical_json_bytes(dict(error_type=type(error).__name__, message=str(error))))
        raise
    finally:
        (OUTPUT / "SEAL.json").write_bytes(canonical_json_bytes(dict(status=status, completion_requests=0,
            source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in
                (Path(__file__), Path(task.__file__), task.AREA / "PUBLIC_CHECK.py", ROOT / "src/working_set_exp/isolation.py",
                 ROOT / "src/working_set_exp/candidate.py")},
            files=[dict(path=p.name, size_bytes=p.stat().st_size, sha256=sha256_file(p))
                   for p in sorted(OUTPUT.iterdir()) if p.is_file()])))


if __name__ == "__main__":
    main()
