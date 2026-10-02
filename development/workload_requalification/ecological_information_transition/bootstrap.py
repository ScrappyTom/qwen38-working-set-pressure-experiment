"""Reuse exact E20 contract helpers without constructing the later job."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(str(ROOT / 'development/workload_requalification/ecological_contract_continuation/bootstrap.py'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
