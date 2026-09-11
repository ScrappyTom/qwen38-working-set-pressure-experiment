"""Reproduce return-size failures using the actual checkout, without model calls."""
from __future__ import annotations

import argparse
from pathlib import Path

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import _record_pair
from working_set_exp.event_frame_v3 import event_from_pair_v3
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.tools import SessionState, ToolExecutor
import working_set_exp.tools as tools_module


def snapshot(state):
    return {"candidate_id": state.candidate.candidate_id, "complete_reads": sorted(state.complete_reads),
            "read_coverage": state.read_coverage, "prefork_check_passed": state.prefork_check_passed,
            "public_check_passed": state.public_check_passed, "fork_ready": state.fork_ready}


class ObservedExecutor(ToolExecutor):
    def _bounded(self, result, **kwargs):
        self.attempted_results.append(result)
        return super()._bounded(result, **kwargs)


def probe(label, line):
    source = (line + "\n").encode("utf-8") * 200
    state = SessionState(Candidate.create({"data.txt": source}), stage="continuation")
    payloads, events, pairs = {}, {}, []
    executor = ObservedExecutor(state, required_full_reads=("data.txt",), prefork_checker=b"", public_checker=b"",
                                final_target="__none__", probe_id=None, probe_body=None,
                                result_reopenable=payloads, event_reopenable=events, read_mode="maximal_bounded_page")
    executor.attempted_results = []
    before = canonical_json_bytes(snapshot(state))
    action = {"action": "read", "path": "data.txt", "start_line": 1}
    result = executor.execute(action)
    after = canonical_json_bytes(snapshot(state))
    attempted = list(executor.attempted_results)
    _record_pair(pairs, action, result, events, payloads)
    external = event_from_pair_v3(action, result, sequence=1, payload_residency="external")
    original = payloads["RES-0001"]
    executor.attempted_results = []
    reopened = executor.execute({"action": "reopen_result", "handle": "RES-0001"})
    wrapper_attempts = list(executor.attempted_results)
    # A gate probe supplies the independent check flag to isolate the read obligation.
    state.stage, state.prefork_check_passed = "prefix", True
    gate = executor.execute({"action": "fork_ready", "expected_candidate_id": state.candidate.candidate_id})
    return {"case": label, "source_utf8": source.decode(), "source_bytes": len(source), "source_sha256": sha256_bytes(source),
            "candidate_admitted": True, "read_action": action, "state_before_utf8": before.decode(),
            "read_result": result, "read_result_bytes": len(canonical_json_bytes(result)),
            "bounded_read_attempt_bytes": [len(canonical_json_bytes(r)) for r in attempted],
            "state_after_read_utf8": after.decode(), "externalized_event": external,
            "stored_original_utf8": original.decode(), "stored_original_sha256": sha256_bytes(original),
            "reopen_result": reopened, "bounded_wrapper_attempt_bytes": [len(canonical_json_bytes(r)) for r in wrapper_attempts],
            "stored_original_unchanged": payloads["RES-0001"] == original,
            "boundary_with_independently_supplied_check_flag": gate,
            "actual_model_requests": 0, "delivery_to_model_observed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    rows = [probe("ordinary", "a" * 89), probe("quote_heavy", '"' * 89), probe("mixed", '"' * 10 + "a" * 79)]
    report = {"scope": "offline actual-checkout probes; no model inference; synthetic admitted source, not observed model behavior",
              "probe_source_sha256": sha256_file(Path(__file__)), "tools_sha256": sha256_file(Path(tools_module.__file__)),
              "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(report))
    for r in rows:
        print(r["case"], "read", r["read_result"]["accepted"], r["bounded_read_attempt_bytes"],
              "reopen", r["reopen_result"]["accepted"], r["bounded_wrapper_attempt_bytes"],
              "state", r["state_after_read_utf8"])


if __name__ == "__main__":
    main()
