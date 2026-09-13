"""Opt-in bounded operating view. Historical experiment renderers stay unchanged."""
from __future__ import annotations

import re
from typing import Any

from .jsonutil import canonical_json_bytes
from .tools import action_schema


def obj(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def schema():
    forms = action_schema("continuation", probe_id=None, read_mode="maximal_bounded_page",
                          hierarchical_p0=True, result_reopen=True, event_reopen=True)["json_schema"]["schema"]["oneOf"]
    forms = [f for f in forms if f["properties"]["action"]["const"] not in
             {"read", "patch", "reopen_result", "reopen_event", "reopen_observation"}]
    for form in forms:
        if form["properties"]["action"]["const"] == "check":
            form["properties"]["check_id"]["enum"] = ["public"]
    text = {"type": "string"}
    path = dict(type="string", minLength=1, maxLength=160)
    line = dict(type="integer", minimum=1, maximum=2_000_000)
    end = dict(type="integer", minimum=0, maximum=2_000_000)
    sha = dict(type="string", pattern="^[0-9a-f]{64}$")
    source = obj(dict(path=path, start_line=line, end_line=end))
    def action(name, **fields):
        return obj({"action": {"type": "string", "const": name}, **fields})
    forms += [action("read", **source["properties"]),
              action("work_on", sources=dict(type="array", items=source, maxItems=16),
                     results=dict(type="array", items=dict(type="string", pattern="^RES-[0-9]{4,}$"), maxItems=16)),
              action("patch", path=path, old=text, new=text,
                     expected_candidate_id=sha, expected_file_sha256=sha),
              action("history", before=dict(type="integer", minimum=0), path=dict(type="string", maxLength=160))]
    for name, prefix in (("reopen_result", "RES"), ("reopen_event", "EVT")):
        forms.append(action(name, handle=dict(type="string", pattern=f"^{prefix}-[0-9]{{4,}}$"),
                            offset=dict(type="integer", minimum=0)))
    return dict(type="json_schema", json_schema=dict(name="bounded_working_action_v1", strict=True,
                                                     schema={"oneOf": forms}))


def validate(value: Any, rule: dict):
    """Validate precisely the small schema vocabulary used above, including arrays."""
    supported = {"type", "properties", "required", "additionalProperties", "items", "maxItems",
                 "const", "enum", "pattern", "minimum", "maximum", "minLength", "maxLength", "oneOf"}
    if set(rule) - supported:
        raise ValueError("unsupported action constraint")
    if "oneOf" in rule:
        matched = 0
        for option in rule["oneOf"]:
            try:
                validate(value, option)
                matched += 1
            except ValueError:
                pass
        if matched != 1:
            raise ValueError("action does not match exactly one supplied form")
        return
    kinds = {"object": dict, "array": list, "string": str, "integer": int}
    if rule.get("type") not in kinds or type(value) is not kinds[rule["type"]]:
        raise ValueError("action argument type differs")
    if "const" in rule and value != rule["const"]:
        raise ValueError("action constant differs")
    if "enum" in rule and value not in rule["enum"]:
        raise ValueError("action enumeration differs")
    if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
        raise ValueError("action pattern differs")
    for key in ("minimum", "maximum", "minLength", "maxLength", "maxItems"):
        if key in rule:
            actual = len(value) if key.endswith(("Length", "Items")) else value
            if (key.startswith("min") and actual < rule[key]) or (key.startswith("max") and actual > rule[key]):
                raise ValueError("action constraint exceeded")
    if type(value) is dict:
        if rule.get("additionalProperties") is not False or set(value) != set(rule["required"]):
            raise ValueError("action keys differ")
        for key, child in value.items():
            validate(child, rule["properties"][key])
    if type(value) is list:
        for item in value:
            validate(item, rule["items"])


EFFECTS = {
    "tree": "Lists a shallow directory page. offset and limit select entries; it returns no source.",
    "p0_page": "Returns a scoped directory or file-outline page with source locations, not exact source. Repository incompleteness describes scope; paging is optional and does not make the root complete.",
    "search": "Literal case-insensitive current-source search. path may be a file or directory; offset/limit page matches. Search snippets are not whole-source inspection.",
    "read": "Opens exact current source and adds it to the working set. Lines are one-based; end_line=0 requests onward. The host chooses a whole-line page that fits the COMPLETE next input while keeping existing working material. A specified end is an upper bound. returned_end_line and next_start_line describe the actual page, not full-file coverage. No need to count characters or tokens.",
    "work_on": "Assembles the source ranges and saved results needed together for a contribution, replacing the previous working set. Uses the same range/page meanings as read. Select material by relevance, not numeric packing. The host sizes pages together and preserves them through navigation, search, edits and checks until another work_on. An empty list releases that kind of working material. Saved results keep their historical version; opening them does not rerun anything.",
    "patch": "Atomically replaces exactly one occurrence of old with new in an existing file. expected_candidate_id is the CURRENT version to edit; expected_file_sha256 is the current file's PRE-EDIT fingerprint. Exact old source must be visible before editing. Equal replacements and stale guards are rejected. The host validates complete UTF-8 sizes, the displayed candidate_limits and next-input capacity before committing; it never shortens an edit. Ordinary complete edits are supported: each fragment may use 65,536 UTF-8 bytes and the action up to 1,048,576 serialized bytes. These are host limits, not a request to manually count or split text. Returns actual successor bindings and inclusive pre/post source-line intervals (empty for no removed/inserted text). Open ranges are refreshed to current source; full original actions and exact diffs remain archived. A successful edit is not a successful check.",
    "check": "Executes the named public check on expected_candidate_id, which must equal the current version. Returns actual output and pass/fail. A failed check is accepted execution. Later edits invalidate applicability of an earlier passing check.",
    "submit": "Finishes with expected_candidate_id only when that exact current candidate has a passing public check. Does not edit or execute another check.",
    "history": "Lists at most eight archived actions, newest first, with exact recovery handles and version/check bindings. before=0 starts at the newest; otherwise use the returned next_before. path='' includes every path; a nonempty path filters actions on that file. This is navigation, not source recovery. Recent activity is only a bounded window, never the whole archive.",
    "reopen_result": "Reads exact serialized saved RESULT bytes without executing anything. offset=0 starts; continue with returned next_offset. The host fits a UTF-8-safe page beside working material. A later page replaces the earlier page of the same handle in the working set. Original bytes and identity remain unchanged. An old check concerns its saved candidate, not the current candidate automatically.",
    "reopen_event": "Reads exact saved ACTION bytes, including original patch arguments, without replay or mutation. offset=0 starts; use next_offset for another exact UTF-8-safe page. The archive also preserves actual patch diffs. It does not return fresh source or a new check.",
}


def system_prompt():
    reference = []
    for form in schema()["json_schema"]["schema"]["oneOf"]:
        name = form["properties"]["action"]["const"]
        reference.append(name + ": " + EFFECTS[name] + "\nRequired argument forms: " +
                         canonical_json_bytes(form).decode())
    return ("You are repairing software using the supplied workspace. Choose one useful operation and return exactly "
            "one JSON action matching its supplied form. Read exact current source before editing, use actual returned "
            "bindings and evidence, check the successor and submit when the requested contribution is complete. "
            "The host retains a full archive, but your input contains only current state, a bounded recent history, "
            "the working set and the latest result. Material in the latest result is visible too. "
            "If latest_feedback says status_only_full_result_archived, its result is explicitly partial: use the supplied "
            "full_result_handle to inspect omitted output; execution status and version binding remain actual. "
            "Prior private thinking is not carried forward. Saved work is the actual current artifact; a saved check applies only to its version. "
            "A host-generated current source view is exact source, not a model-authored summary. Use work_on when changing "
            "which sources/results you need together; it is optional, not a prerequisite to every action. "
            "The supplied task distinguishes the earlier saved work from this new contribution.\n\n" + "\n\n".join(reference))


def request(state, settings):
    return {**settings, "messages": [{"role": "system", "content": system_prompt()},
                                    {"role": "user", "content": canonical_json_bytes(state).decode()}],
            "response_format": schema()}
