"""Reuse the frozen write-safety task and host; importing opens no runtime."""
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
runpy.run_path(str(AREA.parent/'configparser_write_safety/bootstrap.py'))
sys.path.insert(0, str(AREA))
