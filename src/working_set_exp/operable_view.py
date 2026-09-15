"""Visible contracts for preserved observations and temporary recovery inputs."""
import copy

from . import accounted_contribution as prior, working_view
from .jsonutil import canonical_json_bytes


def action_rule(checks):
    forms = copy.deepcopy(prior.action_rule(checks)["oneOf"])
    def action(name, **fields):
        return working_view.obj(dict(action=dict(type="string", const=name), **fields))
    offset = dict(type="integer", minimum=0)
    forms += [action("inspect_observation", observation=dict(type="string", pattern="^CHK-[0-9]{4,}$"),
                     stream=dict(type="string", enum=["stdout", "stderr", "outcome"]), offset=offset),
              action("selection_page", offset=offset),
              action("work_on_exact", regions=dict(type="array", maxItems=16,
                     items=dict(type="string", pattern="^SRC-[0-9a-f]{64}$")),
                     results=dict(type="array", maxItems=16,
                     items=dict(type="string", pattern="^(RES|EVT)-[0-9]{4,}$")))]
    return dict(oneOf=forms)


def reply_schema(checks):
    rule = copy.deepcopy(prior.reply_schema(checks))
    rule["json_schema"]["name"] = "operable_contribution_v1"
    for form in rule["json_schema"]["schema"]["oneOf"]:
        if "operation" in form["properties"]:
            form["properties"]["operation"] = action_rule(checks)
    return rule


EFFECTS = dict(
    read="Reads exact current source using one-based lines and end_line=0 for onward. In ordinary presentation it adds the returned page to selected material. In recovery presentation it inspects a temporary whole-line page in latest feedback without changing selected material; that page is visible only while actually included in the input. The host sizes the page and returns actual extents, continuation and a reusable region reference. A requested end is an upper bound. The whole file is not required for an edit whose exact old text lies in a visible current excerpt.",
    work_on="Replaces designated sources and saved RES/EVT records using requested paths/ranges. Exploratory source ranges may be paged; inspect actual returned extents. Saved records are included whole or the group is rejected. A successful replacement fits ordinary presentation and returns to it. On rejection prior designations remain and recovery presentation permits another decision. Empty lists release that kind of selection. This changes selection, not stored artifacts or archived records. Selecting saved actions does not execute them or make their text eligible source.",
    work_on_exact="Replaces selected material with complete identified source regions plus complete saved RES/EVT records. Copy region references returned by reads, search contexts, outlines or selection inventory; no coordinate arithmetic is needed. Every referenced file fingerprint must still match. Search regions are explicitly bounded context around a match, not necessarily an entire function. If the whole group cannot fit ordinary presentation, reject it and preserve the prior selection. No source region is silently shortened. Success returns ordinary presentation with exact source visible. Empty lists release the selection.",
    check="Executes the named check on the required current candidate. Preserves its outcome and captured raw streams before deriving the displayed report. A failed completed check is accepted execution; timeout or capture limits are explicit incomplete observations. The report separates primary real failures from expected fault-test failures. Use its CHK observation reference for more detail. Reporting or presentation limits do not turn an executed check into request rejection. Applicability includes both candidate and checker identity.",
    inspect_observation="Reads captured stdout, stderr or the outcome record of a saved check; does not execute it again. Copy its CHK reference. offset=0 starts; use next_offset to continue. UTF-8 text is paged at character boundaries; non-UTF-8 captured bytes use explicit base64. Captured bytes and capture completeness describe what exists, not a promise that uncaptured output can be recovered. This inspection does not change source selection or supply editing authority.",
    selection_page="Lists at most eight designated source extents and saved records, with reusable references. offset=0 starts; use next_offset. Their bodies can be absent from a recovery input while remaining selected and stored. An inventory item is an address and scope, not visible source content.",
)

INSTRUCTIONS = (
    "presentation.mode tells you whether this is ordinary work or a recovery input. "
    "Recovery temporarily omits designated source/result bodies so the obstacle and a new operation's feedback can fit. "
    "Designation and actual visibility are different; only source actually shown in this input can authorize an edit. "
    "The task and current bindings remain. A long account is shown only as a labelled prefix, with its exact EVT reference; "
    "the full account is still stored and has not been rewritten. selection lists a bounded inventory; selection_page continues it. "
    "A read in recovery inspects a temporary exact page. Search/outline results return selectable region references. "
    "Use the real obstacle and available information to choose a next operation; all tools remain available under their guards. "
    "Recovery ends only when a selected arrangement fits ordinary presentation, not simply when another result appears. "
    "An accepted edit can lead to recovery presentation if its refreshed selection is too large; the edit and its actual check remain recorded. "
    "The host measures capacity. It does not decide which evidence is relevant or guarantee that an accepted operation resolves the task. "
    "Account provenance records authorship, not whether its claimed support is true."
)


def operating_reference(checks):
    reference = prior.operating_reference(checks, forms=action_rule(checks)["oneOf"],
                                         effect_overrides=EFFECTS, extra_instructions=INSTRUCTIONS)
    reference = reference.replace("With work_on, account and replacement", "With work_on or work_on_exact, account and replacement")
    return reference.replace(working_view.INPUT_INTERPRETATION,
        "The complete working set is all information actually presented in this call. "
        "In ordinary presentation, selected objects already shown in latest_feedback are omitted from the separate working_set lists. "
        "In recovery presentation, designated bodies may be omitted from both; only explicitly returned inspection content is visible. "
        "A historical capacity rejection describes its own attempted input, not a new measurement after changes.")


def feedback_view(feedback, *, recovery=False, limit=6144, show_inspection=False):
    if feedback is None:
        return None
    value = copy.deepcopy(feedback)
    result = value["result"]
    has_source = "source" in result or bool(result.get("sources"))
    if (not recovery or (not has_source or show_inspection)) and len(canonical_json_bytes(value)) <= limit:
        return value
    keys = ("accepted", "executed", "candidate_id", "previous_candidate_id", "checked_candidate_id",
            "file_sha256", "check_id", "check_definition_sha256", "passed", "returncode", "submitted",
            "observation", "capture_complete", "termination", "error", "error_code", "detail", "account_handle")
    brief = {k: result[k] for k in keys if k in result}
    for key, text in list(brief.items()):
        if isinstance(text, str) and len(text.encode()) > 512:
            brief[key] = text.encode()[:512].decode("utf-8", errors="ignore")
            brief[key + "_complete"] = False
    summary = {k: v for k, v in value.get("action_summary", {}).items()
               if k in ("action", "path", "check_id", "start_line", "end_line", "handle", "observation")}
    value.update(result=brief, action_summary=summary,
                 output_scope="status_only_full_result_archived",
                 full_result_handle=f"RES-{value['sequence']:04d}")
    return value


def present_receipts(view, receipts):
    recovery = view["presentation"]["mode"] == "recovery"
    return [feedback_view(r, recovery=recovery, limit=1024 if recovery else 6144)
            for r in receipts if not view["latest_feedback"] or r["sequence"] != view["latest_feedback"]["sequence"]]
