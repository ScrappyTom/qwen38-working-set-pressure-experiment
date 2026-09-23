from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/workload_requalification/documentation_followup'))
runpy.run_path(str(ROOT/'development/workload_requalification/documentation_followup/bootstrap.py'))
