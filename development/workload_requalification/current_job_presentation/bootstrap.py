"""Reuse the qualified dispatch operating/runtime imports."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dispatch_continuity'))
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'dispatch_continuity/bootstrap.py'))
