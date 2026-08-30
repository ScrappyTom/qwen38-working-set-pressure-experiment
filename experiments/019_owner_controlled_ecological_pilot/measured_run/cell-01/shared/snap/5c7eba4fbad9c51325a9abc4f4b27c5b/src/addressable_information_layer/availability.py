"""Human-readable availability audit derived from offline receipts."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from .serialization import to_plain

if TYPE_CHECKING:
    from .runner import FixtureRunResult


def build_availability_audit(result: "FixtureRunResult") -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    readiness_by_call = {
        receipt.model_call_id: result.readiness_decisions[index]
        for index, receipt in enumerate(result.context_receipts)
        if index < len(result.readiness_decisions)
    }

    disposition_totals: Counter[str] = Counter()
    info_need_totals: Counter[str] = Counter()
    criteria_totals: Counter[str] = Counter()
    summary_claim_failures: list[dict[str, Any]] = []

    for receipt in result.context_receipts:
        dispositions = Counter(item.get("disposition", "unknown") for item in receipt.candidate_dispositions)
        disposition_totals.update(dispositions)
        info_need = receipt.information_need_classification.get("classification", "unknown")
        info_need_totals.update([info_need])
        criteria_classes = Counter(item.get("classification", "unknown") for item in receipt.criterion_classifications)
        criteria_totals.update(criteria_classes)
        failed_claims = [item for item in receipt.summary_claim_audit if item.get("status") == "failed"]
        summary_claim_failures.extend(failed_claims)

        readiness = readiness_by_call.get(receipt.model_call_id)
        calls.append(
            {
                "model_call_id": receipt.model_call_id,
                "current_focus_ref": receipt.current_focus_ref,
                "information_need": dict(receipt.information_need_classification),
                "availability_class": _availability_class(dispositions, info_need),
                "disposition_counts": dict(sorted(dispositions.items())),
                "blocked_missing": [
                    item
                    for item in receipt.candidate_dispositions
                    if item.get("disposition") == "block_if_missing"
                ],
                "criteria_classes": dict(sorted(criteria_classes.items())),
                "summary_claim_failures": failed_claims,
                "readiness": to_plain(readiness) if readiness is not None else None,
            }
        )

    return {
        "episode_id": result.audit_report.episode_id,
        "report_id": result.audit_report.report_id,
        "passed": result.audit_report.passed,
        "model_call_count": len(result.context_receipts),
        "artifact_count": len(result.artifacts),
        "layer0_event_count": len(result.log.events),
        "availability_totals": dict(sorted(disposition_totals.items())),
        "information_need_totals": dict(sorted(info_need_totals.items())),
        "criterion_class_totals": dict(sorted(criteria_totals.items())),
        "readiness_totals": dict(
            sorted(Counter(decision.status.value for decision in result.readiness_decisions).items())
        ),
        "summary_claim_failure_count": len(summary_claim_failures),
        "calls": calls,
    }


def render_markdown_report(result: "FixtureRunResult") -> str:
    audit = build_availability_audit(result)
    lines = [
        f"# Offline Audit Summary: {audit['episode_id']}",
        "",
        f"- Report: `{audit['report_id']}`",
        f"- Passed: `{str(audit['passed']).lower()}`",
        f"- Model calls: `{audit['model_call_count']}`",
        f"- Artifacts: `{audit['artifact_count']}`",
        f"- Layer 0 events: `{audit['layer0_event_count']}`",
        "",
        "## Availability",
        "",
        _format_counts("Candidate dispositions", audit["availability_totals"]),
        _format_counts("Information needs", audit["information_need_totals"]),
        _format_counts("Criterion classes", audit["criterion_class_totals"]),
        _format_counts("Readiness decisions", audit["readiness_totals"]),
        f"- Summary claim failures: `{audit['summary_claim_failure_count']}`",
        "",
        "## Calls",
        "",
    ]
    for call in audit["calls"]:
        readiness = call["readiness"] or {}
        info_need = call["information_need"]
        lines.extend(
            [
                f"### {call['model_call_id']}",
                "",
                f"- Availability: `{call['availability_class']}`",
                f"- Information need: `{info_need.get('classification', 'unknown')}` - {info_need.get('reason', '')}",
                f"- Readiness: `{readiness.get('response_type', 'none')}` / `{readiness.get('status', 'none')}`",
                f"- Readiness reason: {readiness.get('reason', '')}",
                _format_counts("Dispositions", call["disposition_counts"]),
                _format_counts("Criteria", call["criteria_classes"]),
            ]
        )
        if call["blocked_missing"]:
            lines.append("- Blocked missing:")
            for item in call["blocked_missing"]:
                lines.append(f"  - `{item.get('path_or_name')}`: {item.get('reason_code')}")
        if call["summary_claim_failures"]:
            lines.append("- Summary claim failures:")
            for item in call["summary_claim_failures"]:
                lines.append(f"  - `{item.get('summary_id')}`: {item.get('reason')}")
        lines.append("")

    if result.audit_report.failures:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in result.audit_report.failures)
        lines.append("")

    lines.extend(["## Findings", ""])
    lines.extend(f"- {finding}" for finding in result.audit_report.findings)
    lines.append("")
    return "\n".join(lines)


def _availability_class(dispositions: Counter[str], info_need: str) -> str:
    if dispositions.get("block_if_missing") or info_need == "insufficient_context":
        return "missing_or_blocked"
    if dispositions.get("show_exact"):
        return "show_exact"
    if dispositions.get("show_card"):
        return "show_card"
    if dispositions.get("available_by_handle"):
        return "available_by_handle"
    if info_need == "needs_decomposition":
        return "needs_decomposition"
    return "unknown"


def _format_counts(label: str, counts: dict[str, int]) -> str:
    if not counts:
        return f"- {label}: none"
    formatted = ", ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))
    return f"- {label}: {formatted}"
