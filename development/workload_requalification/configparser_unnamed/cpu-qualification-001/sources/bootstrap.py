"""Reuse the coding runtime and optional recovery projection; no launch on import."""
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
runpy.run_path(str(AREA.parent/'configparser_write_safety/bootstrap.py'))
sys.path.append(str(AREA.parent/'recovery_navigation'))
sys.path.insert(0, str(AREA.parent/'configparser_write_safety_continuation'))
sys.path.insert(0, str(AREA))
