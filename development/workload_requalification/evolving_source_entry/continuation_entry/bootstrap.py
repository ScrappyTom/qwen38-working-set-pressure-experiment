"""Reuse the source entry's runtime paths without executing its task."""
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
ROOT = runpy.run_path(str(AREA.parent / 'bootstrap.py'))['ROOT']
sys.path.insert(0, str(AREA.parent))
sys.path.insert(0, str(AREA))
