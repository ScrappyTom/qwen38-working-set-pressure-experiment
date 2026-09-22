"""Reuse the qualified finite lifecycle; no implicit retry or coaching."""
import argparse
from types import SimpleNamespace

import navigation_task as task
import run_repairs
from working_set_exp.jsonutil import sha256_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('case', choices=('shift', 'receipts'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = task.Task(args.case, args.version)
    task.qualification_bindings()
    if args.mode == 'prepare':
        run_repairs.prepare(module)
    else:
        run_repairs.runner.run_once(SimpleNamespace(owner_direction=run_repairs.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)), module)
