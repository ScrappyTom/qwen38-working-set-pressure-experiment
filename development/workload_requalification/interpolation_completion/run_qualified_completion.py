"""Run the unchanged prepared job with the qualified checkpoint adapter."""
import argparse
import qualified_task
import run_completion as original


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--version', default='002')
    args = parser.parse_args()
    execution = original.execution
    execution.Loop = execution.runner.Loop = original.Loop
    execution.qualification_route = original.qualification_route
    function = execution.prepare if args.mode == 'prepare' else execution.run_once
    function(qualified_task.Task(args.version))


if __name__ == '__main__':
    main()
