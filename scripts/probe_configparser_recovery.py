"""Exercise saved exact-access wrappers offline, without continuing the actor."""
import argparse
from pathlib import Path

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.tools import SessionState, ToolExecutor, MAX_RESULT_BYTES


def probe():
    root = Path(__file__).resolve().parents[1]
    folder = root / "development/configparser_backport/run-001"
    saved = load_json_strict((folder / "final-candidate.json").read_bytes())
    candidate = Candidate.create({f["path"]: f["content_utf8"].encode() for f in saved["files"]},
                                 max_file_bytes=1_048_576)
    assert candidate.candidate_id == saved["candidate_id"]
    payloads = folder / "payloads/final"
    results = {p.stem: p.read_bytes() for p in payloads.glob("RES-*.json")}
    events = {p.stem: p.read_bytes() for p in payloads.glob("EVT-*.json")}
    state = SessionState(candidate, stage="continuation")
    executor = ToolExecutor(state, required_full_reads=(), prefork_checker=b"", public_checker=b"",
        final_target="Lib/configparser.py", probe_id=None, probe_body=None,
        result_reopenable=results, event_reopenable=events)
    rows = []
    for handle, raw in sorted(results.items()):
        response = executor.execute({"action": "reopen_result", "handle": handle})
        assert response["accepted"] and response["exact_result_utf8"].encode() == raw
        assert response["exact_result_sha256"] == sha256_bytes(raw)
        size = len(canonical_json_bytes(response))
        assert size <= MAX_RESULT_BYTES
        rows.append(dict(handle=handle, stored_bytes=len(raw), wrapper_bytes=size))
    for handle, raw in sorted(events.items()):
        response = executor.execute({"action": "reopen_event", "handle": handle})
        assert response["accepted"] and canonical_json_bytes(response["action_payload"]) == raw
        assert response["action_payload_sha256"] == sha256_bytes(raw)
        rows.append(dict(handle=handle, stored_bytes=len(raw), wrapper_bytes=len(canonical_json_bytes(response))))
    assert state.candidate.candidate_id == saved["candidate_id"] and not state.submitted
    return dict(scope="offline exact wrapper replay, not model-selected retrieval or input delivery",
                no_model_requests=True, candidate_unchanged=True, result_handles=len(results),
                event_handles=len(events), max_wrapper_bytes=max(r["wrapper_bytes"] for r in rows), rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe()
    with args.output.open("xb") as stream:
        stream.write(canonical_json_bytes(result))
    print({k: v for k, v in result.items() if k != "rows"})
