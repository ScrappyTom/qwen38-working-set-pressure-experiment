"""Post-seal exact replay and ordinary-testfile check, never actor input."""
import contextlib
import doctest
import importlib.util
import io
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_documentation as entry
study = entry.study
sys.path.insert(0, str(study.AREA / 'review'))
from verify_dispatch import verify
from working_set_exp.jsonutil import load_json_strict, sha256_bytes


def main():
    task = entry.Task()
    output = Path(__file__).resolve().parent / 'run-001'
    assert not output.exists(), 'Preserve the first audit, do not overwrite it.'
    verify(task, output)
    seal = study.read(task.RUN / 'RESPONSE_SEAL.json')
    stem = 'stopped' if seal['disposition'] == 'stopped_without_retry' else 'final'
    candidate = study.candidate_from_snapshot(study.read(task.RUN / f'{stem}-candidate.json'))
    state = study.read(task.RUN / f'{stem}-state.json')
    protected = {p: candidate.file_map[p] == raw
                 for p, raw in task.inherited_candidate.file_map.items() if p != entry.DOC}
    assert len(protected) == 7 and all(protected.values())
    store = study.ObservationStore(output / 'postseal-check', timeout=60)
    check = store.execute(candidate, entry.checker(task.inherited_candidate), 'public', 'CHK-0001')
    rows = [load_json_strict(line) for line in
            (store.directory('CHK-0001') / 'stdout.bin').read_bytes().splitlines()]
    with tempfile.TemporaryDirectory(prefix='dispatch-doc-testfile-') as folder:
        folder = Path(folder)
        source = folder / 'functools.py'
        source.write_bytes(candidate.file_map['Lib/functools.py'])
        doc = folder / 'union-dispatch.rst'
        doc.write_bytes(candidate.file_map[entry.DOC])
        spec = importlib.util.spec_from_file_location('saved_documentation_library', source)
        library = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = library
        spec.loader.exec_module(library)
        previous = sys.modules['functools']
        sys.modules['functools'] = library
        stream = io.StringIO()
        try:
            with contextlib.redirect_stdout(stream):
                result = doctest.testfile(str(doc), module_relative=False,
                    globs={'functools': library}, verbose=True, encoding='utf-8')
        finally:
            sys.modules['functools'] = previous
            sys.modules.pop(spec.name, None)
    study.save(output, 'ordinary-testfile-output.txt', stream.getvalue().encode())
    summary = dict(disposition=seal['disposition'], candidate_id=candidate.candidate_id,
        protected_files_exact=protected,
        changed_files=[p for p, raw in candidate.file_map.items()
                       if task.inherited_candidate.file_map[p] != raw],
        file_sha256={p: sha256_bytes(raw) for p, raw in candidate.file_map.items()},
        postseal_public_pass=check['passed'], checker_records=rows,
        ordinary_testfile=dict(failed=result.failed, attempted=result.attempted,
                              namespace='__main__ default from installed doctest.testfile'),
        repeated_checker_is_not_new_coverage=True,
        final_account=task.restore(state, candidate, task.RUN, replay=True).working_account(),
        documentation_prose_requires_direct_review=True)
    study.save(output, 'ARTIFACT_AUDIT.json', summary)
    study.save(output, 'saved-union-dispatch.rst', candidate.file_map[entry.DOC])
    print({k: summary[k] for k in ('disposition', 'candidate_id', 'changed_files',
                                  'postseal_public_pass', 'ordinary_testfile')})


if __name__ == '__main__': main()
