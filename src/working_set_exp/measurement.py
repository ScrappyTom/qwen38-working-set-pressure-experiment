from __future__ import annotations

from typing import Any


def check_opportunity(*, calls_used: int, call_limit: int, result: dict[str, Any]) -> dict[str, Any]:
    """Measure action allowance at a check, without changing execution policy.

    The attempted check consumes one call even if rejected. A numeric allowance
    does not establish physical context admission or that the host offered the
    next request; those remain separate host-path findings.
    """
    if type(calls_used) is not int or type(call_limit) is not int or not 0 <= calls_used < call_limit:
        raise ValueError("a check attempt must have positive remaining action allowance")
    before = call_limit - calls_used
    failed = result.get("accepted") is True and result.get("passed") is False
    return {
        "basis": "action_allowance_only_not_runtime_admission",
        "calls_remaining_before": before,
        "calls_remaining_after": before - 1,
        "accepted": result.get("accepted"),
        "passed": result.get("passed"),
        "check_patch_recheck_submit_fits_before": before >= 4,
        "patch_recheck_submit_fits_after_failure": before - 1 >= 3 if failed else None,
    }


def check_opportunities(pairs: list[dict[str, Any]], *, call_limit: int) -> list[dict[str, Any]]:
    """For an ordered complete action history, record first and later checks."""
    rows = []
    for sequence, pair in enumerate(pairs, 1):
        if pair["response"].get("action") == "check":
            rows.append({
                "sequence": sequence,
                "first_check": not rows,
                **check_opportunity(calls_used=sequence - 1, call_limit=call_limit, result=pair["result"]),
            })
    return rows
