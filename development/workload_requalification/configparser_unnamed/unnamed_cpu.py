"""Qualify the task contract against ordinary execution before model exposure."""
import argparse
import doctest
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

import bootstrap
import corrected_checker
import unnamed_material as material
import unnamed_reference as reference
from unnamed_contract import UnnamedContract
from working_set_exp.jsonutil import sha256_file


def checker():
    return (b'CONFIG = '+repr(material.checker_configuration()).encode()+b'\n'+
        (material.AREA/'unnamed_contract.py').read_bytes()+b'\n'+
        corrected_checker.contract_source()+b'\n'+
        (material.AREA/'unnamed_checker_program.py').read_bytes())


def load(raw, name):
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(raw, name, 'exec'), module.__dict__)
    return module


def direct(raw, name):
    library = load(raw, name)
    UnnamedContract.library = library
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(UnnamedContract))
    return dict(successful=result.wasSuccessful(), tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), output=stream.getvalue())


def run(files, ordinary=False):
    with tempfile.TemporaryDirectory(prefix='unnamed-coding-') as temp:
        root = Path(temp)
        for name, raw in files.items():
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        if ordinary:
            command = [sys.executable, '-B', '-m', 'unittest', '-v',
                'test.test_configparser', 'test.test_configparser_write_safety', 'test.test_configparser_unnamed']
        else:
            (root/'checker.py').write_bytes(checker())
            command = [sys.executable, '-B', 'checker.py']
        result = subprocess.run(command, cwd=root,
            env={**os.environ, 'PYTHONPATH': str(root/'Lib')}, capture_output=True, timeout=90)
        return dict(returncode=result.returncode, stdout=result.stdout.decode(), stderr=result.stderr.decode())


def mutants(raw):
    cases = {
        'sentinel_converted_to_string': ('            if section is not UNNAMED_SECTION:\n                section = str(section)',
                                       '            section = str(section)'),
        'unnamed_header_emitted': ('        if section_name is not UNNAMED_SECTION:\n            fp.write("[{}]\\n".format(section_name))',
                                  '        fp.write("[{}]\\n".format(section_name))'),
        'unnamed_write_guard_skipped': ('            self._validate_write_key(key)',
                                       '            if section_name is not UNNAMED_SECTION:\n                self._validate_write_key(key)'),
    }
    unnamed = ('        if self._sections.get(UNNAMED_SECTION):\n'
        '            self._write_section(fp, UNNAMED_SECTION,\n'
        '                                self._sections[UNNAMED_SECTION].items(), d)\n')
    defaults = ('        if self._defaults:\n            self._write_section(fp, self.default_section,\n'
                '                                    self._defaults.items(), d)\n')
    cases['defaults_written_first'] = (unnamed+defaults, defaults+unnamed)
    text = raw.decode()
    for name, (old, new) in cases.items():
        assert text.count(old) == 1, name
        yield name, text.replace(old, new).encode()


def main(version):
    folder = material.AREA/f'cpu-qualification-{version}'
    folder.mkdir(exist_ok=False)
    proof = dict(completion_requests=0, native_calls=0, cases={})
    # Preserve exact sources before any checks, with short package-relative paths.
    paths = [*material.AREA.glob('*.py'), *material.AREA.glob('*.txt'),
             *material.AREA.glob('*.md'), *sorted((material.AREA/'tests').glob('*.py'))]
    proof['sources'] = {}
    for path in paths:
        relative = path.relative_to(material.AREA)
        destination = folder/'sources'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
        proof['sources'][relative.as_posix()] = sha256_file(path)
    try:
        files = reference.files()
        for name, raw, expected in [('saved_baseline', material.baseline_files()[material.LIBRARY], False),
            ('independent_feature', files[material.LIBRARY], True),
            ('pinned_314_reference', material.upstream_library(), False),
            *((name, raw, False) for name, raw in mutants(files[material.LIBRARY]))]:
            value = direct(raw, 'qualify_'+name)
            proof['cases'][name] = value
            assert value['successful'] is expected, (name, value)
            if name == 'pinned_314_reference':
                assert value['failures'] > 0, 'Record reference limitations, not an oracle pass.'
        fixtures = dict(correct=files, saved_baseline=material.starting_files(),
            vacuous_tests={**files, material.NEW_TESTS: b'import unittest\nclass Empty(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n'},
            missing_documentation={**files, material.DOC: material.baseline_files()[material.DOC]})
        for name, candidate in fixtures.items():
            value = run(candidate)
            proof['cases']['checker_'+name] = value
            report = json.loads(value['stdout'])
            assert report['passed'] is (name == 'correct')
            assert (value['returncode'] == 0) is (name == 'correct')
        ordinary = run(files, ordinary=True)
        proof['cases']['ordinary_reference'] = ordinary
        assert ordinary['returncode'] == 0
        library = load(files[material.LIBRARY], 'configparser')
        example = doctest.DocTestParser().get_doctest(reference.DOC_ADDITION,
            {'__name__': '__main__', 'configparser': library}, 'unnamed-example', 'configparser.rst', 0)
        output = io.StringIO()
        runner = doctest.DocTestRunner(verbose=True)
        result = runner.run(example, out=output.write)
        proof['cases']['ordinary_example'] = dict(failed=result.failed, attempted=result.attempted, output=output.getvalue())
        assert result.attempted == 5 and result.failed == 0
        completed = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover',
            '-s', str(material.AREA/'tests'), '-v'], capture_output=True, timeout=120)
        proof['integration'] = dict(returncode=completed.returncode,
            stdout=completed.stdout.decode(), stderr=completed.stderr.decode())
        assert completed.returncode == 0, proof['integration']
        proof['status'] = 'qualified_cpu_only'
    except BaseException as problem:
        proof.update(status='failed_preserved', error=dict(type=type(problem).__name__, message=str(problem)))
        raise
    finally:
        (folder/'RESULTS.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    print(dict(status=proof['status'], cases=len(proof['cases']), completion_requests=0), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    main(parser.parse_args().version)
