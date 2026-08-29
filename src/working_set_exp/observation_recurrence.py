from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonutil import canonical_json_bytes, load_json_strict, sha256_file
from .recurrent_pressure import _ledger, _observation_case, _replace_case


EXPERIMENT_ID = "009_recurrent_observation_validity"
CASE_IDS = ("E9-OBS-ALPHA", "E9-OBS-BETA")
SEEDS = (173205, 223607)
OUTPUT_ROOT = r"C:\e9-primary"
DEVELOPMENT_OUTPUT_ROOT = r"C:\e9-dev"
FINAL_DEVELOPMENT_OUTPUT_ROOT = r"C:\e9-final-dev"
FINAL_DEVELOPMENT_V2_OUTPUT_ROOT = r"C:\e9-final-dev2"
MAXIMUM_HTTP_COMPLETION_CALLS = 160
AUTHORIZATION_SCHEMA = "experiment-009-recurrent-observation-authorization-v1"


def _fresh_observation_case(
    *,
    fixture_id: str,
    namespace: str,
    label_name: str,
    header_name: str,
    codec_name: str,
    archive_names: tuple[str, str, str],
    bridge_names: tuple[str, str, str, str],
    marker_v1: str,
    marker_v2: str,
) -> dict[str, Any]:
    """Create a lexical sibling without changing the earned interaction surface."""
    replacements = (
        ("E7-OBSERVATION", fixture_id),
        ("K4::", marker_v1),
        ("M7::", marker_v2),
        ("iris", archive_names[0]),
        ("juniper", archive_names[1]),
        ("kestrel", archive_names[2]),
        ("lumen", bridge_names[0]),
        ("marrow", bridge_names[1]),
        ("nylon", bridge_names[2]),
        ("osprey", bridge_names[3]),
        ("session_label", label_name),
        ("session_header", header_name),
        ("encoded_session", codec_name),
        ("session/label.py", f"{namespace}/label.py"),
        ("session/header.py", f"{namespace}/header.py"),
        ("session/wire.py", f"{namespace}/wire.py"),
        ("session.label", f"{namespace}.label"),
        ("session.header", f"{namespace}.header"),
        ("session.wire", f"{namespace}.wire"),
        ("session_marker", f"{namespace}_marker"),
        ("session", namespace),
    )
    case = _replace_case(_observation_case(), replacements)

    # Two complete custody files retain the same pressure mass as the old four-
    # file geometry while leaving four of twelve Phase-B actions as genuine
    # behavioral headroom. The removed files are not hidden distractors.
    keep_bridges = bridge_names[:2]
    for name in bridge_names[2:]:
        del case["files"][f"bridge/{name}.py"]
    for index, name in enumerate(keep_bridges):
        case["files"][f"bridge/{name}.py"] = _ledger(
            name,
            f"R{fixture_id[-1]}{index}",
            rows=192,
        )
    case["phase_b_required"] = tuple(f"bridge/{name}.py" for name in keep_bridges)

    archive_text = ", ".join(f"`archive/{name}.py`" for name in archive_names)
    bridge_text = " and ".join(f"`bridge/{name}.py`" for name in keep_bridges)
    phase_b = (
        f"Phase B: reopen the exact current `{namespace}` compatibility observation from Phase A and repair "
        f"`{namespace}/label.py` so it prepends that marker. Then run check `public`. After the mutation, call "
        f"compatibility probe `{namespace}` again to capture the current candidate-bound marker. Read both exact "
        f"bridge custody files completely: {bridge_text}. Call `fork_ready`. Do not change the Phase C target "
        "before that boundary."
    )
    phase_c = (
        f"Phase C: repair `{namespace}/header.py` so it prepends the exact marker from the compatibility observation "
        "valid for the current candidate. An older observation remains available but is stale. Use the candidate "
        f"bindings and reopen exact evidence before mutation. Preserve trimming, case folding, and `{namespace}/wire.py` "
        "ASCII behavior. Run check `public` and submit."
    )
    case["phase_b"] = phase_b
    case["phase_c"] = phase_c
    case["task"] = (
        f"Perform Phase A, Phase B, and Phase C in order. Phase A: read each exact custody file completely: {archive_text}. "
        "Then repair `stage/ready.py` so `completed_groups()` returns the number of `PHASE_A_GROUPS`, run check "
        f"`prefork`, call compatibility probe `{namespace}` on that current candidate, and call `fork_ready`. Do not "
        f"change Phase B or C targets before their stated boundary. {phase_b} {phase_c}"
    )
    return case


def case_definitions() -> tuple[dict[str, Any], ...]:
    alpha = _fresh_observation_case(
        fixture_id=CASE_IDS[0],
        namespace="beacon",
        label_name="beacon_label",
        header_name="beacon_header",
        codec_name="encoded_beacon",
        archive_names=("cedar", "fir", "pine"),
        bridge_names=("amber", "brass", "copper", "silver"),
        marker_v1="C3%%",
        marker_v2="N9%%",
    )
    beta = _fresh_observation_case(
        fixture_id=CASE_IDS[1],
        namespace="pulse",
        label_name="pulse_label",
        header_name="pulse_header",
        codec_name="encoded_pulse",
        archive_names=("aspen", "willow", "yew"),
        bridge_names=("cobalt", "indigo", "ochre", "umber"),
        marker_v1="L6!!",
        marker_v2="P4!!",
    )
    return alpha, beta


def development_case_definition() -> dict[str, Any]:
    return _fresh_observation_case(
        fixture_id="E9-DEV-OBS-GAMMA",
        namespace="relay",
        label_name="relay_label",
        header_name="relay_header",
        codec_name="encoded_relay",
        archive_names=("acacia", "larch", "spruce"),
        bridge_names=("crimson", "saffron", "teal", "violet"),
        marker_v1="D5##",
        marker_v2="T2##",
    )


def final_development_case_definition() -> dict[str, Any]:
    return _fresh_observation_case(
        fixture_id="E9-DEV-OBS-DELTA",
        namespace="gateway",
        label_name="gateway_label",
        header_name="gateway_header",
        codec_name="encoded_gateway",
        archive_names=("hemlock", "magnolia", "sequoia"),
        bridge_names=("cerulean", "scarlet", "tan", "viridian"),
        marker_v1="F7&&",
        marker_v2="V3&&",
    )


def final_development_v2_case_definition() -> dict[str, Any]:
    return _fresh_observation_case(
        fixture_id="E9-DEV-OBS-EPSILON",
        namespace="portal",
        label_name="portal_label",
        header_name="portal_header",
        codec_name="encoded_portal",
        archive_names=("cypress", "dogwood", "redwood"),
        bridge_names=("azure", "maroon", "peach", "slate"),
        marker_v1="G8++",
        marker_v2="W6++",
    )


def expected_authorization(experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": AUTHORIZATION_SCHEMA,
        "status": "owner_authorized_exact_recurrent_observation_validity_execution",
        "owner_statement": "Proceed with the next recurrent observation-validity experiment.",
        "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"],
        "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"),
        "actor_sha256": profile["model_sha256"],
        "conditions": ["C50-R1", "T25-R1-host-v2"],
        "cases": 2,
        "seeds_per_case": 2,
        "prefixes": 4,
        "middle_branches": 8,
        "maximum_final_branches": 8,
        "host_v2_actual_pressure_transition": True,
        "maximum_t25_recurrent_resets": 2,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS,
        "attempts_per_call": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "response_seal_before_evaluator_access": True,
        "output_root": OUTPUT_ROOT,
        "automatic_successor": False,
        "server_reasoning_budget_tokens": 512,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("Experiment 009 authorization differs")
    return {
        "verified": True,
        "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json"),
    }
