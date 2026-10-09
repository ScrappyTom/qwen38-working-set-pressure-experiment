"""Evaluator-side actual-input audit; no task policy, source selection or model call."""
import json

from working_set_exp.jsonutil import sha256_bytes


def source_rows(value):
    if not isinstance(value, dict):
        return []
    if value.get('kind') == 'current_source':
        return [value]
    rows = []
    for key in ('source', 'sources'):
        item = value.get(key)
        for row in item if isinstance(item, list) else [item]:
            if isinstance(row, dict):
                rows.extend(source_rows(row))
    return rows


def actual_sources(view):
    rows = list(view['working_set']['sources'])
    pages = list(view['working_set']['saved_results'])
    latest = view.get('latest_feedback')
    if latest:
        result = latest['result']
        rows.extend(source_rows(result))
        pages.extend(result.get('saved_results', []))
        if result.get('kind') == 'saved_bytes':
            pages.append(result)
    for page in pages:
        if (page.get('kind') == 'saved_bytes' and page.get('handle', '').startswith('RES-')
                and page.get('offset') == 0 and page.get('next_offset') is None):
            raw = page['exact_utf8'].encode()
            if len(raw) != page['total_bytes'] or sha256_bytes(raw) != page['sha256']:
                raise ValueError('historical source page does not exactly recover its result')
            rows.extend(source_rows(json.loads(raw)))
    return rows


class Trace:
    def __init__(self, module):
        self.module = module
        self.original = module.starting_files()
        self.coverage = {path: set() for path in module.REQUIRED_INSPECTION_PATHS}
        self.witnesses, self.decisions = [], []
        self.sequence = 0
        self.first_primary = self.first_policy = self.first_secondary = None
        self.policy_changes, self.policy_acquisitions, self.policy_deliveries = [], [], []
        self.submitted_from_current_pass = False

    def observe(self, tag, view, operations, versions):
        rows = actual_sources(view)
        witnessed = set()
        for source in rows:
            path, identity = source['path'], source['candidate_id']
            if identity not in versions:
                raise ValueError('presented source version is not recorded')
            raw = versions[identity].file_map[path]
            first, last = source['returned_start_line'], source['returned_end_line']
            lines = raw.decode().splitlines(keepends=True)
            expected = ''.join(lines[first - 1:last]) if lines else ''
            if (source['file_sha256'] != sha256_bytes(raw) or source['content'] != expected
                    or first < 1 or (lines and not first <= last <= len(lines))):
                raise ValueError('actual presented source extent does not match recorded bytes')
            key = (path, identity, first, last)
            if key in witnessed:
                continue
            witnessed.add(key)
            if path in self.coverage and raw == self.original[path]:
                self.coverage[path].update(range(first, last + 1))
                self.witnesses.append(dict(request=tag, path=path, candidate_id=identity,
                    first=first, last=last, file_sha256=source['file_sha256']))
            if path == self.module.POLICY and self.policy_changes:
                change = self.policy_changes[-1]
                requests = [r for r in self.policy_acquisitions
                    if r['sequence'] > change['sequence'] and r['file_sha256'] == source['file_sha256']]
                if requests and source['file_sha256'] == change['file_sha256']:
                    self.policy_deliveries.append(dict(request=tag, acquisition_sequence=requests[-1]['sequence'],
                        policy_change_sequence=change['sequence'], file_sha256=source['file_sha256'],
                        candidate_id=identity, first=first, last=last, delivered_before_sequence=self.sequence + 1))
        effects = []
        for operation in operations:
            self.sequence += 1
            action, result = operation['action'], operation['result']
            kind = action['action']
            effects.append(dict(sequence=self.sequence, action=kind, accepted=result.get('accepted'),
                path=result.get('path', action.get('path'))))
            if not result.get('accepted'):
                continue
            if kind in ('patch', 'replace_region'):
                path = result['path']
                if path == self.module.TARGET and self.first_primary is None:
                    self.first_primary = self.sequence
                if path == self.module.POLICY:
                    if self.first_policy is None:
                        self.first_policy = self.sequence
                    self.policy_changes.append(dict(sequence=self.sequence, file_sha256=result['file_sha256']))
                if path == self.module.SECONDARY and self.first_secondary is None:
                    self.first_secondary = self.sequence
            if kind in ('read', 'work_on', 'work_on_exact'):
                for source in source_rows(result):
                    if source['path'] == self.module.POLICY:
                        self.policy_acquisitions.append(dict(sequence=self.sequence,
                            file_sha256=source['file_sha256'], candidate_id=source['candidate_id']))
            if kind == 'submit':
                self.submitted_from_current_pass = bool(view['verification']['submission']['eligible'])
        self.decisions.append(dict(request=tag, candidate_id=view['candidate_id'], effects=effects,
            supplied_source_extents=[dict(path=p, candidate_id=c, first=f, last=l) for p,c,f,l in sorted(witnessed)],
            complete_ledgers=[p for p, seen in self.coverage.items()
                if seen == set(range(1, len(self.original[p].decode().splitlines()) + 1))]))

    def result(self):
        complete = {path: seen == set(range(1, len(self.original[path].decode().splitlines()) + 1))
                    for path, seen in self.coverage.items()}
        ordered = all(v is not None for v in (self.first_primary, self.first_policy, self.first_secondary))
        ordered = bool(ordered and self.first_primary < self.first_policy < self.first_secondary)
        reacquired = bool(self.first_secondary and any(
            row['policy_change_sequence'] < row['acquisition_sequence'] < self.first_secondary
            and row['delivered_before_sequence'] <= self.first_secondary
            for row in self.policy_deliveries))
        return dict(complete_ledger_delivery=complete, all_ledgers_delivered=all(complete.values()),
            first_primary=self.first_primary, first_policy=self.first_policy, first_secondary=self.first_secondary,
            prescribed_edit_order=ordered, requested_current_policy_delivered_before_secondary=reacquired,
            submitted_from_current_pass=self.submitted_from_current_pass,
            temporal_contract_met=all(complete.values()) and ordered and reacquired and self.submitted_from_current_pass,
            ledger_witnesses=self.witnesses, policy_changes=self.policy_changes,
            policy_acquisitions=self.policy_acquisitions, policy_deliveries=self.policy_deliveries,
            decisions=self.decisions,
            limits=['Exact acquisition and order are distinct from interpretation and behavioral correctness.',
                'Automatic source refresh is not credited as a requested policy reacquisition.',
                'Actual terminal receipts have no subsequent delivery claim.'])
