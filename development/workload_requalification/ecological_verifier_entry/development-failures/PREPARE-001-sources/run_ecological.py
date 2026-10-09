"""Reuse the existing owned-runtime lifecycle; one separately sealed attempt."""
import argparse
import bootstrap
import ecological_task as study
import qualification_route

controller = study.load_private('e20_verifier_controller', study.ROOT /
    'development/workload_requalification/ecological_observation_entry/run_ecological.py')
controller.study = study
controller.qualification_route = qualification_route

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare','run'))
    parser.add_argument('--version', default='001')
    args = parser.parse_args()
    module = study.Task(args.version)
    (controller.prepare if args.mode == 'prepare' else controller.run_once)(module)
