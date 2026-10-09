"""Reuse the existing coding host; importing this opens no runtime."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(str(ROOT / 'development/workload_requalification/dispatch_continuity/bootstrap.py'))
sys.path.insert(0, str(ROOT / 'development/workload_requalification/configparser_original'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
