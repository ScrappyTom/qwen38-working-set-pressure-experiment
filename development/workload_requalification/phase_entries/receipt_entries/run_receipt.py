"""Run one declared original case through the existing owned-runtime controller."""
import argparse

import receipt_task as study
import receipt_qualification
import probe_native_forms
import native_forms
import run_phase as controller


def configure(task):
    controller.native_forms=probe_native_forms if task.config['probe'] else native_forms
    controller.qualification_route=receipt_qualification
    return controller


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--case',choices=study.CASES,required=True)
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    task=study.Task(args.version,case=args.case)
    controller=configure(task)
    controller.prepare(task) if args.mode=='prepare' else controller.run_once(task)
