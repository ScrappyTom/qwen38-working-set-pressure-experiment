"""Account for the combined session without diagnosing its thinking from counts."""
from datetime import datetime
import json

import parser_documentation_session as task


def measure():
    rows = []
    for folder in sorted(task.AREA.glob("turn-*")):
        records = [json.loads(line) for line in (folder/"records.jsonl").read_text(encoding="utf-8").splitlines()]
        def only(kind):
            found = [r for r in records if r["record_type"] == kind]
            if len(found) != 1:
                raise ValueError(f"Expected one {kind} in {folder.name}; do not hide partial calls")
            return found[0]
        start, finish = only("turn_prepared"), only("runtime_closed")
        done, processed = only("invocation_completed")["payload"], only("reply_processed")["payload"]
        seal = task.base.read(folder/"RESPONSE_SEAL.json")
        begin, end = start["created_at_utc"], finish["created_at_utc"]
        elapsed = (datetime.fromisoformat(end.replace("Z", "+00:00")) -
                   datetime.fromisoformat(begin.replace("Z", "+00:00"))).total_seconds()
        rows.append(dict(turn=folder.name, started_at=begin, closed_at=end,
            input_tokens=done["usage"]["prompt_tokens"], generated_tokens=done["usage"]["completion_tokens"],
            model_request_seconds=done["elapsed_seconds"], host_processing_seconds=processed["processing_seconds"],
            actual_operations=done["actual_operations"], owned_turn_seconds=elapsed, memory=seal["memory"]))
    task.base.require(bool(rows), "no completed turns")
    def date(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    window = (date(rows[-1]["closed_at"]) - date(rows[0]["started_at"])).total_seconds()
    owned = sum(r["owned_turn_seconds"] for r in rows)
    return dict(turns=rows, completed_replies=len(rows),
        totals={key: sum(r[key] for r in rows) for key in ("input_tokens", "generated_tokens", "model_request_seconds",
                "host_processing_seconds", "actual_operations", "owned_turn_seconds")},
        first_prepared_turn_through_last_runtime_closure_seconds=window,
        between_owned_turns_seconds=window-owned,
        timing_scope="Between-turn intervals include review and preparation, not a causal measure of active reviewer labor. "
            "Initial design/preparation and final audit are additional and unmeasured here, not zero.")


if __name__ == "__main__":
    result = measure()
    task.base.save(task.AREA, "SESSION_MEASUREMENTS.json", result)
    print(json.dumps(result, indent=2))
