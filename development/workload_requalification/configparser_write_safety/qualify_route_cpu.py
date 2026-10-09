"""Exercise the exact scripted route without claiming native input measurement."""
import argparse
from pathlib import Path
import bootstrap
import write_task as study
import qualification_route
from manage import legacy
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes


class CPUInput:
    def __init__(self, log):
        self.log = log

    def measure(self, view):
        return 1  # Deliberate admission stub: native token qualification follows.


def main(version):
    folder = study.AREA/f'cpu-route-{version}'
    folder.mkdir(exist_ok=False)
    store = ArtifactStore(folder)
    task = study.Task()
    log = legacy.QualificationLog(folder/'records.jsonl', 'write-safety-cpu-route', task_module=task)
    from run_uncoached_contribution import Adapter
    try:
        result = qualification_route.qualify(task, CPUInput(log), Adapter(task), store, folder)
        result.update(status='qualified_cpu_route_only', native_token_measurement=False,
                      completion_requests=0, records=len(verify_records(folder/'records.jsonl', folder)))
    except BaseException as error:
        store.put('FAILED.json', canonical_json_bytes(dict(type=type(error).__name__, message=str(error),
                                                         native_token_measurement=False, completion_requests=0)))
        raise
    store.put('RESULTS.json', canonical_json_bytes(result))
    print(result['status'], result['decisions'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    main(parser.parse_args().version)
