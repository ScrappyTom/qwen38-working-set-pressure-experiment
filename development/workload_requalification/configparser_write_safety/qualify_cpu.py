"""Compare ordinary execution with the actual checker before any model exposure."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import material
import reference_work
from contract_cases import WriteSafetyContract


def checker():
    return (b'CONFIG = ' + repr(material.checker_configuration()).encode() + b'\n' +
            (material.AREA / 'contract_cases.py').read_bytes() + b'\n' +
            (material.AREA / 'checker_program.py').read_bytes())


def load(raw, name):
    import types
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(raw, name, 'exec'), module.__dict__)
    return module


def direct(raw, name):
    module = load(raw, name)
    WriteSafetyContract.library = module
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(WriteSafetyContract))
    parser = module.ConfigParser()
    parser['settings'] = {'first=second': 'third'}
    target = io.StringIO()
    try:
        parser.write(target)
        restored = module.ConfigParser()
        restored.read_string(target.getvalue())
        observation = dict(written=target.getvalue(), read_back=dict(restored['settings']))
    except Exception as error:
        observation = dict(exception=type(error).__name__, diagnostic=str(error), partial_output=target.getvalue())
    return dict(successful=result.wasSuccessful(), tests=result.testsRun,
                failures=len(result.failures), errors=len(result.errors),
                runner_output=stream.getvalue(), ordinary_example=observation)


def run(files, ordinary=False):
    with tempfile.TemporaryDirectory(prefix='write-safety-qualification-') as temp:
        root = Path(temp)
        for name, raw in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        if ordinary:
            command = [sys.executable, '-B', '-m', 'unittest', '-v',
                       'test.test_configparser', 'test.test_configparser_write_safety']
        else:
            (root / 'checker.py').write_bytes(checker())
            command = [sys.executable, '-B', 'checker.py']
        environment = {**os.environ, 'PYTHONPATH': str(root / 'Lib')}
        completed = subprocess.run(command, cwd=root, env=environment, capture_output=True, timeout=90)
        return dict(returncode=completed.returncode, stdout=completed.stdout.decode(), stderr=completed.stderr.decode())


def main(version):
    folder = material.AREA / f'cpu-qualification-{version}'
    folder.mkdir(exist_ok=False)
    result = dict(completion_requests=0, native_requests=0, cases={})
    try:
        for name, raw in [('saved_baseline', material.baseline_files()[material.LIBRARY]),
                          ('minimal_backport', material.reference_library()),
                          ('pinned_upstream', material.reference_source().encode())]:
            outcome = direct(raw, name)
            result['cases'][name] = outcome
            assert outcome['successful'] is (name != 'saved_baseline'), name
        files = reference_work.files()
        fixtures = dict(correct=files,
            unsafe_write={**files, material.LIBRARY: material.baseline_with_exception()},
            vacuous_test={**files, material.NEW_TESTS: b'import unittest\nclass Empty(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n'},
            missing_documentation={**files, material.DOC: material.baseline_files()[material.DOC]})
        for name, candidate in fixtures.items():
            outcome = run(candidate)
            result['cases']['checker_'+name] = outcome
            assert (outcome['returncode'] == 0) is (name == 'correct'), name
            report = json.loads(outcome['stdout'])
            assert report['passed'] is (name == 'correct')
            if name == 'unsafe_write':
                assert report['contract']['failures'] > 0
                assert 'InvalidWriteError not raised' in outcome['stdout']
        for name, candidate, expected in [('correct', files, 0), ('unsafe_write', fixtures['unsafe_write'], 1)]:
            outcome = run(candidate, ordinary=True)
            result['cases']['ordinary_'+name] = outcome
            assert outcome['returncode'] == expected, name
        result['status'] = 'qualified_cpu_only'
    except BaseException as error:
        result.update(status='failed_preserved', error=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        result['sources'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in material.AREA.glob('*.py')}
        (folder / 'RESULTS.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']), completion_requests=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    main(parser.parse_args().version)
