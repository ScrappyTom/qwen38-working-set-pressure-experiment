"""Import the qualified phase host; never start a runtime on import."""
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
runpy.run_path(str(AREA.parent / 'phase_entries' / 'bootstrap.py'))
sys.path.insert(0, str(AREA))
