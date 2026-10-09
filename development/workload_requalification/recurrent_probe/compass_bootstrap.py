"""Import existing phase/probe machinery without opening a runtime."""
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
runpy.run_path(str(AREA.parent / 'recurrent_entries/recurrent_bootstrap.py'))
sys.path.insert(0, str(AREA.parent / 'phase_entries/probe_entry'))
sys.path.insert(0, str(AREA.parent / 'decision_facts'))
sys.path.insert(0, str(AREA))
