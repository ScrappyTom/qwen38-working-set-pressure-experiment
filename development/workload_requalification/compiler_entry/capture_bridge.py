"""Task-local access to sealed incident observations, without new edit authority.

Imported OBS records have no invented historical action. An actual acquisition
creates a normal RES receipt; existing exact result retention and paging then
apply. This adapter changes no checker, source guard, account or execution policy.
"""
from __future__ import annotations

import copy
import re

import navigation
import operational_reply
import repair_task
from search_navigation import SearchNavigationMixin
from working_set_exp import decision_view, working_view
from working_set_exp.accounted_contribution import account_rule
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


MAX_IMPORTED_OBSERVATIONS = 3
MAX_IMPORTED_BODY_BYTES = 16_384
_MANIFEST_KEYS = {"action", "candidate_id", "handle", "sequence", "sha256", "size_bytes", "target"}

REFERENCE_ADDITION = """
Imported incident observations are listed in imported_observations. Their OBS
addresses identify immutable records from the original reported incident, bound
to observed_candidate_id, not observations of a later repair. This inventory is
navigation, not the capture contents and not evidence that a capture was read.
reopen_observation requires exactly {"action":"reopen_observation","handle":"OBS-0001"}
(copy any listed OBS handle). It retrieves the complete preserved record without
rerunning the capture, check or compiler and without changing the candidate.
The accepted receipt contains exact content_utf8, its size_bytes and sha256, the
original observed_candidate_id and target, and a new exact_result_handle (RES).
Acquisition and actual presentation are different. If feedback is explicitly
status-only, the full acquisition receipt is archived at that RES address; use
reopen_result to inspect its actual byte pages. A partial serialized RES page is
not a complete capture. work_on or work_on_exact can retain complete acquired RES
receipts together with exact current source. Saved records are retained whole or
the group is rejected; exploratory source requests retain their existing paging.
shown_complete says a complete acquisition receipt is actually present in this
input, not merely that an acquisition previously succeeded. Imported captures
are historical evidence, supply no source-edit authority and never establish an
applicable check on the current candidate. Selecting or rereading them does not
execute a saved operation or alter their original binding.
""".strip()


def imported_action_form():
    return working_view.obj(dict(
        action=dict(type="string", const="reopen_observation"),
        handle=dict(type="string", pattern="^OBS-[0-9]{4}$")))


def extend_action_rule(rule):
    value = copy.deepcopy(rule)
    if set(value) != {"oneOf"} or any(
            form["properties"]["action"].get("const") == "reopen_observation"
            for form in value["oneOf"]):
        raise ValueError("unexpected or duplicate imported-observation action contract")
    value["oneOf"].append(imported_action_form())
    return value


def action_rule(checks):
    return extend_action_rule(decision_view.action_rule(checks))


def reply_schema(checks):
    value = operational_reply.reply_schema(checks)
    value["json_schema"]["name"] = "compiler_incident_contribution_v1"
    for form in value["json_schema"]["schema"]["oneOf"]:
        if "operation" in form["properties"]:
            form["properties"]["operation"] = action_rule(checks)
    return value


def reply_grammar(checks, converter_class):
    """Preserve the qualified ordinary/literal channels; add one operation form."""
    inherited = decision_view.reply_schema(checks)["json_schema"]["schema"]
    expanded = reply_schema(checks)["json_schema"]["schema"]
    replacements = []

    class ImportedConverter(converter_class):
        def visit(self, schema, name):
            if name == "ordinary-reply":
                if schema != inherited or replacements:
                    raise ValueError("inherited ordinary grammar entry changed")
                replacements.append(name)
                schema = expanded
            return super().visit(schema, name)

    grammar = decision_view.reply_grammar(checks, ImportedConverter)
    if replacements != ["ordinary-reply"]:
        raise ValueError("imported grammar did not extend the ordinary reply")
    return grammar


def decode_reply(content, checks):
    reply = decision_view.decode_reply(content)
    working_view.validate(reply, reply_schema(checks)["json_schema"]["schema"])
    return reply


def operating_reference(existing_text):
    return operational_reply.operating_reference(existing_text) + "\n\n" + REFERENCE_ADDITION


def _normalized_imports(observations, bodies):
    """Freeze exact manifests separately from exact immutable canonical bodies."""
    if not isinstance(observations, dict) or not 1 <= len(observations) <= MAX_IMPORTED_OBSERVATIONS:
        raise ValueError("imported observation inventory must contain one to three records")
    provided = dict(bodies) if bodies is not None else {}
    manifests, records = {}, {}
    for handle, row in observations.items():
        if (not isinstance(row, dict) or not isinstance(handle, str)
                or re.fullmatch(r"OBS-[0-9]{4}", handle) is None):
            raise ValueError("invalid imported observation identity")
        row = copy.deepcopy(row)
        embedded = row.pop("content_utf8", None)
        if set(row) != _MANIFEST_KEYS or row["handle"] != handle or row["action"] != "capture":
            raise ValueError("imported observation manifest differs from capture contract")
        if (not isinstance(row["candidate_id"], str)
                or re.fullmatch(r"[0-9a-f]{64}", row["candidate_id"]) is None
                or not isinstance(row["sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
                or type(row["sequence"]) is not int or row["sequence"] < 1
                or type(row["size_bytes"]) is not int or not 0 < row["size_bytes"] <= MAX_IMPORTED_BODY_BYTES
                or not isinstance(row["target"], str) or not 0 < len(row["target"].encode()) <= 256):
            raise ValueError("imported observation binding or supported extent differs")
        if embedded is not None and not isinstance(embedded, str):
            raise ValueError("imported content_utf8 must be exact text")
        raw = provided.pop(handle, None)
        if raw is None and embedded is not None:
            raw = embedded.encode()
        if not isinstance(raw, bytes) or (embedded is not None and embedded.encode() != raw):
            raise ValueError("imported observation body unavailable or conflicting")
        value = load_json_strict(raw)
        if (canonical_json_bytes(value) != raw or len(raw) != row["size_bytes"]
                or sha256_bytes(raw) != row["sha256"]):
            raise ValueError("imported observation body is not the exact canonical bound record")
        manifests[handle], records[handle] = canonical_json_bytes(row), raw
    if provided:
        raise ValueError("unlisted imported observation body")
    # Immutable tuples of byte strings are shared safely by session clones.
    return tuple(sorted(manifests.items())), tuple(sorted(records.items()))


def capture_snapshot(session):
    return dict(schema="compiler-imported-observations-v1",
                inventory=[load_json_strict(raw) for _, raw in session._imported_manifests],
                body_sha256={handle: sha256_bytes(raw) for handle, raw in session._imported_bodies})


def restore_capture_state(session, state):
    """Reconstruction supplies sealed bodies; the checkpoint may not rebind them."""
    if capture_snapshot(session) != state:
        raise ValueError("checkpoint imported observation bindings differ")
    return session


class Session(SearchNavigationMixin, navigation.NavigationMixin, repair_task.Session):
    def __init__(self, *args, imported_observations, imported_bodies=None, **kwargs):
        self._imported_manifests, self._imported_bodies = _normalized_imports(
            imported_observations, imported_bodies)
        super().__init__(*args, **kwargs)

    def action_rule(self):
        return dict(oneOf=[*action_rule(self.checkers)["oneOf"], account_rule()])

    def reply_schema(self):
        return reply_schema(self.checkers)

    def imported_record(self, handle):
        manifest = dict(self._imported_manifests).get(handle)
        raw = dict(self._imported_bodies).get(handle)
        if manifest is None or raw is None:
            raise ValueError("imported observation handle is unavailable")
        if not isinstance(manifest, bytes) or not isinstance(raw, bytes):
            raise ValueError("imported observation custody binding differs")
        row = load_json_strict(manifest)
        if (len(raw) != row["size_bytes"] or sha256_bytes(raw) != row["sha256"]
                or canonical_json_bytes(load_json_strict(raw)) != raw):
            raise ValueError("imported observation custody binding differs")
        return row, raw

    def _ordinary(self, action):
        if action["action"] != "reopen_observation":
            return super()._ordinary(action)
        row, raw = self.imported_record(action["handle"])
        return dict(accepted=True, kind="imported_observation", handle=row["handle"],
            observed_candidate_id=row["candidate_id"], target=row["target"],
            size_bytes=len(raw), sha256=row["sha256"], content_utf8=raw.decode(),
            exact_result_handle=f"RES-{len(self.pairs)+1:04d}",
            retrieval_only=True, source_edit_authority=False)

    def _shown_acquisitions(self, value):
        results = []
        latest = value.get("latest_feedback")
        if latest:
            results.append(latest["result"])
        pages = list(value["working_set"]["saved_results"])
        if latest:
            pages.extend(latest["result"].get("saved_results", []))
            if latest["result"].get("kind") == "saved_bytes":
                pages.append(latest["result"])
        for page in pages:
            if (page.get("kind") != "saved_bytes" or page.get("offset") != 0
                    or page.get("next_offset") is not None):
                continue
            text = page.get("exact_utf8", "")
            raw = text.encode()
            if len(raw) != page.get("total_bytes") or sha256_bytes(raw) != page.get("sha256"):
                continue
            try:
                result = load_json_strict(raw)
            except (ValueError, UnicodeError):
                continue
            if isinstance(result, dict):
                results.append(result)
        shown = set()
        for result in results:
            if not result.get("accepted") or result.get("kind") != "imported_observation":
                continue
            try:
                row, raw = self.imported_record(result["handle"])
            except (KeyError, ValueError, UnicodeError):
                continue
            if (result.get("observed_candidate_id") == row["candidate_id"]
                    and result.get("size_bytes") == len(raw) and result.get("sha256") == row["sha256"]
                    and result.get("content_utf8") == raw.decode()):
                shown.add(row["handle"])
        return shown

    def view(self, **kwargs):
        value = super().view(**kwargs)
        shown = self._shown_acquisitions(value)
        entries = []
        for handle, manifest in self._imported_manifests:
            row = load_json_strict(manifest)
            acquired = next((i for i in range(len(self.pairs), 0, -1)
                if self.pairs[i-1]["response"].get("action") == "reopen_observation"
                and self.pairs[i-1]["response"].get("handle") == handle
                and self.pairs[i-1]["result"].get("accepted")), None)
            entries.append(dict(handle=handle, target=row["target"],
                observed_candidate_id=row["candidate_id"], size_bytes=row["size_bytes"], sha256=row["sha256"],
                historical_incident=True, latest_acquisition_result=f"RES-{acquired:04d}" if acquired else None,
                shown_complete=handle in shown,
                retrieve=dict(action="reopen_observation", handle=handle)))
        value["imported_observations"] = dict(entries=entries, total_entries=len(entries),
            inventory_is_not_capture_content=True,
            scope="Original reported incident captures; not checks of the current repair.")
        return value
