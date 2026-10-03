"""CPU comparison with ordinary discovery and standalone doctest, pass and failure."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import overlap_task as entry
import overlap_reference as reference
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file


def discover(folder, library):
    previous = sys.modules['functools']
    sys.modules['functools'] = library
    sys.modules.pop('test_virtual_registration',None)
    stream = io.StringIO()
    try:
        suite = unittest.defaultTestLoader.discover(str(folder/'tests'),pattern='test_virtual_registration.py')
        result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    finally:
        sys.modules['functools'] = previous
        sys.modules.pop('test_virtual_registration',None)
    return dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                passed=result.wasSuccessful(),output=stream.getvalue())


def main():
    output = Path(__file__).resolve().parent/'environment-003'
    output.mkdir(exist_ok=False)
    task = entry.Task(version='002'); start=task.inherited_candidate
    files=dict(start.file_map)
    files[entry.TEST]=reference.tests(files[entry.TEST].decode()).encode()
    files[entry.DOC]=reference.documentation(files[entry.DOC].decode()).encode()
    candidate=entry.study.Candidate.create(files,max_file_bytes=entry.study.FILE_LIMIT)
    program=entry.checker(start)
    observations=entry.ObservationStore(output/'observations',timeout=60)
    results={}
    for name, data in (('pass',files),('doctest_failure',{**files,entry.DOC:files[entry.DOC]+b'\n\n>>> 1 + 1\n3\n'})):
        value=entry.study.Candidate.create(data,max_file_bytes=entry.study.FILE_LIMIT)
        receipt=observations.execute(value,program,'public','CHK-'+('0001' if name=='pass' else '0002'))
        rows={r['case']:r for r in (load_json_strict(x) for x in
            (observations.directory(receipt['observation'])/'stdout.bin').read_bytes().splitlines()) if 'case' in r}
        custom=rows['executable_documentation']; ordinary=rows['ordinary_standalone_documentation']
        assert (custom['failed'],custom['attempted'])==(ordinary['failed'],ordinary['attempted'])
        assert custom['failed']==(0 if name=='pass' else 1)
        results[name]=dict(receipt=receipt,custom_documentation=custom,ordinary_documentation=ordinary)
    with tempfile.TemporaryDirectory() as root:
        root=Path(root)
        (root/'tests').mkdir()
        (root/'tests/test_virtual_registration.py').write_bytes(files[entry.TEST])
        source=root/'functools.py'; source.write_bytes(files['Lib/functools.py'])
        def load(name):
            spec=importlib.util.spec_from_file_location(name,source)
            library=importlib.util.module_from_spec(spec);sys.modules[name]=library
            spec.loader.exec_module(library);return library
        normal=discover(root,load('ordinary_saved_library'))
        assert normal['passed'] and normal['tests']==5,normal
        old='raise RuntimeError("Ambiguous dispatch: {} or {}".format(\n                    match, t))'
        body=source.read_text(encoding='utf-8'); assert body.count(old)==1
        source.write_text(body.replace(old,'return registry[match]',1),encoding='utf-8')
        fault=discover(root,load('ordinary_faulted_library'))
        (output/'ordinary-unittest.json').write_bytes(canonical_json_bytes(dict(normal=normal,fault=fault)))
        assert not fault['passed'] and fault['failures']==4 and fault['errors']==0,fault
    results['ordinary_unittest']=dict(pass_execution=normal,fault_execution=fault,
        candidate_import='sys.modules[functools] points to the exact saved candidate module',
        ordinary_path='unittest.defaultTestLoader.discover(tests), TextTestRunner',
        interpreter=sys.version,probes_are_evaluator_only=True)
    results['qualifier_sha256']=sha256_file(Path(__file__))
    (output/'RESULTS.json').write_bytes(canonical_json_bytes(results))
    print('Ordinary/custom doctest agree on pass and real failure; ordinary unittest passes5 methods and detects4 resolver-fault subtest failures in2 methods.')


if __name__=='__main__': main()
