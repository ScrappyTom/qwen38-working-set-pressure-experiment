"""Run fixture packs that contain multiple expected offline probes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .records import DeltaStatus
from .runner import run_fixture_data
from .serialization import to_plain


def run_fixture_pack(path: str | Path) -> dict[str, Any]:
    pack_path = Path(path)
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    case_reports = []
    for case in pack.get("cases", []):
        case_id = case.get("case_id", "case")
        if "fixture" not in case:
            case_reports.append(
                {
                    "case_id": case_id,
                    "passed": False,
                    "reason": "case has no fixture; this pack may be a seed pack, not an executable fixture pack",
                }
            )
            continue
        result = run_fixture_data(case["fixture"])
        expectation = _check_expectations(result, case.get("expect", {}))
        case_reports.append(
            {
                "case_id": case_id,
                "passed": expectation["passed"],
                "reason": expectation["reason"],
                "audit_passed": result.audit_report.passed,
                "report_id": result.audit_report.report_id,
                "readiness": [to_plain(decision) for decision in result.readiness_decisions],
                "information_need": result.context_receipts[0].information_need_classification
                if result.context_receipts
                else {},
                "candidate_dispositions": result.context_receipts[0].candidate_dispositions
                if result.context_receipts
                else [],
                "rejected_delta_refs": [delta.delta_id for delta in result.state_deltas if delta.status == DeltaStatus.REJECTED],
            }
        )
    return {
        "pack_id": pack.get("pack_id", pack_path.stem),
        "path": str(pack_path),
        "case_count": len(case_reports),
        "passed": all(case.get("passed") for case in case_reports),
        "cases": case_reports,
    }


def _check_expectations(result, expect: dict[str, Any]) -> dict[str, Any]:
    if not expect:
        return {"passed": True, "reason": "no explicit expectations"}
    failures: list[str] = []
    if "readiness" in expect:
        expected = expect["readiness"]
        decision = next(
            (item for item in result.readiness_decisions if item.response_type.value == expected.get("response_type")),
            None,
        )
        if decision is None:
            failures.append(f"missing readiness for {expected.get('response_type')}")
        else:
            if decision.status.value != expected.get("status"):
                failures.append(f"readiness status {decision.status.value} != {expected.get('status')}")
            if decision.route.value != expected.get("route"):
                failures.append(f"readiness route {decision.route.value} != {expected.get('route')}")
    if "information_need_classification" in expect:
        actual = (
            result.context_receipts[0].information_need_classification.get("classification")
            if result.context_receipts
            else None
        )
        if actual != expect["information_need_classification"]:
            failures.append(f"information need {actual} != {expect['information_need_classification']}")
    if "candidate_disposition" in expect:
        dispositions = {
            item.get("disposition")
            for receipt in result.context_receipts
            for item in receipt.candidate_dispositions
        }
        if expect["candidate_disposition"] not in dispositions:
            failures.append(f"candidate disposition {expect['candidate_disposition']} missing")
    if "rejected_delta_contains" in expect:
        rejected_reasons = [delta.reason for delta in result.state_deltas if delta.status == DeltaStatus.REJECTED]
        if not any(expect["rejected_delta_contains"] in reason for reason in rejected_reasons):
            failures.append(f"rejected delta reason missing {expect['rejected_delta_contains']}")
    return {"passed": not failures, "reason": "; ".join(failures) if failures else "expectations satisfied"}
