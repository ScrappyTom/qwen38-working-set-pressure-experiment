"""Describe actual delivery and operation costs after closure, not model memory."""
from collections import defaultdict
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import observation_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def evaluate():
    audit = study.read(AREA / 'review/TEMPORAL-AUDIT-001.json')
    metrics = study.read(AREA / 'review/METRICS-001.json')
    verification = study.read(AREA / 'review/VERIFICATION-001.json')
    assert verification['status'] == 'replayed_exactly'
    assert audit['response_seal_sha256'] == metrics['response_seal_sha256'] == verification['response_seal_sha256']
    decisions = {r['request']: r for r in audit['decisions']}
    contexts = {r['id']: r for r in audit['decision_context']}
    seen = {p: set() for p in study.REQUIRED_INSPECTION_PATHS}
    rows, costs = [], defaultdict(list)
    for call in metrics['calls']:
        tag = call['id']
        row = decisions[tag]
        newly_delivered = {}
        for source in row['supplied_sources']:
            path = source['path']
            if path not in seen:
                continue
            values = set(range(source['first'], source['last'] + 1))
            newly_delivered[path] = newly_delivered.get(path, 0) + len(values - seen[path])
            seen[path].update(values)
        actions = contexts[tag]['actions']
        kinds = [r['action']['action'] for r in actions if r['action']['action'] != 'record_account']
        kind = kinds[0] if len(kinds) == 1 else '+'.join(kinds) or 'account_or_no_action'
        acquisition = []
        host_path = AREA / 'run-001/calls' / f'{tag}-host-result.json'
        if host_path.exists():
            for op in study.read(host_path)['operations']:
                result = op['result']
                if not result.get('accepted'):
                    continue
                source_rows = list(result.get('sources', []))
                if 'source' in result:
                    source_rows.append(result['source'])
                for source in source_rows:
                    path = source['path']
                    if path not in seen:
                        continue
                    returned = set(range(source['returned_start_line'], source['returned_end_line'] + 1))
                    acquisition.append(dict(path=path, first=source['returned_start_line'], last=source['returned_end_line'],
                        returned_lines=len(returned), previously_delivered_lines=len(returned & seen[path]),
                        not_previously_delivered_lines=len(returned - seen[path]),
                        later_delivery_separately_recorded=True))
        rows.append(dict(id=tag, operation_kind=kind, call=call, new_ledger_lines_in_this_input=newly_delivered,
            accepted_ledger_acquisitions=acquisition,
            cumulative_delivered_ledger_lines={p: len(v) for p, v in seen.items()}))
        costs[kind].append(tag)
    return dict(status='descriptive_acquisition_analysis', response_seal_sha256=audit['response_seal_sha256'],
        source_sha256=sha256_file(Path(__file__)), calls_by_operation=dict(costs), rows=rows,
        limits=['The required ledgers are artificial custody material, not substantive repair dependencies.',
                'Previously delivered bytes are not necessarily remembered or currently visible.',
                'This does not classify every reacquisition or all generated reasoning as waste.',
                'An accepted terminal acquisition is not credited as subsequent model delivery.',
                'Byte/range authenticity comes from the separately replayed actual-input audit.'])


if __name__ == '__main__':
    value = evaluate()
    path = AREA / 'review/ACQUISITION-COSTS-001.json'
    raw = canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes() == raw
    else:
        path.write_bytes(raw)
    print(json.dumps(dict(status=value['status'], decisions=len(value['rows']), calls_by_operation=value['calls_by_operation']), indent=2))
