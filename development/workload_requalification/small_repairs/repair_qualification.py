"""Bind prerequisites to the current implementation and exact saved evidence."""
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict,sha256_bytes,sha256_file


def verify(root,folder,expected_sources,kind):
    root,folder=Path(root),Path(folder)
    seal_path=folder/'SEAL.json'
    seal=load_json_strict(seal_path.read_bytes())
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256'], 'Qualification inventory differs'
    assert seal['source_sha256']==expected_sources, 'Qualification source closure differs'
    for name,digest in expected_sources.items():
        assert sha256_file(root/name)==digest, 'Qualification source changed: '+name
    bindings={seal_path.relative_to(root).as_posix():sha256_file(seal_path)}
    names=[]
    for row in seal['files']:
        name=row['path'];names.append(name)
        path=folder/name
        assert path.resolve().is_relative_to(folder.resolve()), 'Qualification path escapes its package'
        assert path.stat().st_size==row['size_bytes'] and sha256_file(path)==row['sha256'], name
        bindings[path.relative_to(root).as_posix()]=row['sha256']
    assert len(names)==len(set(names)) and 'RESULTS.json' in names, 'Invalid qualification inventory'
    assert 'FAILED.json' not in names, 'Failed qualification cannot authorize preparation'
    result=load_json_strict((folder/'RESULTS.json').read_bytes())
    if kind=='checker':
        assert seal['status']=='qualified_no_model_inference' and seal['completion_requests']==0
        assert result['completion_requests']==0
        rows={(r['case'],r['entry']):r for r in result['cases']}
        assert len(rows)==len(result['cases'])==6
        assert set(rows)=={(case,entry) for case in ('artifact_map','shift','receipts') for entry in ('original','reference')}
        assert all(r['passed'] is (entry=='reference') for (case,entry),r in rows.items())
    elif kind=='native':
        assert result['status']=='passed' and result['model_inference_calls']==0 and result['vocabulary_only'] is True
        assert result['cases'] and all(r['accepted_including_eos'] is r['expected'] for r in result['cases'])
    else:
        raise ValueError('Unknown qualification kind')
    return bindings
