"""Post-seal artifact and separately declared follow-on boundary review."""
import importlib.util
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap
import dispatch_task as study
from working_set_exp.jsonutil import load_json_strict, sha256_bytes
from working_set_exp.observations import ObservationStore


def main():
    module = study.Task('union', '002')
    state, candidate = study.inherited_material(module.RUN)
    output = study.AREA/'review/union-002'
    original = study.starting_files()
    changed = [p for p, raw in candidate.file_map.items() if raw != original[p]]
    assert set(changed) == {'Lib/functools.py', 'tests/test_union_registration.py'}
    store = ObservationStore(output/'postseal-check', timeout=60)
    check = store.execute(candidate, study.checker('union'), 'public', 'CHK-0001')
    rows = [load_json_strict(line) for line in
            (store.directory('CHK-0001')/'stdout.bin').read_bytes().splitlines()]
    assert check['passed'] and rows[-1]['passed']
    # This separate prospective job requirement is not an added first-job grade.
    import abc
    import typing
    with tempfile.TemporaryDirectory(prefix='dispatch-artifact-review-') as temporary:
        path = Path(temporary)/'functools.py'
        path.write_bytes(candidate.file_map['Lib/functools.py'])
        spec = importlib.util.spec_from_file_location('reviewed_candidate_functools', path)
        library = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(library)
        observations = []
        for style in ('typing', 'pipe', 'ordinary_class'):
            class Plugin(abc.ABC): pass
            class Payload: pass
            @library.singledispatch
            def dispatch(value): return 'default'
            def handler(value): return 'plugin'
            members = (typing.Union[Plugin, int] if style == 'typing' else
                       Plugin | int if style == 'pipe' else Plugin)
            dispatch.register(members, handler)
            before = dispatch(Payload())
            Plugin.register(Payload)
            after = dispatch(Payload())
            observations.append(dict(style=style, before=before, after=after,
                virtual_membership=issubclass(Payload, Plugin),
                abc_registry_handler=dispatch.registry[Plugin] is handler))
    summary = dict(candidate_id=candidate.candidate_id,
        changed_files=changed, protected_files_exact=len(original)-len(changed),
        file_sha256={p:sha256_bytes(raw) for p,raw in candidate.file_map.items()},
        postseal_public_pass=check['passed'],
        repeated_checker_is_not_new_coverage=True,
        checker_records=rows,
        declared_follow_on_observations=observations,
        follow_on_is_not_first_job_rescore=True,
        final_account=module.restore(state, candidate, module.RUN, replay=True).working_account())
    study.save(output, 'ARTIFACT_AUDIT.json', summary)
    print({k:summary[k] for k in ('candidate_id','changed_files','protected_files_exact',
        'postseal_public_pass','declared_follow_on_observations')})


if __name__ == '__main__': main()
