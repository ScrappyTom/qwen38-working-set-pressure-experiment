import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.working_session import WorkingSession, INPUT_LIMIT, CONTROL_ROOM
from working_set_exp import working_view

ROOT = Path(__file__).resolve().parents[1]


def cheap_count(view):
    """Deterministic test meter, not a claim about native model token counts."""
    return len(canonical_json_bytes(view)) // 3 + 1000


def session(files=None, pairs=()):
    return WorkingSession(Candidate.create(files or {"app.py": b"value = 1\n"}, max_file_bytes=1_048_576),
                          b"from app import value\nassert value == 2\n", "Repair, check, submit.",
                          pairs=pairs, call_limit=100)


def act(s, action, meter=cheap_count):
    s.mark_delivered(s.view())
    return s.execute(action, meter)


def read(s, path="app.py", first=1, last=0, meter=cheap_count):
    return act(s, dict(action="read", path=path, start_line=first, end_line=last), meter)


def edit(s, old, new, path="app.py", meter=cheap_count):
    return act(s, dict(action="patch", path=path, old=old, new=new,
                       expected_candidate_id=s.candidate.candidate_id,
                       expected_file_sha256=s.candidate.file_sha256(path)), meter)


class WorkingSessionTests(unittest.TestCase):
    def test_history_floor_does_not_grow_with_all_records(self):
        pair = dict(response=dict(action="read", path="app.py", start_line=1),
                    result=dict(accepted=True, path="app.py", content="secret historical source"))
        short, long = session(pairs=[pair]*100), session(pairs=[pair]*10_000)
        a, b = canonical_json_bytes(short.view()), canonical_json_bytes(long.view())
        self.assertLess(abs(len(a)-len(b)), 80)
        self.assertEqual(len(long.view()["recent_activity"]), 6)
        self.assertNotIn(b"secret historical source", b)
        result = act(long, dict(action="history", before=15, path="app.py"))
        self.assertEqual([r["sequence"] for r in result["entries"]], list(range(14,6,-1)))
        self.assertEqual(result["next_before"], 7)
        self.assertEqual(json.loads(long.payload("RES-0001")), pair["result"])

    def test_complete_natural_edit_and_source_refresh(self):
        s = session()
        self.assertTrue(read(s)["accepted"])
        new = "value = 2\n" + "# preserves a complete logical contribution\n"*35
        self.assertGreater(len(new), 512)
        before = s.candidate.candidate_id
        result = edit(s, "value = 1\n", new)
        self.assertTrue(result["accepted"])
        self.assertEqual(s.candidate.file_map["app.py"], new.encode())
        self.assertEqual(s.sources()[0]["content"], new)
        self.assertEqual(result["previous_candidate_id"], before)
        self.assertEqual(result["replaced_source_lines"], [1,1])
        self.assertEqual(result["replacement_source_lines"], [1,len(new.splitlines())])
        self.assertEqual(s.view()["candidate_limits"]["max_line_utf8_bytes"],512)
        self.assertIn("+value = 2", s.diffs[2])
        self.assertEqual(json.loads(s.payload("EVT-0002"))["new"], new)

    def test_actual_540_character_plan_is_one_atomic_edit(self):
        run = ROOT / "development/configparser_backport/run-001"
        original = json.loads((run/"after/C10-candidate.json").read_bytes())
        files = {f["path"]: f["content_utf8"].encode() for f in original["files"]}
        s = session(files)
        text = (run/"calls/C11-assistant-reasoning.txt").read_text(encoding="utf-8")
        action, _ = json.JSONDecoder().raw_decode(text[text.index('{"action":"patch"'):])
        self.assertEqual(len(action["new"]), 540)
        self.assertEqual(s.candidate.candidate_id, action["expected_candidate_id"])
        read(s, "Lib/configparser.py", 280, 345)
        result = act(s, action)
        self.assertTrue(result["accepted"])
        source = s.candidate.file_map["Lib/configparser.py"].decode()
        expected = files["Lib/configparser.py"].decode().replace(action["old"], action["new"], 1)
        self.assertEqual(source, expected)
        namespace = {"__name__": "offline_whole_edit"}
        exec(compile(source, "Lib/configparser.py", "exec"), namespace)
        namespace["ConfigParser"]()
        self.assertIn("_UNSET", namespace)

    def test_stale_and_unread_edits_do_not_mutate(self):
        s = session()
        before = s.candidate
        self.assertFalse(edit(s, "value = 1", "value = 2")["accepted"])
        self.assertEqual(s.candidate, before)
        read(s)
        old_guard = dict(action="patch", path="app.py", old="value = 1", new="value = 3",
                         expected_candidate_id=before.candidate_id, expected_file_sha256=before.file_sha256("app.py"))
        self.assertTrue(edit(s, "value = 1", "value = 2")["accepted"])
        current = s.candidate
        self.assertFalse(act(s, old_guard)["accepted"])
        self.assertEqual(s.candidate, current)

    def test_edit_capacity_rejection_commits_neither_source_nor_views(self):
        s = session()
        read(s)
        before, views = s.candidate, copy.deepcopy(s.ranges)
        meter = lambda view: 999_999 if view["candidate_id"] != before.candidate_id else 500
        self.assertFalse(edit(s, "value = 1", "value = 2", meter=meter)["accepted"])
        self.assertEqual(s.candidate, before)
        self.assertEqual(s.ranges, views)
        self.assertEqual(s.diffs, {})
        self.assertEqual(set(s.versions), {before.candidate_id})

    def test_group_survives_other_operations_and_fits_pages(self):
        data = ("value = 1  # " + "quoted \\\""*20 + "\n").encode()*400
        s = session({"app.py": data, "rule.txt": b"Preserve prior contributions.\n"})
        result = act(s, dict(action="work_on", sources=[dict(path="app.py", start_line=1, end_line=0),
            dict(path="rule.txt", start_line=1, end_line=0)], results=[]))
        self.assertTrue(result["accepted"])
        self.assertIsNotNone(result["sources"][0]["next_start_line"])
        self.assertLessEqual(cheap_count(s.view()), INPUT_LIMIT-CONTROL_ROOM)
        original = s.sources()
        self.assertTrue(act(s, dict(action="tree", path=".", offset=0, limit=8))["accepted"])
        self.assertEqual(s.sources(), original)
        self.assertEqual({v["path"] for v in s.view()["working_set"]["sources"]}, {"app.py", "rule.txt"})

    def test_rejected_read_has_no_acquisition_state(self):
        s = session()
        meter = lambda view: 999_999 if view["working_set"]["sources"] or (
            view["latest_feedback"] and "source" in view["latest_feedback"]["result"]) else 500
        self.assertFalse(read(s, meter=meter)["accepted"])
        self.assertEqual(s.ranges, [])
        self.assertNotIn("source", s.pairs[-1]["result"])

    def test_paged_exact_recovery_of_large_escaped_result(self):
        original = dict(accepted=True, text=('\\"雪\n'*15_000))
        s = session(pairs=[dict(response=dict(action="check"), result=original)])
        body, offset = canonical_json_bytes(original), 0
        parts = []
        for _ in range(20):
            result = act(s, dict(action="reopen_result", handle="RES-0001", offset=offset))
            self.assertTrue(result["accepted"])
            self.assertEqual(result["sha256"], sha256_bytes(body))
            parts.append(result["exact_utf8"].encode())
            self.assertLessEqual(cheap_count(s.view()), INPUT_LIMIT-CONTROL_ROOM)
            if result["next_offset"] is None:
                break
            self.assertGreater(result["next_offset"], offset)
            offset = result["next_offset"]
        else:
            self.fail("exact recovery did not finish")
        self.assertGreater(len(parts), 1)
        self.assertEqual(b"".join(parts), body)
        self.assertEqual(s.payload("RES-0001"), body)

    def test_delete_last_line_and_empty_file(self):
        for original, old, expected in ((b"a\nb\n", "b\n", b"a\n"), (b"a\n", "a\n", b"")):
            with self.subTest(original=original):
                s = session({"app.py": original})
                read(s, first=len(original.splitlines()), last=len(original.splitlines()))
                result=edit(s, old, "")
                self.assertTrue(result["accepted"])
                self.assertEqual(result["replacement_source_lines"],[])
                self.assertEqual(s.candidate.file_map["app.py"], expected)
                self.assertEqual(s.sources()[0]["content"].encode(), expected)

    def test_check_applicability_submission_and_saved_history(self):
        s = session()
        read(s)
        self.assertFalse(act(s, dict(action="submit", expected_candidate_id=s.candidate.candidate_id))["accepted"])
        self.assertTrue(edit(s, "value = 1", "value = 2")["accepted"])
        check = act(s, dict(action="check", check_id="public", expected_candidate_id=s.candidate.candidate_id))
        self.assertTrue(check["passed"])
        old = s.candidate.candidate_id
        self.assertTrue(edit(s, "value = 2", "value = 2  # saved")["accepted"])
        self.assertEqual(s.check_state()["candidate_id"], old)
        self.assertFalse(s.check_state()["applies_to_current"])
        self.assertFalse(act(s, dict(action="submit", expected_candidate_id=s.candidate.candidate_id))["accepted"])
        self.assertTrue(act(s, dict(action="check", check_id="public", expected_candidate_id=s.candidate.candidate_id))["passed"])
        self.assertTrue(act(s, dict(action="submit", expected_candidate_id=s.candidate.candidate_id))["accepted"])
        self.assertTrue(s.submitted)

    def test_large_check_feedback_preserves_real_result_and_status(self):
        s = session()
        read(s)
        actual = dict(accepted=True, passed=False, check_id="public", checked_candidate_id=s.candidate.candidate_id,
                      stdout="x"*100_000, stderr="", returncode=1)
        with patch.object(WorkingSession, "_ordinary", return_value=actual):
            result = act(s, dict(action="check", check_id="public", expected_candidate_id=s.candidate.candidate_id))
        self.assertEqual(result, actual)
        self.assertEqual(json.loads(s.payload("RES-0002")), actual)
        self.assertEqual(s.last["output_scope"], "status_only_full_result_archived")
        self.assertFalse(s.last["result"]["passed"])
        self.assertEqual(s.sources()[0]["content"], "value = 1\n")

    def test_schema_reference_complete_and_rejects_unknown_arguments(self):
        forms = working_view.schema()["json_schema"]["schema"]["oneOf"]
        prompt = working_view.system_prompt()
        for form in forms:
            self.assertIn(canonical_json_bytes(form).decode(), prompt)
        s = session()
        before = s.candidate
        self.assertFalse(act(s, dict(action="read", path="app.py", start_line=True, end_line=0))["accepted"])
        self.assertFalse(act(s, dict(action="work_on", sources=[dict(path="app.py", start_line=1, end_line=0, extra=1)], results=[]))["accepted"])
        self.assertEqual(s.candidate, before)
        self.assertNotIn('"maxLength":512', prompt)


if __name__ == "__main__":
    unittest.main()
