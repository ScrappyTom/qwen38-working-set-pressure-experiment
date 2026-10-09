"""Load the existing phase/probe host without starting a runtime."""
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
runpy.run_path(str(AREA.parent / 'probe_entry' / 'probe_bootstrap.py'))
sys.path.insert(0, str(AREA))
