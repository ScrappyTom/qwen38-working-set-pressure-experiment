from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parents[3]
FOLDER=ROOT/'development/workload_requalification/diagnostic_continuity'
sys.path.insert(0,str(FOLDER))
runpy.run_path(str(FOLDER/'bootstrap.py'))
