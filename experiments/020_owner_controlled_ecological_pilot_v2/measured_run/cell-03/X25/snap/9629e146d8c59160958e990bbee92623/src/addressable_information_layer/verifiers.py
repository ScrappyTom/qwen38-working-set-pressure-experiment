"""Deterministic offline criterion checks."""

from __future__ import annotations

import ast
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from .hashing import stable_id
from .records import Artifact, CriterionArtifact, VerifierReceipt, VerifierStatus

DEFAULT_COMMAND_PREFIXES = (
    ("python", "-m", "pytest"),
    ("python", "-m", "py_compile"),
    ("python", "-m", "compileall"),
    ("python3", "-m", "pytest"),
    ("python3", "-m", "py_compile"),
    ("python3", "-m", "compileall"),
    ("py", "-m", "pytest"),
    ("py", "-m", "py_compile"),
    ("pytest",),
)
MAX_COMMAND_TIMEOUT_SECONDS = 60
MAX_COMMAND_OUTPUT_CHARS = 1600


def run_criterion_checks(criteria: list[CriterionArtifact], artifacts: dict[str, Artifact]) -> list[VerifierReceipt]:
    receipts: list[VerifierReceipt] = []
    for criterion in criteria:
        if criterion.check_type in {"command", "shell_command"}:
            receipts.append(_check_command(criterion, artifacts))
            continue
        artifact = _target_artifact(criterion, artifacts)
        if artifact is None:
            receipts.append(_receipt(criterion, VerifierStatus.SKIPPED, "no target artifact resolved", None))
            continue
        if criterion.check_type == "python_syntax":
            receipts.append(_check_python_syntax(criterion, artifact))
        elif criterion.check_type == "contains":
            receipts.append(_check_contains(criterion, artifact))
        elif criterion.check_type == "not_contains":
            receipts.append(_check_not_contains(criterion, artifact))
        elif criterion.check_type == "regex":
            receipts.append(_check_regex(criterion, artifact))
        elif criterion.check_type == "verifier_log_passed":
            receipts.append(_check_verifier_log_passed(criterion, artifact))
        elif criterion.check_type == "required_headings":
            receipts.append(_check_required_headings(criterion, artifact))
        elif criterion.check_type == "section_contains":
            receipts.append(_check_section_contains(criterion, artifact))
        elif criterion.check_type == "no_unresolved_markers":
            receipts.append(_check_no_unresolved_markers(criterion, artifact))
        elif criterion.check_type == "word_count_min":
            receipts.append(_check_word_count_min(criterion, artifact))
        else:
            receipts.append(_receipt(criterion, VerifierStatus.SKIPPED, f"unsupported check_type {criterion.check_type}", artifact))
    return receipts


def _target_artifact(criterion: CriterionArtifact, artifacts: dict[str, Artifact]) -> Artifact | None:
    if criterion.target_artifact_ref and criterion.target_artifact_ref in artifacts:
        return artifacts[criterion.target_artifact_ref]
    if criterion.target_path:
        for artifact in artifacts.values():
            if artifact.path_or_name == criterion.target_path:
                return artifact
    if len(artifacts) == 1:
        return next(iter(artifacts.values()))
    return None


def _check_python_syntax(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    try:
        ast.parse(artifact.text)
    except SyntaxError as exc:
        return _receipt(criterion, VerifierStatus.FAILED, f"python syntax failed: {exc}", artifact)
    return _receipt(criterion, VerifierStatus.PASSED, "python syntax passed", artifact)


def _check_contains(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    needle = str(criterion.params.get("text", ""))
    if not needle:
        return _receipt(criterion, VerifierStatus.SKIPPED, "contains check missing params.text", artifact)
    if needle in artifact.text:
        return _receipt(criterion, VerifierStatus.PASSED, "required text found", artifact)
    return _receipt(criterion, VerifierStatus.FAILED, "required text not found", artifact)


def _check_not_contains(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    needle = str(criterion.params.get("text", ""))
    if not needle:
        return _receipt(criterion, VerifierStatus.SKIPPED, "not_contains check missing params.text", artifact)
    if needle not in artifact.text:
        return _receipt(criterion, VerifierStatus.PASSED, "forbidden text absent", artifact)
    return _receipt(criterion, VerifierStatus.FAILED, "forbidden text present", artifact)


def _check_regex(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    pattern = str(criterion.params.get("pattern", ""))
    if not pattern:
        return _receipt(criterion, VerifierStatus.SKIPPED, "regex check missing params.pattern", artifact)
    if re.search(pattern, artifact.text, flags=re.MULTILINE):
        return _receipt(criterion, VerifierStatus.PASSED, "regex matched", artifact)
    return _receipt(criterion, VerifierStatus.FAILED, "regex did not match", artifact)


def _check_verifier_log_passed(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    lowered = artifact.text.lower()
    if any(token in lowered for token in ("failed", "failure", "error", "traceback", "exception", "assertionerror")):
        return _receipt(criterion, VerifierStatus.FAILED, "verifier log contains failure signal", artifact)
    if any(token in lowered for token in ("passed", "success", "ok")):
        return _receipt(criterion, VerifierStatus.PASSED, "verifier log contains pass signal", artifact)
    return _receipt(criterion, VerifierStatus.SKIPPED, "verifier log contains no pass/fail signal", artifact)


def _check_required_headings(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    required = criterion.params.get("headings")
    if not isinstance(required, list) or not required:
        return _receipt(criterion, VerifierStatus.SKIPPED, "required_headings check missing params.headings", artifact)
    present = {_normalize_heading(title) for title, _start, _end in _markdown_sections(artifact.text)}
    missing = [str(title) for title in required if _normalize_heading(str(title)) not in present]
    if not missing:
        return _receipt(criterion, VerifierStatus.PASSED, "required headings present", artifact)
    return _receipt(criterion, VerifierStatus.FAILED, f"missing headings: {', '.join(missing)}", artifact)


def _check_section_contains(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    needle = str(criterion.params.get("text", ""))
    heading = criterion.params.get("heading") or criterion.params.get("section")
    address = criterion.params.get("address")
    if not needle:
        return _receipt(criterion, VerifierStatus.SKIPPED, "section_contains check missing params.text", artifact)
    if not heading and isinstance(address, str) and address.startswith("section:"):
        heading = address.removeprefix("section:").replace("-", " ")
    if not heading:
        return _receipt(criterion, VerifierStatus.SKIPPED, "section_contains check missing params.heading or params.address", artifact)
    section = _section_text(artifact.text, str(heading))
    if section is None:
        return _receipt(criterion, VerifierStatus.FAILED, f"section not found: {heading}", artifact)
    if needle in section:
        return _receipt(criterion, VerifierStatus.PASSED, "section contains required text", artifact)
    return _receipt(criterion, VerifierStatus.FAILED, "section missing required text", artifact)


def _check_no_unresolved_markers(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    markers = criterion.params.get("markers")
    marker_values = [str(item) for item in markers] if isinstance(markers, list) and markers else ["TODO", "TBD", "FIXME", "???"]
    lowered = artifact.text.lower()
    found = [marker for marker in marker_values if marker.lower() in lowered]
    if not found:
        return _receipt(criterion, VerifierStatus.PASSED, "no unresolved markers found", artifact)
    return _receipt(criterion, VerifierStatus.FAILED, f"unresolved markers found: {', '.join(found)}", artifact)


def _check_word_count_min(criterion: CriterionArtifact, artifact: Artifact) -> VerifierReceipt:
    try:
        minimum = int(criterion.params.get("min_words"))
    except (TypeError, ValueError):
        return _receipt(criterion, VerifierStatus.SKIPPED, "word_count_min check missing integer params.min_words", artifact)
    count = len(re.findall(r"\b\w+\b", artifact.text))
    if count >= minimum:
        return _receipt(criterion, VerifierStatus.PASSED, f"word count {count} >= {minimum}", artifact)
    return _receipt(criterion, VerifierStatus.FAILED, f"word count {count} < {minimum}", artifact)


def _markdown_sections(text: str) -> list[tuple[str, int, int]]:
    lines = text.splitlines()
    headings: list[tuple[str, int]] = []
    for idx, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            headings.append((match.group(2).strip(), idx))
    sections: list[tuple[str, int, int]] = []
    for pos, (title, start) in enumerate(headings):
        end = headings[pos + 1][1] - 1 if pos + 1 < len(headings) else max(len(lines), start)
        sections.append((title, start, end))
    return sections


def _section_text(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    wanted = _normalize_heading(heading)
    for title, start, end in _markdown_sections(text):
        if _normalize_heading(title) == wanted:
            return "\n".join(lines[start - 1 : end])
    return None


def _normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _check_command(criterion: CriterionArtifact, artifacts: dict[str, Artifact]) -> VerifierReceipt:
    command = criterion.params.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
        return _receipt(criterion, VerifierStatus.SKIPPED, "command check requires params.command as a string list", None)
    if not _command_is_allowed(command, criterion):
        return _receipt(criterion, VerifierStatus.SKIPPED, "command prefix is not in the offline verifier allowlist", None)

    timeout = _bounded_timeout(criterion.params.get("timeout_seconds"))
    expected_exit = int(criterion.params.get("expected_exit_code", 0))
    with tempfile.TemporaryDirectory(prefix="ail_verify_") as temp_name:
        workspace = Path(temp_name)
        _materialize_artifacts(workspace, artifacts)
        cwd = _resolve_safe_cwd(workspace, str(criterion.params.get("cwd", ".")))
        if cwd is None:
            return _receipt(criterion, VerifierStatus.SKIPPED, "command cwd must stay inside verifier workspace", None)
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
        except FileNotFoundError:
            return _receipt(criterion, VerifierStatus.SKIPPED, f"command executable not found: {command[0]}", None)
        except subprocess.TimeoutExpired as exc:
            output = _truncate_output((exc.stdout or "") + "\n" + (exc.stderr or ""))
            return _receipt(criterion, VerifierStatus.FAILED, f"command timed out after {timeout}s: {output}", None)

    output = _truncate_output((completed.stdout or "") + "\n" + (completed.stderr or ""))
    reason = f"command exited {completed.returncode}, expected {expected_exit}"
    if output.strip():
        reason = f"{reason}; output: {output}"
    status = VerifierStatus.PASSED if completed.returncode == expected_exit else VerifierStatus.FAILED
    return _receipt(criterion, status, reason, None)


def _command_is_allowed(command: list[str], criterion: CriterionArtifact) -> bool:
    configured = criterion.params.get("allowed_prefixes")
    prefixes = configured if isinstance(configured, list) and configured else DEFAULT_COMMAND_PREFIXES
    normalized = [_normalize_executable(command[0]), *[part.lower() for part in command[1:]]]
    for prefix in prefixes:
        if not isinstance(prefix, (list, tuple)) or not prefix:
            continue
        normalized_prefix = [_normalize_executable(str(prefix[0])), *[str(part).lower() for part in prefix[1:]]]
        if normalized[: len(normalized_prefix)] == normalized_prefix:
            return True
    return False


def _normalize_executable(token: str) -> str:
    name = Path(token).name.lower()
    return name[:-4] if name.endswith(".exe") else name


def _bounded_timeout(value) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        return 20
    return min(max(timeout, 1), MAX_COMMAND_TIMEOUT_SECONDS)


def _materialize_artifacts(workspace: Path, artifacts: dict[str, Artifact]) -> None:
    for artifact in artifacts.values():
        relative = _safe_relative_path(artifact.path_or_name)
        if relative is None:
            continue
        target = workspace.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact.text, encoding="utf-8")


def _safe_relative_path(path_or_name: str) -> PurePosixPath | None:
    normalized = path_or_name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() and ".." in path.parts or not path.parts:
        return None
    return path


def _resolve_safe_cwd(workspace: Path, cwd_value: str) -> Path | None:
    if cwd_value in {"", "."}:
        return workspace.resolve()
    relative = _safe_relative_path(cwd_value)
    if relative is None:
        return None
    cwd = workspace.joinpath(*relative.parts).resolve()
    workspace_resolved = workspace.resolve()
    try:
        cwd.relative_to(workspace_resolved)
    except ValueError:
        return None
    cwd.mkdir(parents=True, exist_ok=True)
    return cwd


def _truncate_output(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_COMMAND_OUTPUT_CHARS:
        return text
    return text[:MAX_COMMAND_OUTPUT_CHARS] + "\n[truncated command verifier output]"


def _receipt(
    criterion: CriterionArtifact,
    status: VerifierStatus,
    reason: str,
    artifact: Artifact | None,
) -> VerifierReceipt:
    payload = {
        "criterion": criterion.criterion_id,
        "status": status.value,
        "reason": reason,
        "artifact": artifact.artifact_id if artifact else None,
    }
    return VerifierReceipt(
        receipt_id=stable_id("verifier", payload),
        criterion_id=criterion.criterion_id,
        status=status,
        reason=reason,
        artifact_id=artifact.artifact_id if artifact else None,
        evidence_refs=[artifact.blob_ref] if artifact else [],
    )
