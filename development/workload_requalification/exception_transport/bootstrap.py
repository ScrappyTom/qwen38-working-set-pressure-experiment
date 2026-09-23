from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'development/workload_requalification/saved_library_entry'))
runpy.run_path(str(ROOT/'development/workload_requalification/saved_library_entry/bootstrap.py'))
