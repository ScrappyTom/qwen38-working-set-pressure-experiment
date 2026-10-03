"""Post-seal continuation artifact check; never supplied to the actor."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dynamic'))
import run_saved_dispatch as entry
study = entry.study
from working_set_exp.jsonutil import load_json_strict,sha256_bytes


def main():
    module = entry.Task('dynamic','001',study.AREA/'union/run-002')
    seal = study.read(module.RUN/'RESPONSE_SEAL.json')
    stem = 'stopped' if seal['disposition']=='stopped_without_retry' else 'final'
    candidate = study.candidate_from_snapshot(study.read(module.RUN/f'{stem}-candidate.json'))
    state = study.read(module.RUN/f'{stem}-state.json')
    old = module.inherited_candidate.file_map
    changed = [p for p,raw in candidate.file_map.items() if old[p]!=raw]
    allowed = {'Lib/functools.py','tests/test_virtual_registration.py','Doc/howto/union-dispatch.rst'}
    assert set(changed)<=allowed
    output = study.AREA/'review/dynamic-001'
    store = study.ObservationStore(output/'postseal-check',timeout=60)
    check = store.execute(candidate,study.checker('dynamic',module.inherited_candidate),
                          'public','CHK-0001')
    raw = (store.directory('CHK-0001')/'stdout.bin').read_bytes()
    rows = [load_json_strict(line) for line in raw.splitlines()]
    summary = dict(disposition=seal['disposition'],candidate_id=candidate.candidate_id,
        changed_files=changed,protected_files_exact=len(old)-len(allowed),
        first_regression_exact=candidate.file_map['tests/test_union_registration.py']==old['tests/test_union_registration.py'],
        file_sha256={p:sha256_bytes(v) for p,v in candidate.file_map.items()},
        postseal_public_pass=check['passed'],repeated_checker_is_not_new_coverage=True,
        checker_records=rows,
        final_account=module.restore(state,candidate,module.RUN,replay=True).working_account(),
        documentation_prose_requires_direct_review=True)
    study.save(output,'ARTIFACT_AUDIT.json',summary)
    for path in ('tests/test_virtual_registration.py','Doc/howto/union-dispatch.rst'):
        study.save(output,'saved-'+Path(path).name,candidate.file_map[path])
    print({k:summary[k] for k in ('disposition','candidate_id','changed_files',
          'protected_files_exact','first_regression_exact','postseal_public_pass')})


if __name__=='__main__': main()
