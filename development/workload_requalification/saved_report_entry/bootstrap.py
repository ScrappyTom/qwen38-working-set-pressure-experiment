"""Current compiler host import boundary; no task or runtime execution."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(str(ROOT / 'development/workload_requalification/compiler_entry/bootstrap.py'))
sys.path.insert(0, str(ROOT / 'development/workload_requalification/compiler_entry'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
