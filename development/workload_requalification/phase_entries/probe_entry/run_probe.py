"""Use the existing phase controller with the declared probe task/qualification."""
import argparse

import probe_bootstrap
import probe_task as study
import probe_native_forms
import probe_qualification
import run_phase as controller

controller.native_forms = probe_native_forms
controller.qualification_route = probe_qualification


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    task = study.Task(args.version)
    controller.prepare(task) if args.mode == 'prepare' else controller.run_once(task)
