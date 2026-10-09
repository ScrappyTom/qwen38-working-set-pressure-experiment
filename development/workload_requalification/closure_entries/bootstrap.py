"""Load the qualified host; no construction, checks or model calls on import."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(str(ROOT / 'development/workload_requalification/ecological_observation_entry/bootstrap.py'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
