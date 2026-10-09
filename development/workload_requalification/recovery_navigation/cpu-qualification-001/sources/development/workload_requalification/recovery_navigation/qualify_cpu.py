"""Record focused offline tests without overwriting previous attempts."""
import argparse
import io
import json
from pathlib import Path
import unittest

import fixture
from working_set_exp.jsonutil import sha256_file


def main(version):
    folder = fixture.AREA/f'cpu-qualification-{version}'
    if folder.exists():
        raise FileExistsError(folder)
    folder.mkdir()
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(fixture.AREA/'tests'))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    sources = [*fixture.AREA.glob('*.py'), *fixture.AREA.glob('*.md'),
               *(fixture.AREA/'tests').glob('*.py')]
    report = dict(status='passed_cpu_only' if result.wasSuccessful() else 'failed_cpu_only',
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        output=stream.getvalue(), model_completions=0, native_tokenization=0,
        source_sha256={p.relative_to(fixture.ROOT).as_posix():sha256_file(p) for p in sources},
        original_run_seal_sha256=fixture.SEAL_SHA256)
    (folder/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='001')
    raise SystemExit(main(parser.parse_args().version))
