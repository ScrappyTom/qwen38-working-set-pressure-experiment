"""CPU-only exact-state and transition qualification; no native/model/checker calls."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

AREA = Path(__file__).resolve().parents[1]
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("navigation_candidate", AREA / "navigation.py")
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.observations import ObservationStore

RUN = ROOT / "development/workload_requalification/small_repairs/artifact_map/run-001"
STATES = {"C04":"C03-O02", "C05":"C04-O01", "C06":"C05-O02", "C07":"C06-O01",
          "C08":"C07-O02", "C09":"C08-O01", "C10":"C09-O02", "C16":"C15-O02"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_from(path):
    value = read(path)
    result = Candidate.create({r["path"]:r["content_utf8"].encode() for r in value["files"]},
                              max_file_bytes=value["max_file_bytes"])
    assert result.candidate_id == value["candidate_id"]
    return result


def saved_case(tag):
    wire = RUN / f"calls/{tag}-wire-request.json"
    request = read(wire)
    state = read(RUN / f"after/{STATES[tag]}-state.json")
    view = json.loads(request["messages"][1]["content"])["workspace"]
    # Verify the source wire and checkpoint against actual recorded custody, not
    # a reconstructed prompt guessed from diagnostics. The live log is read-only.
    wanted = {wire.relative_to(RUN).as_posix(), f"after/{STATES[tag]}-state.json"}
    found = set()
    for line in (RUN / "records.jsonl").read_bytes().splitlines():
        record = json.loads(line)
        for artifact in record["artifacts"]:
            if artifact["path"] in wanted:
                data = (RUN / artifact["path"]).read_bytes()
                assert len(data) == artifact["size_bytes"] and sha256_bytes(data) == artifact["sha256"]
                found.add(artifact["path"])
    assert found == wanted
    candidate = candidate_from(RUN / "starting-candidate.json")
    assert state["candidate_id"] == view["candidate_id"] == candidate.candidate_id
    return view, state["pairs"], candidate


def session():
    candidate = Candidate.create({"a.py":b"def alpha():\n    return 1\n", "b.py":b"answer = 1\n"})
    return nav.NavigationSession(candidate, {"public":b"# not executed"}, "Inspect and repair.",
        edit_checks={}, observations=ObservationStore(AREA / "not-executed", replay=True),
        call_limit=20000, request_limit=100)


def outline_then_account(s):
    outcome = s.execute(dict(action="p0_page",path="a.py",offset=0), lambda v: 0)
    s.execute(dict(action="record_account",text="Question remains open."),lambda v:0)
    return outcome


def detailed(view):
    return [r for r in view["recent_activity"]
            if r.get("navigation",{}).get("detail_status") == "complete_returned_navigation_page"]


class NavigationTests(unittest.TestCase):
    def test_saved_inputs_preserve_every_non_navigation_field_and_archive(self):
        for tag in STATES:
            with self.subTest(tag=tag):
                view,pairs,candidate = saved_case(tag)
                before,archive = canonical_json_bytes(view),canonical_json_bytes(pairs)
                projected = nav.project_navigation(view,pairs,candidate)
                stripped = copy.deepcopy(projected)
                for row in stripped["recent_activity"]:
                    row.pop("navigation",None)
                self.assertEqual(canonical_json_bytes(stripped),before)
                self.assertEqual(canonical_json_bytes(view),before)
                self.assertEqual(canonical_json_bytes(pairs),archive)
                self.assertLessEqual(len(canonical_json_bytes(projected))-len(before),nav.NAVIGATION_BYTES)

    def test_c10_retains_outline_and_second_directory_page(self):
        view,pairs,candidate = saved_case("C10")
        rows = {r["sequence"]:r for r in nav.project_navigation(view,pairs,candidate)["recent_activity"]}
        self.assertEqual(rows[12]["navigation"]["observed_page"]["total_entries"],4)
        entries = rows[12]["navigation"]["observed_page"]["entries"]
        self.assertEqual(entries[2]["name"],"apply_patch_preview")
        self.assertEqual(entries[2]["start_line"],80)
        self.assertTrue(entries[2]["source_reference"]["file_matches_current"])
        self.assertEqual(rows[9]["navigation"]["observed_page"]["offset"],16)
        self.assertEqual(rows[14]["navigation"]["detail_status"],"already_in_latest_feedback")
        self.assertEqual(rows[11]["navigation"]["detail_status"],"duplicate_returned_page")
        self.assertEqual(rows[11]["navigation"]["shown_at_sequence"],14)

    def test_c09_deduplicates_already_visible_outline_without_claiming_it_was_absent(self):
        view,pairs,candidate = saved_case("C09")
        result = nav.project_navigation(view,pairs,candidate)
        row = next(r for r in result["recent_activity"] if r["sequence"]==12)
        self.assertEqual(row["navigation"]["detail_status"],"already_in_latest_feedback")
        self.assertEqual(result["latest_feedback"],view["latest_feedback"])

    def test_c16_restores_exact_known_directory_entries_with_their_version(self):
        view,pairs,candidate = saved_case("C16")
        rows = nav.project_navigation(view,pairs,candidate)["recent_activity"]
        detail = next(r["navigation"] for r in rows if r["sequence"]==20)
        self.assertEqual(detail["observed_page"]["entries"],pairs[19]["result"]["entries"])
        self.assertEqual(detail["observed_page"]["next_offset"],16)
        self.assertEqual(detail["observed_page"]["total_entries"],25)
        self.assertEqual(detail["observed_candidate_id"],candidate.candidate_id)

    def test_latest_without_returned_references_does_not_suppress_complete_projection(self):
        view,pairs,candidate = saved_case("C09")
        view["latest_feedback"]["result"].pop("regions")
        projected = nav.project_navigation(view,pairs,candidate)
        row = next(r for r in projected["recent_activity"] if r["sequence"]==12)
        self.assertEqual(row["navigation"]["detail_status"],"complete_returned_navigation_page")
        self.assertIn("source_reference",row["navigation"]["observed_page"]["entries"][0])

    def test_search_and_rejected_navigation_unchanged(self):
        s = session()
        s.execute(dict(action="search",path="a.py",query="alpha",offset=0,limit=8),lambda v:0)
        rejected=s.execute(dict(action="tree",path="../absent",offset=0,limit=16),lambda v:0)
        self.assertFalse(rejected["accepted"])
        self.assertFalse(any("navigation" in r for r in s.view()["recent_activity"]))

    def test_outline_file_binding_survives_unrelated_edit_but_not_target_edit(self):
        s = session(); outline = outline_then_account(s)
        archive = canonical_json_bytes(s.pairs)
        original = s.candidate
        files = original.file_map; files["b.py"] = b"answer = 2\n"
        s.candidate = Candidate.create(files)
        detail = detailed(s.view())[0]["navigation"]
        self.assertFalse(detail["candidate_matches_current"])
        self.assertEqual(detail["observed_candidate_id"],original.candidate_id)
        self.assertTrue(detail["observed_page"]["entries"][0]["source_reference"]["file_matches_current"])
        s.resolve_region(outline["regions"][0]["region_ref"])
        files["a.py"] = b"# moved\ndef alpha():\n    return 1\n"
        s.candidate = Candidate.create(files)
        detail = detailed(s.view())[0]["navigation"]
        self.assertFalse(detail["observed_page"]["entries"][0]["source_reference"]["file_matches_current"])
        with self.assertRaisesRegex(ValueError,"stale"):
            s.resolve_region(outline["regions"][0]["region_ref"])
        self.assertEqual(canonical_json_bytes(s.pairs),archive)

    def test_directory_statistics_keep_observed_binding_after_edit(self):
        s = session()
        s.execute(dict(action="p0_page",path=".",offset=0),lambda v:0)
        s.execute(dict(action="record_account",text="Continue"),lambda v:0)
        old = s.candidate
        files=old.file_map;files["b.py"]=b"answer = 999\n"
        s.candidate=Candidate.create(files)
        result=detailed(s.view())[0]["navigation"]
        self.assertFalse(result["candidate_matches_current"])
        self.assertEqual(result["observed_candidate_id"],old.candidate_id)
        self.assertEqual(result["observation"],"historical_navigation_not_source")

    def test_navigation_does_not_establish_source_edit_authority(self):
        s = session();outline_then_account(s)
        s.mark_delivered(s.view())
        self.assertEqual(s.delivered_sources,[])
        before=s.candidate.candidate_id
        reply=s.execute(dict(action="patch",path="a.py",old="return 1",new="return 2",
            expected_candidate_id=before,expected_file_sha256=s.candidate.file_sha256("a.py")),lambda v:0)
        self.assertFalse(reply["accepted"])
        self.assertEqual(s.candidate.candidate_id,before)

    def test_complete_feedback_yields_navigation_before_history_or_recovery(self):
        s=session();outline_then_account(s)
        before=canonical_json_bytes(s.pairs)
        base_last=copy.deepcopy(s.view()["latest_feedback"])
        def crowded(view):
            return 23809 if any("navigation" in r for r in view["recent_activity"]) else 23808
        self.assertTrue(s._fits_feedback(crowded))
        self.assertEqual(s.last[nav.SETTING],-1)
        self.assertNotIn("recent_activity_limit",s.last)
        self.assertFalse(s.recovery)
        self.assertEqual(s.view()["latest_feedback"],base_last)
        self.assertEqual(canonical_json_bytes(s.pairs),before)
        s.mark_delivered(s.view())

    def test_rejection_and_selection_transition_keep_control_path(self):
        s=session();outline_then_account(s)
        def crowded(view):
            return 23809 if any("navigation" in r for r in view["recent_activity"]) else 23000
        result=s.execute(dict(action="read",path="missing.py",start_line=1,end_line=10),crowded)
        self.assertFalse(result["accepted"])
        self.assertFalse(s.delivery_blocked)
        self.assertEqual(s.view()["latest_feedback"]["result"],result)
        result=s.execute(dict(action="work_on",sources=[dict(path="a.py",start_line=1,end_line=2)],results=[]),crowded)
        self.assertTrue(result["accepted"])
        self.assertEqual(s.view()["working_set"]["sources"][0]["content"],"def alpha():\n    return 1\n")
        self.assertFalse(s.recovery)

    def test_clone_and_checkpoint_last_preserve_admitted_projection(self):
        s=session();outline_then_account(s)
        before=copy.deepcopy(s.last)
        cloned=s.clone()
        self.assertTrue(cloned._fits(lambda v:23809 if detailed(v) else 0,margin=0))
        self.assertEqual(s.last,before)
        restored=cloned.clone();restored.last=json.loads(json.dumps(cloned.last))
        self.assertEqual(restored.view(),cloned.view())
        self.assertNotIn(nav.SETTING,restored.view()["latest_feedback"])

    def test_many_archived_pages_do_not_grow_resident_navigation(self):
        s=session();outline_then_account(s)
        original=copy.deepcopy(s.pairs[0]);sizes=[]
        for count in (100,10000):
            pairs=[original]*count
            rows=[dict(sequence=i,result_handle=f"RES-{i:04d}",action="p0_page") for i in range(count-5,count+1)]
            base=dict(recent_activity=rows,latest_feedback=None)
            result=nav.project_navigation(base,pairs,s.candidate)
            self.assertEqual(len(detailed(result)),1)
            sizes.append(len(canonical_json_bytes(result))-len(canonical_json_bytes(base)))
        self.assertLessEqual(max(sizes)-min(sizes),24)
        self.assertTrue(all(n<=nav.NAVIGATION_BYTES for n in sizes))

    def test_oversized_page_is_omitted_whole_with_recovery_handle_preserved(self):
        s=session();outline_then_account(s)
        s.pairs[0]["result"]["entries"][0]["signature"]="def " + "symbol_"*5000
        view=s.view();row=view["recent_activity"][0]
        self.assertEqual(row["navigation"]["detail_status"],"omitted_for_navigation_byte_allowance")
        self.assertEqual(row["result_handle"],"RES-0001")
        self.assertNotIn("observed_page",row["navigation"])
        baseline=copy.deepcopy(view)
        for row in baseline["recent_activity"]:row.pop("navigation",None)
        self.assertEqual(nav.project_navigation(baseline,s.pairs,s.candidate,byte_limit=0),baseline)


if __name__=="__main__":
    unittest.main()
