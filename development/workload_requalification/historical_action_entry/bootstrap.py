"""Reuse the current host modules; importing this file performs no task work."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(str(ROOT / 'development/workload_requalification/ecological_source_entry/bootstrap.py'))
sys.path.insert(0, str(ROOT / 'development/workload_requalification/ecological_source_entry'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
