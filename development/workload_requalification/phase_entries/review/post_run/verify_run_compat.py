"""Supplement the frozen verifier; never modify the sealed run or bound code."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_run as original
from snapshot_compat import restored_diff_keys
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def verify(version):
    with restored_diff_keys(original.study.Task):
        result = original.verify(version)
    result['restore_compatibility'] = dict(
        reason='Recover original integer diff-map key types after JSON decoding; all original restore and replay checks remain active.',
        verifier_sha256=sha256_file(Path(__file__)),
        compatibility_sha256=sha256_file(Path(__file__).with_name('snapshot_compat.py')),
        original_failure_sha256=sha256_file(Path(__file__).parents[1] / f'VERIFICATION-{version}-FAILED.json'))
    path = Path(__file__).parents[1] / f'VERIFICATION-{version}.json'
    raw = canonical_json_bytes(result)
    if path.exists():
        assert path.read_bytes() == raw
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='002')
    verify(parser.parse_args().version)
