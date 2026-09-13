"""Offline analysis of the consumed C11 patch; never calls a model or edits it."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    run = root / "development/configparser_backport/run-001"
    reasoning = (run / "calls/C11-assistant-reasoning.txt").read_bytes().decode()
    start = reasoning.index('{"action":"patch"')
    planned, _ = json.JSONDecoder().raw_decode(reasoning[start:])
    actual = json.loads((run / "calls/C11-action.json").read_bytes())
    request = json.loads(
        (run / "admission/C11-x005-endpoint-request.json").read_bytes()
    )
    forms = request["response_format"]["json_schema"]["schema"]["oneOf"]
    patch = next(f for f in forms if f["properties"]["action"]["const"] == "patch")
    limit = patch["properties"]["new"]["maxLength"]
    prefix = 0
    for a, b in zip(planned["new"], actual["new"]):
        if a != b:
            break
        prefix += 1
    imports = []
    for call in (10, 11, 12, 13):
        candidate = json.loads(
            (run / f"after/C{call:02d}-candidate.json").read_bytes()
        )
        source = next(
            f["content_utf8"] for f in candidate["files"]
            if f["path"] == "Lib/configparser.py"
        )
        result = {"after_call": call, "candidate_id": candidate["candidate_id"]}
        try:
            code = compile(source, "Lib/configparser.py", "exec")
            result["compiles"] = True
            exec(code, {"__name__": "configparser_boundary_probe"})
            result["module_execution_succeeds"] = True
        except Exception as exc:
            result.setdefault("compiles", False)
            result.update(module_execution_succeeds=False,
                          exception_type=type(exc).__name__, message=str(exc))
        imports.append(result)
    print(json.dumps({
        "scope": "post-run offline development probe, not a model run or score",
        "supplied_new_field_max_characters": limit,
        "reasoning_action_start_character": start,
        "reasoning_planned_new_characters": len(planned["new"]),
        "actual_new_characters": len(actual["new"]),
        "common_prefix_characters": prefix,
        "planned_suffix_after_common_prefix": planned["new"][prefix:],
        "actual_suffix_after_common_prefix": actual["new"][prefix:],
        "candidate_module_execution": imports,
        "interpretation_limit": (
            "The final action differs from the stated plan at the supplied cap. "
            "This does not independently isolate the cause of that difference."
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
