"""Apply the existing original-probe assessment to the separate MINT case."""
import argparse
import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import receipt_task as study
from working_set_exp.jsonutil import canonical_json_bytes,sha256_file


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    task=study.Task(args.version,case='E14-CLOSURE-MINT')
    path=study.AREA.parent/'probe_entry/review/post_run/assess.py'
    spec=importlib.util.spec_from_file_location('mint_original_probe_assessment',path)
    module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'probe_task':study.case_api(task.CASE)}):
        spec.loader.exec_module(module)
    module.AREA=task.AREA
    module.assess(args.version)
    folder=task.AREA/'review'/args.version
    module.save(folder/'ASSESSMENT-ADAPTER.json',dict(case=task.CASE,
        adapter_sha256=sha256_file(Path(__file__)),core_sha256=sha256_file(path),
        task_adapter_sha256=sha256_file(Path(study.__file__)),
        assessment_sha256=sha256_file(folder/'ASSESSMENT.json'),
        metrics_sha256=sha256_file(folder/'METRICS.json'),
        meaning='Existing probe procedure/artifact evaluation with explicit case factory and output directory. No new actor inference.'))
