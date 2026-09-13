"""Prepare or execute the separately declared corrected-host contribution."""
import argparse
from pathlib import Path
import sys

import bounded_parser as baseline
import prepare_bounded_parser as preparation
import run_bounded_parser as runner
from working_set_exp.jsonutil import sha256_file, atomic_write

AREA = baseline.AREA / "contribution-v2"
PACKAGE = AREA / "preparation-001"
RUN = AREA / "run-001"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"


def __getattr__(name):
    return getattr(baseline, name)


def initial_session():
    baseline.require((AREA/"TASK.txt").read_bytes() == (baseline.AREA/"TASK.txt").read_bytes(), "declared task changed")
    return baseline.initial_session()


def source_identities():
    extra = [AREA/"SPEC.md", AREA/"TASK.txt", AREA/"PRESENTATION_DECISION.json",
             *sorted((baseline.ROOT/"tests").glob("test_working_*.py")),
             baseline.ROOT/"tests/test_bounded_visibility.py"]
    return {**baseline.source_identities(), **{p.relative_to(baseline.ROOT).as_posix():sha256_file(p) for p in extra}}


def requirements():
    decision = baseline.read(AREA/"PRESENTATION_DECISION.json")
    baseline.require(decision["consultation_directly_reviewed"] and decision["ready_for_contribution_preparation"],
        "complete and review consultation before freezing a contribution")
    for name, digest in decision["evidence_sha256"].items():
        baseline.require(sha256_file(baseline.ROOT/name) == digest, "consulted evidence changed")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "freeze", "run", "stop"))
    p.add_argument("--manifest-sha256"); p.add_argument("--owner-direction", default="")
    p.add_argument("--reason",default="")
    a = p.parse_args()
    if a.mode == "stop":
        baseline.require((RUN/"records.jsonl").is_file() and not (RUN/"RESPONSE_SEAL.json").exists(), "no active unsealed attempt")
        raw=a.reason.strip().encode()
        baseline.require(0 < len(raw) <= 4096 and not (RUN/"STOP_REQUEST.txt").exists(), "invalid or repeated stop request")
        atomic_write(RUN/"STOP_REQUEST.txt",raw)
        print("Stop requested; current operation will finish before normal closure.")
        sys.exit(0)
    requirements()
    if a.mode == "prepare":
        preparation.main(PACKAGE)
    elif a.mode == "freeze":
        baseline.save(AREA, MANIFEST.name, runner.plan(sys.modules[__name__]))
        print(sha256_file(MANIFEST))
    else:
        runner.run_once(a, sys.modules[__name__])
