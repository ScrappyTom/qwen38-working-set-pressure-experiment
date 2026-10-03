"""Post-seal apparatus/prose probes; never part of either actor input."""
import contextlib
import doctest
import importlib.util
import inspect
import io
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dynamic'))
import run_saved_dispatch as entry

study = entry.study


def main():
    task = entry.Task('dynamic', '001', study.AREA / 'union/run-002')
    seal = study.read(task.RUN / 'RESPONSE_SEAL.json')
    assert seal['disposition'] == 'checked_submission'
    candidate = study.candidate_from_snapshot(study.read(task.RUN / 'final-candidate.json'))
    output = study.AREA / 'review/dynamic-001/documentation-probe'
    assert not output.exists(), 'Preserve the first probe; do not retry over it.'
    document = candidate.file_map['Doc/howto/union-dispatch.rst'].decode()
    observed = {}
    with tempfile.TemporaryDirectory(prefix='dispatch-doc-review-') as folder:
        library_path = Path(folder) / 'functools.py'
        library_path.write_bytes(candidate.file_map['Lib/functools.py'])
        spec = importlib.util.spec_from_file_location('saved_dispatch_review', library_path)
        library = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = library
        spec.loader.exec_module(library)
        old = sys.modules['functools']
        sys.modules['functools'] = library
        try:
            for name, extra in [('original_unset_namespace', {}),
                                ('normal_interactive_namespace', {'__name__': '__main__'})]:
                test = doctest.DocTestParser().get_doctest(
                    document, {'functools': library, **extra}, name,
                    'Doc/howto/union-dispatch.rst', 0)
                stream = io.StringIO()
                result = doctest.DocTestRunner(verbose=True).run(
                    test, out=stream.write, clear_globs=False)
                observed[name] = dict(failed=result.failed, attempted=result.attempted,
                    payload_module=test.globs['Payload'].__module__)
                study.save(output, name + '.txt', stream.getvalue().encode())

            @library.singledispatch
            def handler(value):
                return 'default'

            @handler.register(int | str)
            def union_handler(value):
                return 'union'

            @handler.register(bool)
            def bool_handler(value):
                return 'bool-specific'

            specific = dict(subclass_of_union_member=issubclass(bool, int),
                int_result=handler(1), str_result=handler('x'), bool_result=handler(True))
        finally:
            sys.modules['functools'] = old
            sys.modules.pop(spec.name, None)
    assert observed['original_unset_namespace']['failed'] == 0
    assert observed['normal_interactive_namespace']['failed'] == 1
    assert specific == dict(subclass_of_union_member=True, int_result='union',
                            str_result='union', bool_result='bool-specific')
    result = dict(candidate_id=candidate.candidate_id, python=sys.version,
        library_sha256=study.sha256_bytes(candidate.file_map['Lib/functools.py']),
        documentation_sha256=study.sha256_bytes(document.encode()),
        namespace_probes=observed, specific_registration_counterexample=specific,
        original_check_unchanged=True, new_model_performance_evidence=False,
        documentation_requires_correction=True)
    study.save(output, 'RESULTS.json', result)
    study.save(output, 'installed-testfile-source.txt',
               inspect.getsource(doctest.testfile).encode())
    print(result)


if __name__ == '__main__':
    main()
