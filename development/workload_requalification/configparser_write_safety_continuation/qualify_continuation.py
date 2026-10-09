"""CPU checker/environment and exact continuation tests, without inference."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import bootstrap
import corrected_checker
import material
import reference_work

AREA = Path(__file__).resolve().parent


def main(version):
    folder = AREA/f'cpu-qualification-{version}'
    folder.mkdir(exist_ok=False)
    result = dict(completion_requests=0, native_requests=0, cases={})
    try:
        files = reference_work.files()
        raw = files[material.LIBRARY]
        marker = b'        Error.__init__(self, msg)'
        start = raw.index(b'class InvalidWriteError(Error):')
        end = raw.index(b'class Interpolation:', start)
        exception = raw[start:end]
        assert exception.count(marker) == 1
        alternate = raw[:start] + exception.replace(marker,
            b"        Error.__init__(self, 'Invalid write: ' + msg)") + raw[end:]
        fixtures = dict(correct=files,
            different_valid_diagnostic={**files, material.LIBRARY: alternate},
            unsafe_write={**files, material.LIBRARY: material.baseline_with_exception()},
            vacuous_tests={**files, material.NEW_TESTS:
                b'import unittest\nclass Empty(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n'},
            missing_documentation={**files, material.DOC: material.baseline_files()[material.DOC]})
        for name, candidate in fixtures.items():
            outcome = corrected_checker.run(candidate)
            result['cases']['checker_'+name] = outcome
            expected = name in ('correct', 'different_valid_diagnostic')
            report = json.loads(outcome['stdout'])
            assert (outcome['returncode'] == 0) is expected and report['passed'] is expected, name
            if name == 'unsafe_write':
                assert report['contract']['failures'] > 0
            if name == 'vacuous_tests':
                assert report['new_tests_on_original']['failures'] == 0
        for name in ('correct', 'different_valid_diagnostic', 'unsafe_write'):
            outcome = corrected_checker.run(fixtures[name], ordinary=True)
            result['cases']['ordinary_'+name] = outcome
            assert (outcome['returncode'] == 0) is (name != 'unsafe_write'), name
        outcome = corrected_checker.direct(alternate, 'alternative_diagnostic')
        result['cases']['direct_alternative_diagnostic'] = outcome
        assert outcome['successful']
        completed = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover',
            '-s', str(AREA/'tests'), '-v'], capture_output=True, timeout=120)
        result['integration_tests'] = dict(returncode=completed.returncode,
            stdout=completed.stdout.decode(), stderr=completed.stderr.decode())
        assert completed.returncode == 0, result['integration_tests']
        result['status'] = 'qualified_cpu_only'
    except BaseException as error:
        result.update(status='failed_preserved', error=dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        result['sources'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in AREA.glob('*.py')}
        (folder/'RESULTS.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']), completion_requests=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    main(parser.parse_args().version)
