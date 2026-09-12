"""Qualify explicit larger-file admission through the actual host, without inference."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from working_set_exp.candidate import Candidate, CandidateError, MAX_FILE_BYTES
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.event_frame_v3 import event_from_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.tools import MAX_READ_CONTENT_BYTES, MAX_RESULT_BYTES
import prepare_investigation_loop as preparation
import run_compiler_incident as historical

LIMIT = 1_048_576
OUTPUT = ROOT / "development/long_work/explicit-file-qualification-001"
SYNTHETIC = "src/qualification/escaped_boundary.py"


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(not OUTPUT.exists(), "preserve the existing attempt")
    require(MAX_FILE_BYTES == 24_000, "historical default changed")
    sources = {p.relative_to(ROOT).as_posix(): p.read_bytes()
               for p in sorted((ROOT / "src/working_set_exp").rglob("*.py"))}
    source_bindings = {p: sha256_bytes(raw) for p, raw in sources.items()}
    source_bindings["scripts/prepare_investigation_loop.py"] = sha256_file(Path(preparation.__file__))
    source_bindings[Path(__file__).relative_to(ROOT).as_posix()] = sha256_file(Path(__file__))
    # A constructed serialization boundary, never presented as task material.
    escaped = (b"#" + b'"\\' * 63 + b"\n") * (LIMIT // 128)
    require(len(escaped) == LIMIT, "constructed boundary size differs")
    files = {**sources, SYNTHETIC: escaped}
    OUTPUT.mkdir()

    def save(name, value):
        with (OUTPUT / name).open("xb") as stream:
            stream.write(canonical_json_bytes(value))

    disposition, value = "incomplete", None
    try:
        default_rejected = []
        for path, raw in files.items():
            try:
                Candidate.create({path: raw})
            except CandidateError as error:
                require(len(raw) > MAX_FILE_BYTES and "file exceeds" in str(error), "unexpected default rejection")
                default_rejected.append(path)
        candidate = Candidate.create(files, max_file_bytes=LIMIT)
        require(Candidate.create(candidate.file_map, max_file_bytes=candidate.max_file_bytes) == candidate,
                "explicit snapshot reconstruction differs")
        checker = (b"from pathlib import Path\nfiles=sorted(Path('src').rglob('*.py'))\n"
                   b"for p in files: compile(p.read_bytes(),str(p),'exec')\n"
                   b"print(str(len(files))+' source files compile')\n")
        fixture = EcologicalFixture("EXPLICIT-LARGE-FILE-OFFLINE", "admission_return_probe",
            "Offline qualification only.", candidate, checker, b"", (), (), {}, ())
        value = new_state("explicit-large-file", fixture)
        page_rows, first_handles = [], {}
        for path, expected in files.items():
            start, chunks = 1, []
            while start is not None:
                action = dict(action="read", path=path, start_line=start)
                result = value.execute(action)
                require(result.get("accepted") is True, "source read rejected: " + path)
                raw = canonical_json_bytes(result)
                require(result["candidate_id"] == candidate.candidate_id
                        and result["file_sha256"] == sha256_bytes(expected), "read binding differs")
                require(result["returned_start_line"] == start, "page coverage has a gap")
                expected_lines = expected.decode().splitlines(keepends=True)
                require(result["content"] == "".join(expected_lines[start-1:result["returned_end_line"]]),
                        "returned page is not exact whole lines")
                chunks.append(result["content"].encode())
                handle = f"RES-{len(value.pairs):04d}"
                first_handles.setdefault(path, handle)
                require(value.result_payloads[handle] == raw, "stored result differs")
                external = event_from_pair_v3(action, result, sequence=len(value.pairs), payload_residency="external")
                require(external["result_body"]["fields"] is None
                        and external["result_body"]["canonical_source"]["handle"] == handle,
                        "external record exposes or misaddresses source")
                recovered = value.execute(dict(action="reopen_result", handle=handle))
                require(recovered.get("accepted") is True and recovered["exact_result_utf8"].encode() == raw,
                        "stored result does not recover exactly")
                require(recovered["exact_result_sha256"] == sha256_bytes(raw)
                        and recovered["size_bytes"] == len(raw), "recovery binding differs")
                require(len(raw) <= MAX_RESULT_BYTES and len(canonical_json_bytes(recovered)) <= MAX_RESULT_BYTES
                        and len(result["content"].encode()) <= MAX_READ_CONTENT_BYTES, "result exceeds unchanged bound")
                page_rows.append(dict(path=path, handle=handle, start=start, end=result["returned_end_line"],
                    source_bytes=len(result["content"].encode()), result_bytes=len(raw),
                    recovery_bytes=len(canonical_json_bytes(recovered)), exact_recovery=True))
                start = result["next_start_line"]
            require(b"".join(chunks) == expected and path in value.state.complete_reads, "full source coverage differs")

        target = max(sources, key=lambda path: len(sources[path]))
        old = "from __future__ import annotations\n"
        require(sources[target].decode().count(old) == 1, "real-file edit anchor differs")
        action = dict(action="patch", path=target, old=old,
            new=old + "# Offline explicit file-limit qualification.\n",
            expected_candidate_id=candidate.candidate_id, expected_file_sha256=candidate.file_sha256(target))
        edited = value.execute(action)
        require(edited.get("accepted") is True, "large-file guarded edit rejected")
        successor = value.state.candidate
        require(successor.max_file_bytes == LIMIT, "successor lost selected policy")
        require(Candidate.create(successor.file_map, max_file_bytes=LIMIT) == successor
                and successor.with_files(successor.files) == successor, "policy reconstruction differs")
        stale = value.execute(action)
        require(not stale.get("accepted") and value.state.candidate == successor, "stale patch mutated candidate")
        checked = value.execute(dict(action="check", check_id="public", expected_candidate_id=successor.candidate_id))
        require(checked.get("accepted") and checked.get("passed"), "current syntax check failed")
        handle = first_handles[target]
        saved = value.execute(dict(action="reopen_result", handle=handle))
        original = load_json_strict(saved["exact_result_utf8"].encode())
        require(saved.get("accepted") and original["candidate_id"] == candidate.candidate_id
                and original["file_sha256"] != successor.file_sha256(target), "old page silently became current")

        request = load_json_strict((ROOT / "development/saved_work_continuation/preparation-001/initial-request.json").read_bytes())
        visible = preparation.tool_reference(request["response_format"], candidate=successor)
        require("at most 1,048,576 bytes\nper file" in visible and "at most 24,000 bytes\nper file" not in visible,
                "visible file policy differs")
        (OUTPUT / "visible-tool-reference.txt").write_bytes(visible.encode())

        # Read-only compatibility on the exact earlier saved-work actions. This
        # is prospective-host replay, not rerunning its frozen source verifier.
        past = ROOT / "development/saved_work_continuation/run-001"
        snapshot = load_json_strict((past / "after/P2-07-C09-snapshot.json").read_bytes())
        replay = new_state("historical-default-replay", historical.load_fixture())
        for pair in snapshot["pairs"]:
            require(replay.execute(pair["response"]) == pair["result"], "historical default result changed")
        require(historical.snapshot(replay) == snapshot, "historical session or payload bindings changed")
        require(replay.state.candidate.max_file_bytes == MAX_FILE_BYTES, "historical replay selected a new limit")
        save("RESULTS.json", dict(status="offline_explicit_policy_qualified", completion_requests=0,
            selected_file_limit=LIMIT, historical_default=MAX_FILE_BYTES, real_file_count=len(sources),
            real_source_bytes=sum(map(len, sources.values())), synthetic_path=SYNTHETIC, synthetic_bytes=len(escaped),
            source_files=len(files), source_bytes=sum(map(len, files.values())),
            pages=page_rows, operation_count=len(value.pairs), default_rejected_paths=default_rejected,
            initial_candidate=candidate.candidate_id, edited_candidate=successor.candidate_id,
            edited_real_file=target, edited_real_file_bytes=len(sources[target]),
            public_compile_check=checked, stale_edit_result=stale,
            historical_default_replayed_operations=len(replay.pairs), historical_exact_snapshot_match=True,
            historical_snapshot_sha256=sha256_file(past / "after/P2-07-C09-snapshot.json"),
            visible_reference_sha256=sha256_file(OUTPUT / "visible-tool-reference.txt"),
            source_sha256=source_bindings,
            inventory=[dict(path=path, size_bytes=len(raw), sha256=sha256_bytes(raw), constructed=path == SYNTHETIC)
                       for path, raw in files.items()],
            limitations="No model input or delivery qualification, no application repair, and no model capability claim. "
                        "Syntax compilation does not establish application correctness. Other file/count/line/total and result limits remain unchanged."))
        disposition = "offline_explicit_policy_qualified"
    except BaseException as error:
        save("FAILED.json", dict(error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        if value is not None:
            save("pairs.json", value.pairs)
        require(all(sha256_file(ROOT / path) == digest for path, digest in source_bindings.items()),
                "qualification source changed")
        save("SEAL.json", dict(status=disposition, completion_requests=0, source_sha256=source_bindings,
            files=[dict(path=p.name, size_bytes=p.stat().st_size, sha256=sha256_file(p))
                   for p in sorted(OUTPUT.iterdir()) if p.is_file()]))
    print({"status": disposition, "real_files": len(sources), "constructed_boundary_bytes": len(escaped),
           "pages": len(page_rows), "operations": len(value.pairs), "historical_replays": len(replay.pairs),
           "completion_requests": 0})


if __name__ == "__main__":
    main()
