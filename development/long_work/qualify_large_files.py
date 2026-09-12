"""Offline isolation probe: vary only file admission in this Python process.

This is not a host change or model-facing interface. It leaves tracked sources,
running processes, result bounds and all other admission constraints unchanged.
Run after inference ends, so its source parsing/hashing does not share a timing run.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from working_set_exp import candidate as admission
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

OUTPUT = ROOT / "development/long_work/large-file-qualification-001"


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(not OUTPUT.exists(), "preserve the existing qualification")
    baseline = admission.MAX_FILE_BYTES
    require(baseline == 24_000, "baseline limit changed")
    sources = {p.relative_to(ROOT).as_posix():p.read_bytes()
               for p in sorted((ROOT / "src/working_set_exp").rglob("*.py"))}
    baseline_source_sha = sha256_file(Path(admission.__file__))
    OUTPUT.mkdir()
    def save(name, value):
        with (OUTPUT/name).open("xb") as stream:
            stream.write(canonical_json_bytes(value))
    disposition = "incomplete"
    try:
        # A process-local counterfactual, not editing imported source or adopting
        # a new permanent limit. Candidate.patch still validates through create.
        admission.MAX_FILE_BYTES = 1_048_576
        candidate = admission.Candidate.create(sources)
        checker = b"from pathlib import Path\nfiles=sorted(Path('src').rglob('*.py'))\nfor p in files: compile(p.read_bytes(),str(p),'exec')\nprint(str(len(files))+' source files compile')\n"
        fixture = EcologicalFixture("LARGE-FILE-OFFLINE", "admission_return_probe", "Offline operation qualification only.",
            candidate, checker, b"", (), (), {}, ())
        value = new_state("offline-large-file", fixture)
        pages, first_handles = [], {}
        for path, expected in sources.items():
            start, chunks, count = 1, [], 0
            while start is not None:
                result = value.execute(dict(action="read", path=path, start_line=start))
                require(result.get("accepted") is True, "source read rejected: " + path)
                require(result["file_sha256"] == sha256_bytes(expected), "read source binding differs")
                require(result["returned_start_line"] == start or not expected, "read range has a gap")
                chunks.append(result["content"].encode())
                handle = f"RES-{len(value.pairs):04d}"
                first_handles.setdefault(path, handle)
                original = value.result_payloads[handle]
                recovered = value.execute(dict(action="reopen_result", handle=handle))
                require(recovered.get("accepted") and recovered["exact_result_utf8"].encode() == original,
                        "saved page does not recover exactly")
                start = result["next_start_line"]
                count += 1
            require(b"".join(chunks) == expected and path in value.state.complete_reads, "page coverage differs")
            pages.append(dict(path=path, bytes=len(expected), pages=count, exact_recovery=True))
        target = max(sources, key=lambda name:len(sources[name]))
        old = "from __future__ import annotations\n"
        new = old + "# Offline large-file qualification; not an application repair.\n"
        require(sources[target].decode().count(old) == 1, "unique local edit anchor differs")
        action = dict(action="patch", path=target, old=old, new=new,
            expected_candidate_id=value.state.candidate.candidate_id,
            expected_file_sha256=value.state.candidate.file_sha256(target))
        edited = value.execute(action)
        require(edited.get("accepted"), "guarded edit of large file rejected")
        successor = value.state.candidate
        stale = value.execute(action)
        require(not stale.get("accepted") and value.state.candidate == successor, "stale edit changed large candidate")
        checked = value.execute(dict(action="check", check_id="public", expected_candidate_id=successor.candidate_id))
        require(checked.get("accepted") and checked.get("passed"), "current large candidate compile check failed")
        # Recovery must concern the saved predecessor page, not changed current source.
        historical_handle = first_handles[target]
        original_page = value.result_payloads[historical_handle]
        saved = value.execute(dict(action="reopen_result", handle=historical_handle))
        require(saved.get("accepted") and saved["exact_result_utf8"].encode() == original_page,
                "historical source changed after mutation")
        save("pairs.json", value.pairs)
        save("RESULTS.json", dict(status="offline_counterfactual_qualified", completion_requests=0,
            source_files=len(sources), source_bytes=sum(map(len,sources.values())), pages=pages,
            initial_candidate=candidate.candidate_id, edited_candidate=successor.candidate_id,
            edited_file=target, edited_file_bytes=len(sources[target]),
            original_file_limit=baseline, tested_process_local_file_limit=admission.MAX_FILE_BYTES,
            other_limits_unchanged=True, public_compile_check=checked, stale_edit_result=stale,
            current_model_interface_changed=False, tracked_host_changed=False,
            limitations="No model input/admission/presentation or behavioral trial. Syntax compilation is not application correctness. Long document lines and additional file/total-size limits remain unqualified.",
            inventory=[dict(path=k,size_bytes=len(v),sha256=sha256_bytes(v)) for k,v in sources.items()]))
        disposition = "offline_qualified"
    except BaseException as error:
        save("FAILED.json", dict(error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        admission.MAX_FILE_BYTES = baseline
        require(sha256_file(Path(admission.__file__)) == baseline_source_sha, "tracked admission source changed")
        files = [dict(path=p.name,size_bytes=p.stat().st_size,sha256=sha256_file(p))
                 for p in sorted(OUTPUT.iterdir()) if p.is_file()]
        save("SEAL.json", dict(status=disposition, completion_requests=0, files=files,
            source_sha256=sha256_file(Path(__file__)), admission_source_sha256=baseline_source_sha,
            process_local_limit_restored=admission.MAX_FILE_BYTES == baseline))
    print({"status":disposition, "files":len(sources), "source_bytes":sum(map(len,sources.values())), "completion_requests":0})


if __name__ == "__main__":
    main()
