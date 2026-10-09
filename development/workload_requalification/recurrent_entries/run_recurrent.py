"""Use the existing owned-runtime controller for the original four-phase task."""
import argparse

import recurrent_task as study
import recurrent_qualification
import run_phase as controller
import native_forms


def configure():
    controller.qualification_route = recurrent_qualification
    controller.native_forms = native_forms
    return controller


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    task = study.Task(args.version)
    configured = configure()
    configured.prepare(task) if args.mode == 'prepare' else configured.run_once(task)
