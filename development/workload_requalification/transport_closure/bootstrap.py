from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'development/workload_requalification/search_continuity'))
runpy.run_path(str(ROOT/'development/workload_requalification/search_continuity/bootstrap.py'))
