"""Evaluator-only actual delivery and conditional recovery audit."""
import importlib.util
import sys
from unittest.mock import patch

from working_set_exp.jsonutil import sha256_bytes


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Trace:
    def __init__(self, module):
        self.module, self.original = module, module.starting_files()
        self.rows, self.inventory, self.bodies = module.imports()
        matches = [row['handle'] for row in self.rows if row['candidate_id'] == module.STARTING_ID]
        assert len(matches) == 1
        self.bound_handle = matches[0]
        with patch.dict(sys.modules, {'compiler_task': module}):
            self.capture = load('e18_capture_inspection', module.ROOT / 'development/workload_requalification/compiler_entry/review/verify_run.py')
        self.source = load('e18_source_inspection', module.ROOT / 'development/workload_requalification/evolving_source_entry/temporal_audit.py')
        self.coverage = {p: set() for p in module.REQUIRED_INSPECTION_PATHS}
        self.sequence = 0
        self.decisions, self.edits, self.deliveries = [], [], []
        self.first_label = self.first_footer = None
        self.submitted_from_current_pass = False

    def observe(self, tag, view, operations, versions, pairs, preceding=()):
        supplied = self.source.actual_sources(view)
        for row in supplied:
            path = row['path']
            raw = versions[row['candidate_id']].file_map[path]
            first, last = row['returned_start_line'], row['returned_end_line']
            assert row['file_sha256'] == sha256_bytes(raw)
            assert row['content'] == ''.join(raw.decode().splitlines(True)[first-1:last])
            if path in self.coverage and raw == self.original[path]:
                self.coverage[path].update(range(first, last+1))
        captures = self.capture._sent_capture_bytes(dict(workspace=view, preceding_operation_feedback=list(preceding)),
            pairs, self.inventory, self.bodies)
        complete = {row['handle'] for row in captures if row['representation'] == 'complete_capture_receipt'
                    or row.get('complete_receipt_shown')}
        if self.bound_handle in complete:
            self.deliveries.append(dict(request=tag, before_sequence=self.sequence+1, handle=self.bound_handle))
        all_ledgers = all(seen == set(range(1,len(self.original[p].decode().splitlines())+1))
            for p,seen in self.coverage.items())
        effects = []
        for operation in operations:
            self.sequence += 1
            action, result = operation['action'], operation['result']
            effects.append(dict(sequence=self.sequence, action=action['action'], accepted=result.get('accepted')))
            if not result.get('accepted'):
                continue
            if action['action'] in ('patch','replace_region'):
                path = result['path']
                if path == self.module.TARGET and self.first_label is None:
                    self.first_label = self.sequence
                if path == self.module.SECONDARY and self.first_footer is None:
                    self.first_footer = self.sequence
                self.edits.append(dict(sequence=self.sequence, path=path, all_ledgers_delivered=all_ledgers,
                    bound_marker_previously_delivered=bool(self.deliveries),
                    bound_marker_body_in_this_input=self.bound_handle in complete))
            if action['action'] == 'submit':
                self.submitted_from_current_pass = bool(view['verification']['submission']['eligible'])
        self.decisions.append(dict(request=tag, candidate_id=view['candidate_id'], effects=effects,
            complete_captures_shown=sorted(complete), capture_extents=captures,
            supplied_sources=[dict(path=r['path'],first=r['returned_start_line'],last=r['returned_end_line']) for r in supplied],
            all_ledgers_delivered=all_ledgers))

    def result(self):
        complete = {p: seen == set(range(1,len(self.original[p].decode().splitlines())+1)) for p,seen in self.coverage.items()}
        ordered = self.first_label is not None and self.first_footer is not None and self.first_label < self.first_footer
        supported = bool(self.edits) and all(row['all_ledgers_delivered'] and row['bound_marker_previously_delivered'] for row in self.edits)
        footer = [row for row in self.edits if row['path'] == self.module.SECONDARY]
        conditional = bool(footer) and all(row['bound_marker_body_in_this_input'] for row in footer)
        return dict(complete_ledger_delivery=complete, first_label=self.first_label, first_footer=self.first_footer,
            label_before_footer=ordered, mutation_prerequisites_supported=supported,
            exact_marker_available_at_footer=conditional, submitted_from_current_pass=self.submitted_from_current_pass,
            temporal_contract_met=all(complete.values()) and ordered and supported and conditional and self.submitted_from_current_pass,
            marker_deliveries=self.deliveries, edits=self.edits, decisions=self.decisions,
            limits=['Delivery is distinct from interpretation.', 'The footer condition uses actual exact bodies, not shown flags or account assertions.',
                'Retaining the marker legitimately avoids reacquisition; release is not mandatory.'])
