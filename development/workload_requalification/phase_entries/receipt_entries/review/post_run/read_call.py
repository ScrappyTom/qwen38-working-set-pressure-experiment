"""Reuse exact input/full reply inspection for a selected original case."""
import argparse
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import receipt_task as study

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('tag')
parser.add_argument('--case',choices=study.CASES,required=True)
parser.add_argument('--version',default='001')
args=parser.parse_args()
path=study.AREA.parent/'probe_entry/review/post_run/read_call.py'
with patch.dict(sys.modules,{'probe_task':study.case_api(args.case)}), patch.object(sys,'argv',
        [str(path),args.tag,'--version',args.version]):
    runpy.run_path(str(path),run_name='__main__')
