"""Reuse exact replay and source/delivery metrics for the interpolation target."""
import argparse
import inspect
import json

import interpolation_task as study
from manage import load_helper
from working_set_exp.jsonutil import sha256_file


def main(version):
    area=study.AREA;run=area/f'run-{version}'
    assert (run/'RESPONSE_SEAL.json').exists(), 'Do not assess an unfinished run'
    replay=load_helper('interpolation_replay','development/decision_interface/reference_repair/verify_reference.py')
    replay.study=study
    result=replay.verify(run)
    study.save(area/'review','VERIFICATION.json',result)
    metrics=load_helper('interpolation_metrics','development/decision_interface/reference_repair/review/assess_run.py')
    source=inspect.getsource(metrics.main)
    assert source.count("target='Lib/test/test_urlparse.py'")==1
    source=source.replace("target='Lib/test/test_urlparse.py'","target='Lib/test/test_configparser.py'")
    namespace=dict(metrics.__dict__,AREA=area,RUN=run)
    exec(compile(source,__file__+':target_adaptation','exec'),namespace)
    namespace['main']()
    study.save(area/'review','ANALYSIS_PROVENANCE.json',dict(run=run.name,
        replay_source_sha256=sha256_file(study.ROOT/'development/decision_interface/reference_repair/verify_reference.py'),
        metrics_source_sha256=sha256_file(study.ROOT/'development/decision_interface/reference_repair/review/assess_run.py'),
        adaptation='Only target test filename changed from test_urlparse.py to test_configparser.py.',
        model_requests=0,checker_executions=0))
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='002');main(p.parse_args().version)
