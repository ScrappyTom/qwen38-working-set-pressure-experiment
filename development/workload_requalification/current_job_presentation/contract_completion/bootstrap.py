"""Reuse the qualified runtime/import boundary without changing sealed ancestors."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'bootstrap.py'))
