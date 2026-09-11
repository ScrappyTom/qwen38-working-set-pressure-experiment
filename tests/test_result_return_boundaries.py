"""Actual-host regressions for atomic returns and exact recovery under byte bounds."""
from __future__ import annotations

import copy
from pathlib import Path

import unittest
import tempfile
from unittest import mock

from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore
from working_set_exp.ecological_pilot_v2 import _record_pair
from working_set_exp.event_frame_v3 import event_from_pair_v3
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.tools import MAX_READ_CONTENT_BYTES, MAX_RESULT_BYTES, SessionState, ToolError, ToolExecutor
import working_set_exp.tools as module


def executor(files=None, **kwargs):
    state = SessionState(Candidate.create(files or {"data.txt": b"one\ntwo\n"}), stage="continuation")
    options = dict(required_full_reads=(), prefork_checker=b"", public_checker=b"",
                   final_target="__none__", probe_id=None, probe_body=None, read_mode="maximal_bounded_page")
    options.update(kwargs)
    return ToolExecutor(state, **options)


def envelope(raw, handle="RES-0001"):
    # Independently construct the externally documented recovery object.
    return {"accepted": True, "handle": handle, "exact_result_utf8": raw.decode("utf-8"),
            "exact_result_sha256": sha256_bytes(raw), "size_bytes": len(raw)}


SOURCES = [
    ("ordinary", ("a" * 89 + "\n").encode() * 200),
    ("quotes", ('"' * 89 + "\n").encode() * 200),
    ("backslashes", ("\\" * 89 + "\n").encode() * 200),
    ("mixed", ('"' * 10 + "a" * 79 + "\n").encode() * 200),
    ("controls", ("\x00" * 89 + "\n").encode() * 200),
    ("crlf", ('"' * 88 + "\r\n").encode() * 200),
    ("unicode", ("🙂" * 22 + "\n").encode() * 200),
    ("blank_lines", b"\n" * 24000),
]


def exercise_page_roundtrip(tmp_path, label, source, mode):
    path = "nested/" + "q" * 145 + ".txt"
    host = executor({path: source}, read_mode=mode)
    pairs, events, saved = [], {}, host.result_reopenable
    store = ArtifactStore(tmp_path)
    lines, recovered, start = source.decode().splitlines(keepends=True), [], 1
    while True:
        action = {"action": "read", "path": path, "start_line": start}
        if mode == "actor_selected_count":
            action["line_count"] = 500
        result = host.execute(action)
        assert result["accepted"], result
        raw = canonical_json_bytes(result)
        assert len(raw) <= MAX_RESULT_BYTES
        assert len(result["content"].encode()) <= MAX_READ_CONTENT_BYTES
        assert len(canonical_json_bytes(envelope(raw))) <= MAX_RESULT_BYTES
        end = result["returned_end_line"]
        assert result["content"] == "".join(lines[start-1:end])
        if end < len(lines) and (mode != "actor_selected_count" or end-start+1 < 500):
            bigger = {**result, "content": "".join(lines[start-1:end+1]), "returned_end_line": end+1,
                      "next_start_line": end+2 if end+1 < len(lines) else None, "complete": end+1 == len(lines)}
            larger_raw = canonical_json_bytes(bigger)
            assert (len(bigger["content"].encode()) > MAX_READ_CONTENT_BYTES
                    or len(larger_raw) > MAX_RESULT_BYTES
                    or len(canonical_json_bytes(envelope(larger_raw))) > MAX_RESULT_BYTES)
        handle = _record_pair(pairs, action, result, events, saved)
        store.put(f"{handle}.json", raw)
        host.result_reopenable[handle] = (tmp_path/f"{handle}.json").read_bytes()
        external = event_from_pair_v3(action, result, sequence=len(pairs), payload_residency="external")
        assert external["result_body"]["fields"] is None
        assert external["result_body"]["canonical_source"]["handle"] == handle
        before = copy.deepcopy(host.state)
        for _ in range(2):
            access = {"action": "reopen_result", "handle": handle}
            reopened = host.execute(access)
            assert reopened == envelope(raw, handle)
            assert len(canonical_json_bytes(reopened)) <= MAX_RESULT_BYTES
            assert host.state == before
            keys = set(saved)
            assert _record_pair(pairs, access, reopened, events, saved) == handle
            assert set(saved) == keys and saved[handle] == raw
        # The alternative OBS route uses the identical-sized envelope.
        observer = executor(reopenable={"OBS-0001": raw})
        assert observer.execute({"action": "reopen_observation", "handle": "OBS-0001"}) == envelope(raw, "OBS-0001")
        recovered.append(result["content"])
        if result["next_start_line"] is None:
            break
        assert path not in host.state.complete_reads
        assert result["next_start_line"] == end+1 > start
        start = result["next_start_line"]
    assert "".join(recovered).encode() == source
    assert host.state.read_coverage[path] == [(1, len(lines))]
    assert path in host.state.complete_reads


def reject_accepted(host):
    bounded = host._bounded
    def reject(result, **kwargs):
        if result.get("accepted"):
            raise ToolError("injected complete-return rejection")
        return bounded(result, **kwargs)
    return mock.patch.object(host, "_bounded", side_effect=reject)


def patch_action(host, path, old, new):
    return {"action":"patch", "path":path, "old":old, "new":new,
            "expected_candidate_id":host.state.candidate.candidate_id,
            "expected_file_sha256":host.state.candidate.file_sha256(path)}


class ReturnBoundaryTests(unittest.TestCase):
    def test_serialization_matrix_roundtrips_all_pages(self):
        for mode in ("maximal_bounded_page", "actor_selected_count"):
            for label, source in SOURCES:
                with self.subTest(mode=mode, source=label), tempfile.TemporaryDirectory() as raw:
                    exercise_page_roundtrip(Path(raw), label, source, mode)

    def test_rejected_read_does_not_credit_coverage_or_open_boundary(self):
        for source in (b"", b"one\ntwo\n"):
            with self.subTest(source=source):
                host = executor({"data.txt":source}, required_full_reads=("data.txt",))
                host.state.stage, host.state.prefork_check_passed = "prefix", True
                before = copy.deepcopy(host.state)
                with reject_accepted(host):
                    result = host.execute({"action":"read", "path":"data.txt", "start_line":1})
                self.assertFalse(result["accepted"])
                self.assertNotIn("content", result)
                self.assertEqual(host.state, before)
                gate = host.execute({"action":"fork_ready", "expected_candidate_id":host.state.candidate.candidate_id})
                self.assertFalse(gate["accepted"])
                self.assertIn("complete reads remain", gate["detail"])

    def test_partial_quote_read_leaves_gate_closed_until_continuous_coverage(self):
        host = executor({"data.txt": ('"'*89+'\n').encode()*200}, required_full_reads=("data.txt",))
        host.state.stage, host.state.prefork_check_passed = "prefix", True
        first = host.execute({"action":"read", "path":"data.txt", "start_line":1})
        self.assertTrue(first["accepted"])
        self.assertFalse(first["complete"])
        self.assertFalse(host.execute({"action":"fork_ready", "expected_candidate_id":host.state.candidate.candidate_id})["accepted"])
        start = first["next_start_line"]
        while start is not None:
            result = host.execute({"action":"read", "path":"data.txt", "start_line":start})
            self.assertTrue(result["accepted"])
            start = result["next_start_line"]
        self.assertTrue(host.execute({"action":"fork_ready", "expected_candidate_id":host.state.candidate.candidate_id})["accepted"])

    def test_empty_and_beyond_eof_have_distinct_acquisition_meanings(self):
        host = executor({"empty.txt":b"", "data.txt":b"a\nb\n"})
        self.assertTrue(host.execute({"action":"read", "path":"empty.txt", "start_line":2})["complete"])
        self.assertNotIn("empty.txt", host.state.complete_reads)
        self.assertTrue(host.execute({"action":"read", "path":"empty.txt", "start_line":1})["accepted"])
        self.assertIn("empty.txt", host.state.complete_reads)
        self.assertTrue(host.execute({"action":"read", "path":"data.txt", "start_line":20})["complete"])
        self.assertNotIn("data.txt", host.state.complete_reads)
        self.assertNotIn("data.txt", host.state.read_coverage)

    def test_exact_recovery_size_boundary(self):
        host = executor()
        sample = {"accepted":True, "content":"a"*21000}
        difference = MAX_RESULT_BYTES-len(canonical_json_bytes(envelope(canonical_json_bytes(sample))))
        sample["content"] += "a"*difference
        self.assertEqual(len(canonical_json_bytes(envelope(canonical_json_bytes(sample)))), MAX_RESULT_BYTES)
        self.assertIs(host._bounded(sample), sample)
        with self.assertRaisesRegex(ToolError, "exact-recovery"):
            host._bounded({**sample, "content":sample["content"]+"a"})

    def test_unrecoverable_import_rejected_before_advertising_handle(self):
        for kind, handle in (("reopenable","OBS-0001"), ("result_reopenable","RES-0001"), ("event_reopenable","EVT-0001")):
            with self.subTest(kind=kind):
                body = canonical_json_bytes({"old":'"'*15000, "new":"x"})
                supplied = {handle:body}
                with self.assertRaisesRegex(ToolError, "result bound"):
                    executor(**{kind:supplied})
                self.assertEqual(supplied, {handle:body})

    def test_legal_patch_with_unrecoverable_diff_does_not_mutate(self):
        surrounding = "\x00"*512+"\n"
        host = executor({"data.txt":(surrounding*3+"VALUE=1\n"+surrounding*3).encode()})
        host.state.prefork_check_passed = host.state.public_check_passed = True
        before = copy.deepcopy(host.state)
        result = host.execute(patch_action(host,"data.txt","VALUE=1","VALUE=2"))
        self.assertFalse(result["accepted"])
        self.assertIn("bound", result["detail"])
        self.assertEqual(host.state, before)

    def test_oversized_completed_check_does_not_credit_passing_flag(self):
        host = executor()
        output = {"passed":True, "returncode":0, "stdout":"\x00"*6000, "stderr":""}
        with mock.patch.object(module,"run_checker",return_value=output) as check:
            result = host.execute({"action":"check", "check_id":"public", "expected_candidate_id":host.state.candidate.candidate_id})
        check.assert_called_once()  # Execution is not rolled back or claimed absent.
        self.assertFalse(result["accepted"])
        self.assertFalse(host.state.public_check_passed)

    def test_rejected_stateful_return_does_not_commit_flag(self):
        for kind in ("probe", "fork_ready", "submit"):
            with self.subTest(kind=kind):
                host = executor(probe_id="p", probe_body="payload")
                host.state.stage = "continuation" if kind=="submit" else "prefix"
                host.state.prefork_check_passed, host.state.probe_done = True, kind=="fork_ready"
                action = ({"action":kind,"probe_id":"p"} if kind=="probe" else
                          {"action":kind,"expected_candidate_id":host.state.candidate.candidate_id})
                before = copy.deepcopy(host.state)
                with reject_accepted(host):
                    self.assertFalse(host.execute(action)["accepted"])
                self.assertEqual(host.state, before)

    def test_history_survives_edit_without_claiming_current_file_inspection(self):
        host = executor({"a.txt":b"one\n", "b.txt":b"other\n"})
        history = {p:host.execute({"action":"read", "path":p, "start_line":1}) for p in ("a.txt","b.txt")}
        host.state.public_check_passed = True
        result = host.execute(patch_action(host,"a.txt","one","two"))
        self.assertTrue(result["accepted"])
        self.assertFalse(host.state.public_check_passed)
        self.assertEqual(host.state.complete_reads, {"a.txt","b.txt"})  # Historical acquisition only.
        self.assertNotEqual(history["a.txt"]["file_sha256"], host.state.candidate.file_sha256("a.txt"))
        self.assertEqual(history["b.txt"]["file_sha256"], host.state.candidate.file_sha256("b.txt"))
        self.assertNotEqual(history["b.txt"]["candidate_id"], host.state.candidate.candidate_id)
