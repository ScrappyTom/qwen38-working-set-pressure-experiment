"""Actual edit custody and bounded immediate-delta CPU qualification."""
import copy
import json
import unittest

import test_navigation as t


def read_source(s,path="a.py",first=1,last=0):
    result=s.execute(dict(action="read",path=path,start_line=first,end_line=last),lambda v:0)
    assert result["accepted"]
    s.mark_delivered(s.view())
    return result["source"]


def patch(s,old="return 1",new="return 2"):
    return dict(action="patch",path="a.py",old=old,new=new,
                expected_candidate_id=s.candidate.candidate_id,
                expected_file_sha256=s.candidate.file_sha256("a.py"))


class ChangeTests(unittest.TestCase):
    def test_actual_patch_is_preserved_in_result_and_independently_projected(self):
        s=t.session();read_source(s)
        action=patch(s);result=s.execute(action,lambda v:0);sequence=len(s.pairs)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["applied_diff"],s.diffs[sequence])
        self.assertEqual(json.loads(s.payload(f"RES-{sequence:04d}"))["applied_diff"],s.diffs[sequence])
        self.assertEqual(json.loads(s.payload(f"EVT-{sequence:04d}")),action)
        before=t.canonical_json_bytes(s.pairs)
        view=s.view();shown=view["latest_feedback"]["applied_change"]
        self.assertEqual(shown["diff_utf8"],result["applied_diff"])
        self.assertNotIn("applied_diff",view["latest_feedback"]["result"])
        self.assertEqual(shown["exact_result_handle"],f"RES-{sequence:04d}")
        self.assertEqual(shown["exact_result_field"],"applied_diff")
        self.assertEqual(t.canonical_json_bytes(s.pairs),before)

    def test_literal_actual_diff_includes_supplied_separator_but_proposal_does_not(self):
        s=t.session();source=read_source(s,last=1)
        action=dict(action="replace_region",region=source["region_ref"],
                    expected_candidate_id=s.candidate.candidate_id,new="def beta():")
        result=s.execute(action,lambda v:0)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["supplied_boundary_separator"],"\n")
        self.assertEqual(s.candidate.file_map["a.py"],b"def beta():\n    return 1\n")
        self.assertIn("+def beta():\n",result["applied_diff"])
        self.assertEqual(s.pairs[-1]["response"]["new"],"def beta():")
        self.assertEqual(s.view()["latest_feedback"]["applied_change"]["diff_utf8"],result["applied_diff"])

    def test_rejected_edit_has_no_applied_diff_or_change_projection(self):
        s=t.session();read_source(s);action=patch(s)
        action["expected_candidate_id"]="0"*64
        candidate=s.candidate.candidate_id
        result=s.execute(action,lambda v:0)
        self.assertFalse(result["accepted"])
        self.assertNotIn("applied_diff",result)
        self.assertNotIn("applied_change",s.view()["latest_feedback"])
        self.assertEqual(s.candidate.candidate_id,candidate)
        self.assertEqual(s.diffs,{})

    def test_large_diff_is_omitted_whole_but_exact_RES_recovery_remains(self):
        s=t.session()
        old="".join(f"item_{i:03d} = 1\n" for i in range(500))
        new=old.replace(" = 1\n"," = 2\n")
        s.candidate=t.Candidate.create({"a.py":old.encode()})
        s.versions[s.candidate.candidate_id]=s.candidate
        read_source(s)
        result=s.execute(patch(s,old,new),lambda v:0);seq=len(s.pairs)
        self.assertTrue(result["accepted"])
        self.assertGreater(len(result["applied_diff"].encode()),t.nav.IMMEDIATE_CHANGE_BYTES)
        detail=s.view()["latest_feedback"]["applied_change"]
        self.assertEqual(detail["detail_status"],"omitted_for_change_byte_allowance")
        self.assertNotIn("diff_utf8",detail)
        recovered=s.execute(dict(action="reopen_result",handle=f"RES-{seq:04d}",offset=0),lambda v:0)
        self.assertTrue(recovered["accepted"])
        self.assertIsNone(recovered["next_offset"])
        self.assertEqual(json.loads(recovered["exact_utf8"])["applied_diff"],result["applied_diff"])

    def test_immediate_change_outranks_navigation_and_all_optional_detail_can_yield(self):
        s=t.session();t.outline_then_account(s);read_source(s)
        result=s.execute(patch(s),lambda v:0)
        self.assertTrue(t.detailed(s.view()))
        self.assertTrue(s._fits_feedback(lambda v:23809 if any("navigation" in r for r in v["recent_activity"]) else 23808))
        self.assertEqual(s.last[t.nav.SETTING],-1)
        self.assertEqual(s.last[t.nav.CHANGE_SETTING],2)
        self.assertEqual(s.view()["latest_feedback"]["applied_change"]["diff_utf8"],result["applied_diff"])
        self.assertTrue(s._fits_feedback(lambda v:23809 if "diff_utf8" in v["latest_feedback"].get("applied_change",{}) else 23808))
        self.assertEqual(s.last[t.nav.CHANGE_SETTING],1)
        self.assertEqual(s.view()["latest_feedback"]["applied_change"]["detail_status"],"omitted_for_input_admission_budget")
        self.assertTrue(s._fits_feedback(lambda v:23809 if "applied_change" in v["latest_feedback"] else 23808))
        self.assertEqual(s.last[t.nav.CHANGE_SETTING],0)
        self.assertNotIn("applied_change",s.view()["latest_feedback"])
        self.assertFalse(s.recovery)
        self.assertNotIn("recent_activity_limit",s.last)

    def test_previously_feasible_edit_is_not_rejected_for_added_delta(self):
        s=t.session();read_source(s)
        result=s.execute(patch(s),lambda v:23809 if "applied_change" in v["latest_feedback"] else 23000)
        self.assertTrue(result["accepted"])
        self.assertIn(b"return 2",s.candidate.file_map["a.py"])
        self.assertEqual(s.last[t.nav.CHANGE_SETTING],0)
        self.assertNotIn("applied_change",s.view()["latest_feedback"])
        self.assertIn("applied_diff",s.pairs[-1]["result"])

    def test_diff_never_establishes_edit_eligibility_or_a_passing_check(self):
        s=t.session();read_source(s);s.execute(patch(s),lambda v:0)
        # Model-facing diff remains while a mechanically constructed state has no
        # selected current body. This probes authority, not an actor trajectory.
        s.ranges=[];view=s.view()
        self.assertIn("applied_change",view["latest_feedback"])
        s.mark_delivered(view)
        self.assertEqual(s.delivered_sources,[])
        self.assertFalse(view["verification"]["submission"]["eligible"])
        result=s.execute(patch(s,old="def alpha",new="def beta"),lambda v:0)
        self.assertFalse(result["accepted"])

    def test_preceding_receipt_helper_never_leaks_full_raw_diff(self):
        s=t.session();read_source(s);s.execute(patch(s),lambda v:0)
        previous=copy.deepcopy(s.last)
        s.execute(dict(action="record_account",text="Await actual check."),lambda v:0)
        shown=t.nav.present_receipts(s.view(),[previous])
        self.assertEqual(len(shown),1)
        self.assertNotIn("applied_diff",shown[0]["result"])
        self.assertNotIn(t.nav.SETTING,shown[0])
        self.assertNotIn(t.nav.CHANGE_SETTING,shown[0])
        self.assertIn("applied_diff",previous["result"])

    def test_historical_c19_uses_archived_diff_without_inventing_RES_access(self):
        wire=t.RUN/"calls/C19-wire-request.json"
        statepath=t.RUN/"after/C18-O01-state.json"
        records=[json.loads(line) for line in (t.RUN/"records.jsonl").read_bytes().splitlines()]
        for path in (wire,statepath):
            matching=[a for r in records for a in r["artifacts"] if a["path"]==path.relative_to(t.RUN).as_posix()]
            self.assertTrue(matching)
            self.assertTrue(all(a["sha256"]==t.sha256_bytes(path.read_bytes()) for a in matching))
        view=json.loads(t.read(wire)["messages"][1]["content"])["workspace"]
        state=t.read(statepath);before=t.canonical_json_bytes(state)
        self.assertNotIn("applied_diff",state["pairs"][26]["result"])
        result=t.nav.project_immediate_change(view,historical_diffs={int(k):v for k,v in state["diffs"].items()})
        shown=result["latest_feedback"]["applied_change"]
        self.assertEqual(shown["diff_utf8"],state["diffs"]["27"])
        self.assertNotIn("exact_result_handle",shown)
        self.assertIn("original_RES_has_no_applied_diff",shown["qualification_origin"])
        self.assertEqual(t.canonical_json_bytes(state),before)
        stripped=copy.deepcopy(result);stripped["latest_feedback"].pop("applied_change")
        self.assertEqual(stripped,view)


if __name__=="__main__":
    unittest.main()
