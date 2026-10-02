"""Reuse the current host/runtime import boundary without running a task."""
from pathlib import Path
import runpy
import sys
ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(str(ROOT/'development/workload_requalification/configparser_operational/bootstrap.py'))
sys.path.insert(0, str(ROOT/'development/workload_requalification/search_continuity'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
