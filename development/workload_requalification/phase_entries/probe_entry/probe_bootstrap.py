"""Reuse the phase and current host modules without starting a runtime."""
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
runpy.run_path(str(AREA.parent / 'bootstrap.py'))
sys.path.insert(0, str(AREA))
