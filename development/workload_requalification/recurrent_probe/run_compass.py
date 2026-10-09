"""Use the existing owned-runtime controller; one original COMPASS attempt."""
import argparse
import compass_task as study
import compass_qualification
import compass_native_forms
import run_phase as controller


def configure():
    controller.qualification_route = compass_qualification
    controller.native_forms = compass_native_forms
    return controller


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare','run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    task = study.Task(args.version)
    configured = configure()
    configured.prepare(task) if args.mode == 'prepare' else configured.run_once(task)
