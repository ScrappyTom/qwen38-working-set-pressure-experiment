"""Reuse qualified host/runtime imports; this module starts no process."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(str(ROOT / 'development/workload_requalification/dispatch_continuity/bootstrap.py'))
for relative in ('interpolation', 'interpolation_revision', 'interpolation_completion'):
    sys.path.insert(0, str(ROOT / 'development/workload_requalification' / relative))
