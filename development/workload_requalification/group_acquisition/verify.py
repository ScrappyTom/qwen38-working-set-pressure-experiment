"""Exact qualification replay using saved native counts and check observations."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import qualify as case
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def verify(version):
    folder = case.AREA / ('qualification-' + version)
    module = case.study.Task()
    report, seal = module.read(folder/'QUALIFICATION.json'), module.read(folder/'SEAL.json')
    assert report['status']=='qualified' and report['completion_requests']==0 and report['port_free']
    audit = case.load_helper('group_native_audit', 'development/workload_requalification/closure_entries/review/verify_run.py')
    audit._inventory(folder,seal)
    module.verify_sources(seal['source_sha256'])
    records=verify_records(folder/'records.jsonl',folder)
    assert seal['completion_requests']==0 and seal['status']=='qualified_no_model_inference'
    assert not any(r['record_type']=='invocation_started' for r in records)
    adapter=case.runner.Adapter(module)
    counts=audit._native_counts(folder,records,adapter)
    used=set()
    def measure(view):
        key=sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        assert key in counts, 'Replayed transition has no native measurement'
        used.add(key)
        return counts[key]

    class ExactStore:
        def put(self,name,raw):
            assert (folder/name).read_bytes()==raw, name

    class ReplayTask:
        def __getattr__(self,name): return getattr(module,name)
        def attach_observations(self,session,output,log):
            session.observations=ObservationStore(output/'observations',replay=True)

    loop=SimpleNamespace(measure=measure,log=SimpleNamespace(append=lambda *args: None))
    with patch('working_set_exp.observations.subprocess.Popen',side_effect=AssertionError('No checker execution during replay')):
        rows=case.cases(module,loop,adapter,ExactStore())
        assert rows==report['cases']
        route=case.qualification_route.qualify(ReplayTask(),loop,adapter,ExactStore(),folder)
        assert route==report['route']
    assert len(used)==len(counts), 'Some native qualification inputs were not replayed'
    closed=[r['payload'] for r in records if r['record_type']=='runtime_closed']
    assert len(closed)==1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    return dict(status='replayed_exactly',qualification_seal_sha256=sha256_file(folder/'SEAL.json'),
        cases=len(rows),route_steps=len(route['trials']),crowded_steps=route['crowded_transition']['steps'],
        native_inputs=len(counts),artifacts=len(seal['files']),source_bindings=len(seal['source_sha256']),
        custody_records=len(records),verifier_sha256=sha256_file(Path(__file__)),
        no_new_model_or_tokenizer_or_checker_execution=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    result=verify(args.version)
    path=case.AREA/('VERIFICATION-'+args.version+'.json')
    raw=canonical_json_bytes(result)
    if path.exists(): assert path.read_bytes()==raw
    else: path.write_bytes(raw)
    print(json.dumps(result,indent=2))
