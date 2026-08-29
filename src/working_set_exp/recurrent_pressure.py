from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .authentic_pressure import _inventory
from .candidate import Candidate
from .custody import ArtifactStore, RecordLog
from .fixture import Fixture
from .isolation import run_checker
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .p0 import build_p0
from .request import TOOL_CONTRACT, build_request, fork_binding, observation_directory, render_reasoning_prompt
from .runner import Actor, PrefixOutcome, _execute_call, _save_candidate, _snapshot_prefix
from .runtime import PHYSICAL_CONTEXT, REASONING_BUDGET, T25_TOTAL_CEILING, CapacityStopped, RuntimeProfile, endpoint_request, guard
from .tools import SessionState, ToolExecutor


BANK_SCHEMA = "experiment-007-recurrent-pressure-bank-v1"
PACKAGE_SCHEMA = "experiment-007-recurrent-pressure-package-v1"
CLOSURE_SCHEMA = "experiment-007-recurrent-pressure-closure-v1"
AUTHORIZATION_SCHEMA = "experiment-007-recurrent-pressure-authorization-v1"
CASE_IDS = ("E7-SOURCE", "E7-OBSERVATION")
SEEDS = (173205, 223607)
PREFIX_CALL_LIMIT = 12
MIDDLE_CALL_LIMIT = 12
FINAL_CALL_LIMIT = 8
OUTPUT_ROOT = r"C:\e7-primary"
PRIMARY_OUTPUT_ROOT = r"C:\e8-primary"
MAXIMUM_HTTP_COMPLETION_CALLS = 160


def _ledger(module: str, marker: str, rows: int = 185, *, fact: str | None = None) -> bytes:
    lines = [f'"""Exact {module} custody ledger; every row is task-authorized work."""\n']
    if fact:
        lines.append(fact.rstrip("\n") + "\n")
    lines.append("CUSTODY_ROWS = (\n")
    for index in range(rows):
        digest = sha256_bytes(f"e7:{module}:{marker}:{index:04d}".encode("utf-8"))[:24]
        lines.append(f'    ("{marker}-{index:04d}", "{digest}", "retain-{(index * 37 + 19) % 997:03d}"),\n')
    lines.extend([")\n", "\n", f"def {module}_custody_size() -> int:\n", "    return len(CUSTODY_ROWS)\n"])
    return "".join(lines).encode("utf-8")


def _source_case() -> dict[str, Any]:
    files = {
        "archive/amber.py": _ledger("amber", "SA"),
        "archive/bronze.py": _ledger("bronze", "SB"),
        "policy/route.py": _ledger("route", "SR", fact='ROUTE_STEM = "quartz-"')
        + b'\n\ndef route_stem() -> str:\n    """Return the exact current route stem."""\n    return ROUTE_STEM\n',
        "stage/ready.py": b'PHASE_A_GROUPS = ("amber", "bronze", "route")\n\n\ndef completed_groups() -> int:\n    return 0\n',
        "delivery/key.py": b"def delivery_key(name: str) -> str:\n    return name.strip().casefold()\n",
        "delivery/tag.py": b"def delivery_tag(code: str) -> str:\n    return code.strip().upper()\n",
        "delivery/render.py": (
            b"from delivery.key import delivery_key\nfrom delivery.tag import delivery_tag\n\n"
            b"def render_delivery(name: str, code: str) -> str:\n"
            b"    return f\"{delivery_key(name)}|{delivery_tag(code)}\"\n"
        ),
        "bridge/cinder.py": _ledger("cinder", "SC", rows=80),
        "bridge/delta.py": _ledger("delta", "SD", rows=80),
        "bridge/ember.py": _ledger("ember", "SE", rows=46),
    }
    phase_b = (
        "Phase B: repair `delivery/key.py` so the normalized name is prefixed by the exact current route stem acquired in Phase A. "
        "Preserve trimming, case folding, and the renderer contract. Then read each exact bridge custody file completely: "
        "`bridge/cinder.py`, `bridge/delta.py`, and `bridge/ember.py`. Run check `public` and call `fork_ready`. "
        "Do not change the Phase C target before that boundary."
    )
    phase_c = (
        "Phase C: repair `delivery/tag.py` so the normalized code is also prefixed by the exact current route stem. "
        "The governing source remains `policy/route.py`; reacquire exact current source if it is absent. Preserve trimming, uppercasing, "
        "and `delivery/render.py` behavior. Run check `public` and submit."
    )
    return {
        "fixture_id": "E7-SOURCE", "family": "recurrent_source_continuity", "files": files,
        "phase_a_required": ("archive/amber.py", "archive/bronze.py", "policy/route.py"),
        "phase_b_required": ("bridge/cinder.py", "bridge/delta.py", "bridge/ember.py"),
        "task": (
            "Perform Phase A, Phase B, and Phase C in order. Phase A: read each exact custody file completely: "
            "`archive/amber.py`, `archive/bronze.py`, and `policy/route.py`. Preserve their contents. Then repair `stage/ready.py` so "
            "`completed_groups()` returns the number of `PHASE_A_GROUPS`, run check `prefork`, and call `fork_ready`. "
            "Do not change Phase B or C targets before their stated boundary. " + phase_b + " " + phase_c
        ),
        "phase_b": phase_b, "phase_c": phase_c, "probe_id": None, "probe_v1": None, "probe_v2": None,
        "phase_a_check": b"from stage.ready import completed_groups\nassert completed_groups() == 3\nprint('phase A passed')\n",
        "phase_b_check": (
            b"from delivery.key import delivery_key\nfrom delivery.tag import delivery_tag\n"
            b"assert delivery_key(' Blue ') == 'quartz-blue'\nassert delivery_tag(' x ') == 'X'\nprint('phase B passed')\n"
        ),
        "final_check": (
            b"from delivery.key import delivery_key\nfrom delivery.tag import delivery_tag\nfrom delivery.render import render_delivery\n"
            b"assert delivery_key(' Blue ') == 'quartz-blue'\nassert delivery_tag(' x ') == 'quartz-X'\n"
            b"assert render_delivery(' MiXeD ', ' q7 ') == 'quartz-mixed|quartz-Q7'\nprint('public passed')\n"
        ),
        "hidden": (
            b"from delivery.key import delivery_key\nfrom delivery.tag import delivery_tag\nfrom delivery.render import render_delivery\n"
            b"assert delivery_key(' Blue ') == 'quartz-blue'\nassert delivery_tag(' x ') == 'quartz-X'\n"
            b"assert render_delivery(' MiXeD ', ' q7 ') == 'quartz-mixed|quartz-Q7'\n"
            b"assert delivery_key(' A ') == 'quartz-a'\nassert delivery_tag(' b ') == 'quartz-B'\nprint('hidden passed')\n"
        ),
        "phase_a_patch": {"path": "stage/ready.py", "old": "    return 0", "new": "    return len(PHASE_A_GROUPS)"},
        "phase_b_patch": {"path": "delivery/key.py", "old": "    return name.strip().casefold()", "new": '    return "quartz-" + name.strip().casefold()'},
        "phase_c_patch": {"path": "delivery/tag.py", "old": "    return code.strip().upper()", "new": '    return "quartz-" + code.strip().upper()'},
        "phase_b_target": "delivery/key.py", "phase_c_target": "delivery/tag.py",
        "governing": {"kind": "current_source", "path": "policy/route.py", "fact": 'ROUTE_STEM = "quartz-"'},
    }


def _observation_case() -> dict[str, Any]:
    files = {
        "archive/iris.py": _ledger("iris", "OA"),
        "archive/juniper.py": _ledger("juniper", "OB"),
        "archive/kestrel.py": _ledger("kestrel", "OC"),
        "stage/ready.py": b'PHASE_A_GROUPS = ("iris", "juniper", "kestrel")\n\n\ndef completed_groups() -> int:\n    return 0\n',
        "session/label.py": b"def session_label(name: str) -> str:\n    return name.strip().upper()\n",
        "session/header.py": b"def session_header(name: str) -> str:\n    return name.strip().casefold()\n",
        "session/wire.py": (
            b"from session.label import session_label\nfrom session.header import session_header\n\n"
            b"def encoded_session(name: str) -> bytes:\n"
            b"    return f\"{session_label(name)}|{session_header(name)}\".encode('ascii')\n"
        ),
        "bridge/lumen.py": _ledger("lumen", "OD", rows=80),
        "bridge/marrow.py": _ledger("marrow", "OE", rows=80),
        "bridge/nylon.py": _ledger("nylon", "OF", rows=46),
        "bridge/osprey.py": _ledger("osprey", "OG", rows=168),
    }
    phase_b = (
        "Phase B: reopen the exact current `session` compatibility observation from Phase A and repair `session/label.py` so it prepends "
        "that marker. Then run check `public`. After the mutation, call compatibility probe `session` again to capture the current "
        "candidate-bound marker. Read each bridge custody file completely: `bridge/lumen.py`, `bridge/marrow.py`, `bridge/nylon.py`, and "
        "`bridge/osprey.py`. "
        "Call `fork_ready`. Do not change the Phase C target before that boundary."
    )
    phase_c = (
        "Phase C: repair `session/header.py` so it prepends the exact marker from the compatibility observation valid for the current candidate. "
        "An older observation remains available but is stale. Use the candidate bindings and reopen exact evidence before mutation. Preserve "
        "trimming, case folding, and `session/wire.py` ASCII behavior. Run check `public` and submit."
    )
    return {
        "fixture_id": "E7-OBSERVATION", "family": "version_bound_observation_continuity", "files": files,
        "phase_a_required": ("archive/iris.py", "archive/juniper.py", "archive/kestrel.py"),
        "phase_b_required": ("bridge/lumen.py", "bridge/marrow.py", "bridge/nylon.py", "bridge/osprey.py"),
        "task": (
            "Perform Phase A, Phase B, and Phase C in order. Phase A: read each exact custody file completely: `archive/iris.py`, "
            "`archive/juniper.py`, and `archive/kestrel.py`. Then repair `stage/ready.py` so `completed_groups()` returns the number of "
            "`PHASE_A_GROUPS`, run check `prefork`, call compatibility probe `session` on that current candidate, and call `fork_ready`. "
            "Do not change Phase B or C targets before their stated boundary. " + phase_b + " " + phase_c
        ),
        "phase_b": phase_b, "phase_c": phase_c, "probe_id": "session",
        "probe_v1": "compatibility runtime observation\nsession_marker=K4::\nvalidity=current_candidate_only\n",
        "probe_v2": "compatibility runtime observation\nsession_marker=M7::\nvalidity=current_candidate_only\n",
        "phase_a_check": b"from stage.ready import completed_groups\nassert completed_groups() == 3\nprint('phase A passed')\n",
        "phase_b_check": (
            b"from session.label import session_label\nfrom session.header import session_header\n"
            b"assert session_label(' blue ') == 'K4::BLUE'\nassert session_header(' X ') == 'x'\nprint('phase B passed')\n"
        ),
        "final_check": (
            b"from session.label import session_label\nfrom session.header import session_header\nfrom session.wire import encoded_session\n"
            b"assert session_label(' blue ') == 'K4::BLUE'\nassert session_header(' X ') == 'M7::x'\n"
            b"assert encoded_session(' Ab ') == b'K4::AB|M7::ab'\nprint('public passed')\n"
        ),
        "hidden": (
            b"from session.label import session_label\nfrom session.header import session_header\nfrom session.wire import encoded_session\n"
            b"assert session_label(' blue ') == 'K4::BLUE'\nassert session_header(' X ') == 'M7::x'\n"
            b"assert encoded_session(' Ab ') == b'K4::AB|M7::ab'\n"
            b"assert session_header(' Mixed ') == 'M7::mixed'\nprint('hidden passed')\n"
        ),
        "phase_a_patch": {"path": "stage/ready.py", "old": "    return 0", "new": "    return len(PHASE_A_GROUPS)"},
        "phase_b_patch": {"path": "session/label.py", "old": "    return name.strip().upper()", "new": '    return "K4::" + name.strip().upper()'},
        "phase_c_patch": {"path": "session/header.py", "old": "    return name.strip().casefold()", "new": '    return "M7::" + name.strip().casefold()'},
        "phase_b_target": "session/label.py", "phase_c_target": "session/header.py",
        "governing": {"kind": "candidate_bound_observation", "stale_fact": "session_marker=K4::", "current_fact": "session_marker=M7::"},
    }


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (_source_case(), _observation_case())


def _replace_case(value: Any, replacements: tuple[tuple[str, str], ...]) -> Any:
    if isinstance(value, bytes):
        text = value.decode("utf-8")
        for old, new in replacements:
            text = text.replace(old, new)
        return text.encode("utf-8")
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, tuple):
        return tuple(_replace_case(item, replacements) for item in value)
    if isinstance(value, list):
        return [_replace_case(item, replacements) for item in value]
    if isinstance(value, dict):
        return {_replace_case(key, replacements): _replace_case(item, replacements) for key, item in value.items()}
    return value


def primary_case_definitions() -> tuple[dict[str, Any], ...]:
    source = _replace_case(_source_case(), (
        ("E7-SOURCE", "E8-SOURCE"), ("quartz-", "topaz-"),
        ("ROUTE_STEM", "CHANNEL_STEM"), ("route_stem", "channel_stem"),
        ("policy/route.py", "policy/channel.py"), ("policy.route", "policy.channel"),
        ("route", "channel"), ("amber", "alder"), ("bronze", "birch"),
        ("cinder", "coral"), ("delta", "drift"), ("ember", "elm"),
        ("delivery_key", "dispatch_token"), ("delivery_tag", "dispatch_badge"),
        ("render_delivery", "compose_dispatch"), ("delivery/key.py", "dispatch/token.py"),
        ("delivery/tag.py", "dispatch/badge.py"), ("delivery/render.py", "dispatch/compose.py"),
        ("delivery.key", "dispatch.token"), ("delivery.tag", "dispatch.badge"),
        ("delivery.render", "dispatch.compose"), ("delivery", "dispatch"),
    ))
    observation = _replace_case(_observation_case(), (
        ("E7-OBSERVATION", "E8-OBSERVATION"), ("K4::", "J2@@"), ("M7::", "R8@@"),
        ("iris", "hazel"), ("juniper", "maple"), ("kestrel", "oak"),
        ("lumen", "pearl"), ("marrow", "reed"), ("nylon", "silk"), ("osprey", "tulip"),
        ("session_label", "runtime_nameplate"), ("session_header", "runtime_prefix"),
        ("encoded_session", "encoded_runtime"), ("session/label.py", "runtime/nameplate.py"),
        ("session/header.py", "runtime/prefix.py"), ("session/wire.py", "runtime/codec.py"),
        ("session.label", "runtime.nameplate"), ("session.header", "runtime.prefix"),
        ("session.wire", "runtime.codec"), ("session_marker", "runtime_marker"), ("session", "runtime"),
    ))
    # Preserve an authentic second pressure boundary after the fresh lexical
    # transformation slightly reduced tokenizer occupancy. This exact inert
    # custody row is acquired during Phase B and has no task-semantic content.
    observation["files"]["bridge/tulip.py"] += (
        b'\nRECURRENT_PRESSURE_RESERVE = "custody-only-001-002-003-004-005-006-007-008"\n'
    )
    return source, observation


def _candidate_after(case: dict[str, Any], phase: str) -> Candidate:
    candidate = Candidate.create(case["files"])
    patches = [case["phase_a_patch"]]
    if phase in {"B", "C"}:
        patches.append(case["phase_b_patch"])
    if phase == "C":
        patches.append(case["phase_c_patch"])
    for row in patches:
        candidate, _ = candidate.patch(
            path=row["path"], old=row["old"], new=row["new"],
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(row["path"]),
        )
    return candidate


@dataclass(frozen=True)
class RecurrentFixture:
    fixture_id: str
    family: str
    task: str
    phase_b: str
    phase_c: str
    initial: Candidate
    phase_a_checker: bytes
    phase_b_checker: bytes
    final_checker: bytes
    hidden_checker: bytes
    phase_a_required: tuple[str, ...]
    phase_b_required: tuple[str, ...]
    phase_b_target: str
    phase_c_target: str
    probe_id: str | None
    probe_v1: str | None
    probe_v2: str | None

    def prefix_fixture(self) -> Fixture:
        return Fixture(
            fixture_id=self.fixture_id, family=self.family, task=self.task, initial=self.initial,
            prefork_checker=self.phase_a_checker, public_checker=self.final_checker,
            required_full_reads=self.phase_a_required, final_target=self.phase_b_target,
            probe_id=self.probe_id, probe_body=self.probe_v1,
        )


def construct_bank(
    target: Path, *, replace_preseal: bool = False, definitions: tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any]:
    if target.exists() and not replace_preseal:
        raise FileExistsError(target)
    files: dict[str, bytes] = {}
    definitions = definitions or case_definitions()
    for case in definitions:
        initial = Candidate.create(case["files"])
        after_a, after_b, known_good = (_candidate_after(case, phase) for phase in ("A", "B", "C"))
        visible = f"model_visible/{case['fixture_id']}"
        rows = []
        for path, data in initial.files:
            files[f"{visible}/candidate/{path}"] = data
            rows.append({"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)})
        files[f"{visible}/TASK.txt"] = case["task"].encode()
        files[f"{visible}/PHASE_B.txt"] = case["phase_b"].encode()
        files[f"{visible}/PHASE_C.txt"] = case["phase_c"].encode()
        execution = f"execution_only/{case['fixture_id']}"
        files[f"{execution}/checks/phase_a.py"] = case["phase_a_check"]
        files[f"{execution}/checks/phase_b.py"] = case["phase_b_check"]
        files[f"{execution}/checks/public.py"] = case["final_check"]
        if case["probe_v1"]:
            files[f"{execution}/PROBE_V1.txt"] = case["probe_v1"].encode()
            files[f"{execution}/PROBE_V2.txt"] = case["probe_v2"].encode()
        files[f"{execution}/FIXTURE.json"] = canonical_json_bytes({
            "schema_version": "experiment-007-fixture-v1", "fixture_id": case["fixture_id"], "family": case["family"],
            "initial_candidate_id": initial.candidate_id, "phase_a_candidate_id": after_a.candidate_id,
            "phase_b_candidate_id": after_b.candidate_id, "known_good_candidate_id": known_good.candidate_id,
            "candidate_files": rows, "phase_a_required": list(case["phase_a_required"]),
            "phase_b_required": list(case["phase_b_required"]), "phase_b_target": case["phase_b_target"],
            "phase_c_target": case["phase_c_target"], "probe_id": case["probe_id"],
        })
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        for path, data in known_good.files:
            files[f"{evaluator}/known_good/{path}"] = data
        files[f"{evaluator}/TRUTH.json"] = canonical_json_bytes({
            "schema_version": "experiment-007-truth-v1", "fixture_id": case["fixture_id"], "family": case["family"],
            "known_good_candidate_id": known_good.candidate_id, "phase_a_candidate_id": after_a.candidate_id,
            "phase_b_candidate_id": after_b.candidate_id, "phase_a_patch": case["phase_a_patch"],
            "phase_b_patch": case["phase_b_patch"], "phase_c_patch": case["phase_c_patch"], "governing": case["governing"],
        })
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [{"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)} for path, data in sorted(files.items())]
    manifest = {
        "schema_version": BANK_SCHEMA, "bank_id": "E7BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
        "case_ids": [case["fixture_id"] for case in definitions], "seeds": list(SEEDS), "fresh_before_actor_exposure": True,
        "selected_before_actor_behavior": True, "evaluator_separate": True, "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    files = _inventory(target, excluded={"BANK_MANIFEST.json"})
    if manifest["schema_version"] != BANK_SCHEMA or manifest["files"] != files:
        raise ValueError("recurrent bank differs")
    expected = "E7BANK-" + sha256_bytes(canonical_json_bytes(files))
    if manifest["bank_id"] != expected:
        raise ValueError("recurrent bank identity differs")
    return {"verified": True, "bank_id": expected, "file_count": len(files)}


def load_recurrent_fixture(bank: Path, fixture_id: str) -> RecurrentFixture:
    visible = bank / "model_visible" / fixture_id
    execution = bank / "execution_only" / fixture_id
    row = load_json_strict((execution / "FIXTURE.json").read_bytes())
    files = {item["path"]: (visible / "candidate" / Path(*item["path"].split("/"))).read_bytes() for item in row["candidate_files"]}
    initial = Candidate.create(files)
    if initial.candidate_id != row["initial_candidate_id"]:
        raise ValueError("recurrent fixture candidate differs")
    probe_v1 = execution / "PROBE_V1.txt"
    probe_v2 = execution / "PROBE_V2.txt"
    return RecurrentFixture(
        fixture_id=fixture_id, family=row["family"], task=(visible / "TASK.txt").read_text(),
        phase_b=(visible / "PHASE_B.txt").read_text(), phase_c=(visible / "PHASE_C.txt").read_text(), initial=initial,
        phase_a_checker=(execution / "checks" / "phase_a.py").read_bytes(),
        phase_b_checker=(execution / "checks" / "phase_b.py").read_bytes(),
        final_checker=(execution / "checks" / "public.py").read_bytes(),
        hidden_checker=(bank / "evaluator_only" / fixture_id / "hidden.py").read_bytes(),
        phase_a_required=tuple(row["phase_a_required"]), phase_b_required=tuple(row["phase_b_required"]),
        phase_b_target=row["phase_b_target"], phase_c_target=row["phase_c_target"], probe_id=row["probe_id"],
        probe_v1=probe_v1.read_text() if probe_v1.exists() else None,
        probe_v2=probe_v2.read_text() if probe_v2.exists() else None,
    )


def progress_pointer(fixture: RecurrentFixture, phase: str) -> dict[str, Any]:
    text = fixture.phase_b if phase == "B" else fixture.phase_c
    return {
        "schema_version": "experiment-007-verbatim-active-step-v1", "phase": phase,
        "source": "prospectively_frozen_user_authored_task_segment", "text": text,
        "sha256": sha256_bytes(text.encode()), "host_inference": False,
    }


def build_recurrent_request(
    fixture: RecurrentFixture, *, candidate: Candidate, phase: str, history: list[dict[str, Any]],
    observations: list[dict[str, Any]], reconstructed: bool, boundary_binding: dict[str, Any], calls_used: int,
    read_mode: str = "actor_selected_count", observation_directory_version: int = 1,
    acquisition_contract: bool = False,
) -> bytes:
    stage = "recurrent" if phase == "B" else "continuation"
    base = load_json_strict(build_request(
        fixture_id=fixture.fixture_id, task=fixture.task, candidate=candidate, stage="continuation",
        visible_history=history, prefix_calls_used=PREFIX_CALL_LIMIT, continuation_calls_used=calls_used,
        probe_id=fixture.probe_id, observations=observations, reconstructed=reconstructed,
        fork_binding=boundary_binding, progress_pointer=progress_pointer(fixture, phase),
        prefix_call_limit=PREFIX_CALL_LIMIT,
        continuation_call_limit=MIDDLE_CALL_LIMIT if phase == "B" else FINAL_CALL_LIMIT,
        read_mode=read_mode, observation_directory_version=observation_directory_version,
        acquisition_contract=acquisition_contract,
    ))
    base.update({
        "schema_version": (
            "experiment-011-recurrent-acquisition-request-v1"
            if acquisition_contract else "experiment-007-recurrent-coding-request-v1"
        ), "stage": stage, "phase": phase,
        "completed_phase_ids": ["A"] if phase == "B" else ["A", "B"],
        "available_check_ids": ["public"],
    })
    if phase == "B":
        actions = ["tree", "search", "read", "patch", "check", "reopen_observation", "fork_ready"]
        if fixture.probe_id:
            actions.append("probe")
            base["available_probe_ids"] = [fixture.probe_id]
        else:
            base["available_probe_ids"] = []
        base["available_actions"] = actions
        base["tool_contract"] = {name: TOOL_CONTRACT[name] for name in actions}
        if acquisition_contract:
            base["tool_contract"]["read"] = (
                "exact current whole-line page with actor-selected count and non-guessing continuation"
                if read_mode == "actor_selected_count"
                else "largest exact current whole-line page that fits the frozen result bound, with non-guessing continuation"
            )
            base["read_paging_mode"] = read_mode
    return canonical_json_bytes(base)


def recurrent_binding(
    fixture: RecurrentFixture, *, seed: int, condition: str, candidate: Candidate,
    active_history: list[dict[str, Any]], observations: list[dict[str, Any]], prior_binding: dict[str, Any],
    last_record_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "experiment-007-second-boundary-binding-v1", "fixture_id": fixture.fixture_id,
        "seed": seed, "condition": condition, "completed_phase_ids": ["A", "B"],
        "task_sha256": sha256_bytes(fixture.task.encode()), "candidate_id": candidate.candidate_id,
        "candidate_manifest_sha256": sha256_bytes(canonical_json_bytes([
            {"path": path, "sha256": sha256_bytes(data)} for path, data in candidate.files
        ])),
        "p0_sha256": sha256_bytes(canonical_json_bytes(build_p0(candidate))),
        "active_history_sha256": sha256_bytes(canonical_json_bytes(active_history)),
        "observation_directory_sha256": sha256_bytes(canonical_json_bytes(observation_directory(observations))),
        "prior_binding_sha256": sha256_bytes(canonical_json_bytes(prior_binding)),
        "last_record_sha256": last_record_sha256, "pending_phase": "C",
    }


class CandidateBoundProbeExecutor(ToolExecutor):
    def __init__(self, *args: Any, baseline_candidate_id: str, probe_v1: str | None, probe_v2: str | None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.baseline_candidate_id = baseline_candidate_id
        self.probe_v1 = probe_v1
        self.probe_v2 = probe_v2

    def _probe(self, action: dict[str, Any]) -> dict[str, Any]:
        # The external environment advances after any candidate mutation.  It
        # does not inspect semantic correctness or compare with evaluator truth.
        self.probe_body = self.probe_v2 if self.state.candidate.candidate_id != self.baseline_candidate_id else self.probe_v1
        return super()._probe(action)


@dataclass
class MiddleOutcome:
    state: SessionState
    active_history: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    reopenable: dict[str, bytes]
    binding: dict[str, Any] | None
    calls: int
    http_completion_calls: int
    output_dir: Path
    disposition: str


def _observation_target(action: dict[str, Any]) -> str:
    if action["action"] == "probe":
        return action["probe_id"]
    if action["action"] == "check":
        return action["check_id"]
    return "phase_boundary"


def _capture_observation(
    action: dict[str, Any], result: dict[str, Any], *, sequence: int, state: SessionState,
    observations: list[dict[str, Any]], reopenable: dict[str, bytes],
) -> None:
    if action.get("action") not in {"probe", "check", "fork_ready"} or not result.get("accepted"):
        return
    body = canonical_json_bytes(result)
    handle = f"OBS-{len(observations) + 1:04d}"
    reopenable[handle] = body
    observations.append({
        "handle": handle, "sequence": sequence, "action": action["action"], "target": _observation_target(action),
        "candidate_id": result.get("checked_candidate_id", result.get("candidate_id", state.candidate.candidate_id)),
        "size_bytes": len(body), "sha256": sha256_bytes(body),
    })


def run_middle(
    fixture: RecurrentFixture, prefix: PrefixOutcome, *, condition: str, seed: int, actor: Actor, output_dir: Path,
    read_mode: str = "actor_selected_count", observation_directory_version: int = 1,
    acquisition_contract: bool = False, condition_label: str | None = None,
) -> MiddleOutcome:
    if condition not in {"C50", "T25"}:
        raise ValueError("invalid recurrent condition")
    recorded_condition = condition_label or condition
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{fixture.fixture_id}-S{seed}-{condition}-B")
    state = prefix.state.clone_for_branch()
    state.stage = "recurrent"
    state.fork_ready = False
    state.public_check_passed = False
    state.probe_done = False
    observations = [dict(row) for row in prefix.observations]
    reopenable = dict(prefix.reopenable)
    executor = CandidateBoundProbeExecutor(
        state, required_full_reads=fixture.phase_b_required, prefork_checker=fixture.phase_a_checker,
        public_checker=fixture.phase_b_checker, final_target=fixture.phase_c_target, probe_id=fixture.probe_id,
        probe_body=fixture.probe_v1, reopenable=reopenable, baseline_candidate_id=prefix.state.candidate.candidate_id,
        probe_v1=fixture.probe_v1, probe_v2=fixture.probe_v2,
        read_mode=read_mode,
    )
    base_history = list(prefix.history) if condition == "C50" else [prefix.history[-1]]
    middle_history: list[dict[str, Any]] = []
    log.append("middle_started", {"condition": recorded_condition, "candidate_id": state.candidate.candidate_id, "prior_binding": prefix.binding}, _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)))
    calls = 0
    http_calls = 0
    maximum_prompt = 0
    capacity_stop = None
    while calls < MIDDLE_CALL_LIMIT and not state.fork_ready:
        calls += 1
        active = [*base_history, *middle_history]
        request = build_recurrent_request(
            fixture, candidate=state.candidate, phase="B", history=active, observations=observations,
            reconstructed=condition == "T25", boundary_binding=prefix.binding, calls_used=calls - 1,
            read_mode=read_mode, observation_directory_version=observation_directory_version,
            acquisition_contract=acquisition_contract,
        )
        try:
            action, result, outcome = _execute_call(
                actor=actor, request=request, stage="recurrent", probe_id=fixture.probe_id,
                call_id=f"{fixture.fixture_id}-S{seed}-{recorded_condition}-B{calls:02d}",
                active_total_ceiling=T25_TOTAL_CEILING if condition == "T25" else PHYSICAL_CONTEXT,
                executor=executor, store=store, log=log, artifact_prefix=f"transcript/{calls:03d}",
            )
        except CapacityStopped as exc:
            capacity_stop = exc.admission
            maximum_prompt = max(maximum_prompt, exc.admission["offline_prompt_tokens"])
            break
        http_calls += 1
        maximum_prompt = max(maximum_prompt, outcome.offline_prompt_tokens)
        middle_history.append({"response": action, "result": result})
        _capture_observation(action, result, sequence=len(base_history) + len(middle_history), state=state, observations=observations, reopenable=reopenable)
    binding = None
    if state.fork_ready:
        active = [*base_history, *middle_history]
        binding = recurrent_binding(
            fixture, seed=seed, condition=recorded_condition, candidate=state.candidate, active_history=active,
            observations=observations, prior_binding=prefix.binding, last_record_sha256=log.previous or "",
        )
        prospective = build_recurrent_request(
            fixture, candidate=state.candidate, phase="C", history=active, observations=observations,
            reconstructed=condition == "T25", boundary_binding=binding, calls_used=0,
            read_mode=read_mode, observation_directory_version=observation_directory_version,
            acquisition_contract=acquisition_contract,
        )
        own_guard = guard(
            actor.profile, prospective,
            active_total_ceiling=T25_TOTAL_CEILING if condition == "T25" else PHYSICAL_CONTEXT,
            reasoning_enabled=True,
        )
        physical_guard = guard(actor.profile, prospective, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        if own_guard["authorized"]:
            disposition = "second_boundary_not_reached"
        elif condition == "T25" and physical_guard["authorized"]:
            disposition = "second_boundary_eligible"
        else:
            disposition = "physical_capacity_reference_reached"
        atomic_write(output_dir / "SECOND_BOUNDARY_CAPACITY.json", canonical_json_bytes({
            "schema_version": "experiment-007-second-boundary-capacity-v1", "condition": condition,
            "prospective_request_sha256": sha256_bytes(prospective), "own_guard": own_guard,
            "physical_guard": physical_guard, "disposition": disposition,
        }))
    elif capacity_stop is not None:
        disposition = "capacity_stopped_during_phase_b"
    else:
        disposition = "phase_b_budget_exhausted"
    stopped = log.append("middle_stopped", {
        "condition": recorded_condition, "disposition": disposition, "calls": calls, "prepared_invocations": calls,
        "http_completion_calls": http_calls, "candidate_id": state.candidate.candidate_id,
        "public_check_passed": state.public_check_passed, "capacity_stop": capacity_stop, "boundary_binding": binding,
    }, [])
    summary = {
        "schema_version": "experiment-007-middle-summary-v1", "fixture_id": fixture.fixture_id, "condition": recorded_condition,
        "seed": seed, "disposition": disposition, "calls": calls, "prepared_invocations": calls,
        "http_completion_calls": http_calls, "candidate_id": state.candidate.candidate_id,
        "public_check_passed": state.public_check_passed, "capacity_stop": capacity_stop,
        "maximum_offline_prompt_tokens": maximum_prompt, "boundary_binding": binding,
        "active_history_sha256": sha256_bytes(canonical_json_bytes([*base_history, *middle_history])),
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    return MiddleOutcome(state, [*base_history, *middle_history], observations, reopenable, binding, calls, http_calls, output_dir, disposition)


def run_final(
    fixture: RecurrentFixture, middle: MiddleOutcome, *, condition: str, seed: int, actor: Actor, output_dir: Path,
) -> dict[str, Any]:
    allowed = (
        condition == "T25" and middle.disposition == "second_boundary_eligible"
    ) or (
        condition == "C50" and middle.disposition == "second_boundary_not_reached"
    )
    if middle.binding is None or not allowed:
        raise ValueError("final phase requires an admitted condition-specific transition")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(output_dir / "records.jsonl", f"{fixture.fixture_id}-S{seed}-{condition}-C")
    state = SessionState(candidate=middle.state.candidate, stage="continuation")
    executor = ToolExecutor(
        state, required_full_reads=(), prefork_checker=fixture.phase_a_checker, public_checker=fixture.final_checker,
        final_target=fixture.phase_c_target, probe_id=fixture.probe_id, probe_body=fixture.probe_v2,
        reopenable=middle.reopenable,
    )
    history = [middle.active_history[-1]] if condition == "T25" else list(middle.active_history)
    reconstructed = condition == "T25"
    active_ceiling = T25_TOTAL_CEILING if reconstructed else PHYSICAL_CONTEXT
    log.append("final_started", {"condition": condition, "candidate_id": state.candidate.candidate_id, "boundary_binding": middle.binding}, _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)))
    calls = 0
    http_calls = 0
    maximum_prompt = 0
    capacity_stop = None
    while calls < FINAL_CALL_LIMIT and not state.submitted:
        calls += 1
        request = build_recurrent_request(
            fixture, candidate=state.candidate, phase="C", history=history, observations=middle.observations,
            reconstructed=reconstructed, boundary_binding=middle.binding, calls_used=calls - 1,
        )
        try:
            action, result, outcome = _execute_call(
                actor=actor, request=request, stage="continuation", probe_id=fixture.probe_id,
                call_id=f"{fixture.fixture_id}-S{seed}-{condition}-C{calls:02d}", active_total_ceiling=active_ceiling,
                executor=executor, store=store, log=log, artifact_prefix=f"transcript/{calls:03d}",
            )
        except CapacityStopped as exc:
            capacity_stop = exc.admission
            maximum_prompt = max(maximum_prompt, exc.admission["offline_prompt_tokens"])
            break
        http_calls += 1
        maximum_prompt = max(maximum_prompt, outcome.offline_prompt_tokens)
        history.append({"response": action, "result": result})
    disposition = "submitted" if state.submitted else "capacity_stopped_before_http" if capacity_stop else "final_budget_exhausted"
    stopped = log.append("final_stopped", {
        "disposition": disposition, "calls": calls, "prepared_invocations": calls, "http_completion_calls": http_calls,
        "candidate_id": state.candidate.candidate_id, "submitted": state.submitted,
        "public_check_passed": state.public_check_passed, "capacity_stop": capacity_stop,
    }, [])
    summary = {
        "schema_version": "experiment-007-final-summary-v1", "fixture_id": fixture.fixture_id, "condition": condition,
        "seed": seed, "disposition": disposition, "calls": calls, "prepared_invocations": calls,
        "http_completion_calls": http_calls, "candidate_id": state.candidate.candidate_id,
        "submitted": state.submitted, "public_check_passed": state.public_check_passed,
        "capacity_stop": capacity_stop, "maximum_offline_prompt_tokens": maximum_prompt,
        "history_sha256": sha256_bytes(canonical_json_bytes(history)), "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    return summary


def construct_package(
    target: Path, *, bank: Path, schedule_path: Path, profile: RuntimeProfile, replace_preseal: bool = False,
) -> dict[str, Any]:
    if target.exists() and not replace_preseal:
        raise FileExistsError(target)
    target.mkdir(parents=True, exist_ok=replace_preseal)
    schedule = load_json_strict(schedule_path.read_bytes())
    cells = []
    for row in schedule["cells"]:
        fixture = load_recurrent_fixture(bank, row["fixture_id"])
        base = fixture.prefix_fixture()
        request = build_request(
            fixture_id=base.fixture_id, task=base.task, candidate=base.initial, stage="setup", visible_history=[],
            prefix_calls_used=0, continuation_calls_used=0, probe_id=base.probe_id, observations=[], reconstructed=False,
            fork_binding=None, prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=MIDDLE_CALL_LIMIT,
        )
        endpoint = endpoint_request(profile, request, stage="setup", probe_id=base.probe_id, seed=row["seed"], reasoning_enabled=True)
        rendered = render_reasoning_prompt(request, enabled=True)
        admission = guard(profile, request, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        cell = f"cell-{row['ordinal']:02d}"
        atomic_write(target / cell / "initial-coding-request.json", request)
        atomic_write(target / cell / "initial-endpoint-request.json", endpoint)
        atomic_write(target / cell / "initial-rendered-prompt.txt", rendered)
        cells.append({
            "ordinal": row["ordinal"], "fixture_id": row["fixture_id"], "seed": row["seed"],
            "branch_order": row["branch_order"], "expected_call_id": f"{row['fixture_id']}-S{row['seed']}-P01",
            "coding_request_sha256": sha256_bytes(request), "endpoint_request_sha256": sha256_bytes(endpoint),
            "rendered_prompt_sha256": sha256_bytes(rendered),
            "initial_admission": admission,
        })
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    manifest = {
        "schema_version": PACKAGE_SCHEMA, "bank_id": verify_bank(bank)["bank_id"], "schedule_sha256": sha256_file(schedule_path),
        "conditions": ["C50-R1", "T25-R1-recurrent"], "server_reasoning_budget_tokens": REASONING_BUDGET,
        "prefix_call_limit": PREFIX_CALL_LIMIT, "middle_call_limit": MIDDLE_CALL_LIMIT, "final_call_limit": FINAL_CALL_LIMIT,
        "cells": cells, "files": files, "evaluator_bytes_present": False,
        "package_id": "E7PKG-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_package(target: Path, *, bank: Path, schedule_path: Path, profile: RuntimeProfile) -> dict[str, Any]:
    manifest = load_json_strict((target / "PACKAGE_MANIFEST.json").read_bytes())
    files = _inventory(target, excluded={"PACKAGE_MANIFEST.json"})
    if manifest["schema_version"] != PACKAGE_SCHEMA or manifest["files"] != files:
        raise ValueError("recurrent package differs")
    with tempfile.TemporaryDirectory(prefix="e7-package-") as raw:
        rebuilt = Path(raw) / "package"
        expected = construct_package(rebuilt, bank=bank, schedule_path=schedule_path, profile=profile)
        if canonical_json_bytes(expected) != canonical_json_bytes(manifest):
            raise ValueError("recurrent package reconstruction differs")
    return {"verified": True, "package_id": manifest["package_id"], "file_count": len(files)}


def build_closure(repo: Path, *, entrypoint: str = "scripts/run_recurrent_pressure.py") -> dict[str, Any]:
    paths = sorted((repo / "src" / "working_set_exp").glob("*.py"))
    paths.append(repo / Path(*entrypoint.split("/")))
    rows = [{"path": path.relative_to(repo).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in paths]
    return {"schema_version": CLOSURE_SCHEMA, "files": rows, "aggregate_sha256": sha256_bytes(canonical_json_bytes(rows))}


def verify_closure(repo: Path, path: Path) -> dict[str, Any]:
    expected = load_json_strict(path.read_bytes())
    entrypoints = [row["path"] for row in expected["files"] if not row["path"].startswith("src/working_set_exp/")]
    if len(entrypoints) != 1:
        raise ValueError("recurrent closure entrypoint differs")
    observed = build_closure(repo, entrypoint=entrypoints[0])
    if canonical_json_bytes(expected) != canonical_json_bytes(observed):
        raise ValueError("recurrent closure differs")
    return {"verified": True, "aggregate_sha256": observed["aggregate_sha256"], "file_count": len(observed["files"])}


def expected_authorization(experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": AUTHORIZATION_SCHEMA, "status": "owner_authorized_exact_recurrent_pressure_execution",
        "owner_statement": "Go ahead and work on the next experiment.", "bank_id": bank["bank_id"],
        "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"], "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"], "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"), "actor_sha256": profile["model_sha256"],
        "conditions": ["C50-R1", "T25-R1-recurrent"], "cases": 2, "seeds_per_case": 2,
        "prefixes": 4, "middle_branches": 8, "final_recurrent_branches": 4,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS, "attempts_per_call": 1,
        "retries": 0, "repairs": 0, "rescues": 0, "response_seal_before_evaluator_access": True,
        "output_root": OUTPUT_ROOT, "automatic_successor": False, "server_reasoning_budget_tokens": REASONING_BUDGET,
    }


def validate_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_authorization(experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("recurrent authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}


def expected_primary_authorization(experiment: Path) -> dict[str, Any]:
    bank = load_json_strict((experiment / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    package = load_json_strict((experiment / "execution_package" / "PACKAGE_MANIFEST.json").read_bytes())
    closure = load_json_strict((experiment / "EXECUTABLE_CLOSURE.json").read_bytes())
    profile = load_json_strict((experiment / "RUNTIME_PROFILE.json").read_bytes())
    return {
        "schema_version": "experiment-008-recurrent-pressure-authorization-v1",
        "status": "owner_authorized_exact_fresh_corrected_recurrent_pressure_execution",
        "owner_statement": "Go ahead and work on the next experiment.",
        "attempt1_disposition": "immutable_apparatus_evidence_not_reused_or_reclassified",
        "attempt1_response_seal_sha256": sha256_file(
            experiment.parent / "007_recurrent_bounded_pressure" / "attempt1_apparatus_run" / "RESPONSE_SEAL.json"
        ),
        "bank_id": bank["bank_id"], "bank_manifest_sha256": sha256_file(experiment / "fresh_bank" / "BANK_MANIFEST.json"),
        "package_id": package["package_id"], "package_manifest_sha256": sha256_file(experiment / "execution_package" / "PACKAGE_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(experiment / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"], "schedule_sha256": sha256_file(experiment / "SCHEDULE.json"),
        "runtime_profile_sha256": sha256_file(experiment / "RUNTIME_PROFILE.json"), "actor_sha256": profile["model_sha256"],
        "conditions": ["C50-R1", "T25-R1-recurrent"], "cases": 2, "seeds_per_case": 2,
        "prefixes": 4, "middle_branches": 8, "maximum_final_branches": 8,
        "continue_c50_phase_c_when_physically_admitted": True,
        "maximum_http_completion_calls": MAXIMUM_HTTP_COMPLETION_CALLS, "attempts_per_call": 1,
        "retries": 0, "repairs": 0, "rescues": 0, "response_seal_before_evaluator_access": True,
        "output_root": PRIMARY_OUTPUT_ROOT, "automatic_successor": False, "server_reasoning_budget_tokens": REASONING_BUDGET,
    }


def validate_primary_authorization(experiment: Path) -> dict[str, Any]:
    observed = load_json_strict((experiment / "MEASURED_AUTHORIZATION.json").read_bytes())
    expected = expected_primary_authorization(experiment)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise ValueError("fresh corrected recurrent authorization differs")
    return {"verified": True, "authorization_sha256": sha256_file(experiment / "MEASURED_AUTHORIZATION.json")}


def hidden_grade(fixture: RecurrentFixture, candidate: Candidate) -> dict[str, Any]:
    return run_checker(candidate, fixture.hidden_checker)
