from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'development/workload_requalification/configparser_operational'))
import runpy
runpy.run_path(str(ROOT / 'development/workload_requalification/configparser_operational/bootstrap.py'))
