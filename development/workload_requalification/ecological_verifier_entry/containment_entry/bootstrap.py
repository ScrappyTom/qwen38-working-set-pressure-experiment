"""Reuse the parent's host; keep this job's adapter importable first."""
from pathlib import Path
import runpy
import sys
ROOT = Path(__file__).resolve().parents[4]
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'bootstrap.py'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
