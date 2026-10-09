"""Display actual ORBIT inputs, complete replies and effects; never invoke actor."""
import argparse
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import recurrent_task as study

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('tag')
parser.add_argument('--version', default='001')
args = parser.parse_args()
path = study.AREA.parent / 'phase_entries/probe_entry/review/post_run/read_call.py'
with patch.dict(sys.modules, {'probe_task': study}), patch.object(sys, 'argv',
        [str(path), args.tag, '--version', args.version]):
    runpy.run_path(str(path), run_name='__main__')
