"""Inspect requested source without reviving omitted bulk or duplicating extents."""
from .recovery_detail_session import RecoveryDetailSession
from .working_session import WorkingSession


class RecoveryInspectionSession(RecoveryDetailSession):
    # Immutable address records: ref, path, file version, first line, last line.
    # These stay outside the decision view and supply no source-delivery authority.
    parked_source_regions = ()

    def _remember_focus_regions(self):
        rows = list(self.parked_source_regions)
        known = {row[0] for row in rows}
        for span in self.recovery_focus:
            source = self.source(span)
            if source['region_ref'] not in known:
                rows.append((source['region_ref'], source['path'], source['file_sha256'],
                             source['returned_start_line'], source['returned_end_line']))
                known.add(source['region_ref'])
        self.parked_source_regions = tuple(rows)

    def resolve_region(self, reference):
        for ref, path, fingerprint, first, last in self.parked_source_regions:
            if ref == reference:
                if fingerprint != self.candidate.file_sha256(path):
                    raise ValueError('source region is stale; obtain a current source reference')
                return dict(path=path, start_line=first, end_line=last)
        return super().resolve_region(reference)

    def _record(self, action, result):
        super()._record(action, result)
        if self.recovery and action['action'] == 'read' and result.get('accepted'):
            self._remember_focus_regions()
            self.recovery_focus = self._verified_source_ranges([self.source(span) for span in self.recovery_focus])

    def _fit_pages(self, action, spans, handles, measure, replace):
        if self.recovery and not replace:
            staged = self.clone()
            staged._remember_focus_regions()
            # Designated ranges and archive remain untouched. Omitted inspections
            # do not automatically become current source bodies on the next read.
            staged.recovery_focus = self._verified_source_ranges(self.view()['working_set']['sources'])
            staged.control_tier = 0
            staged._inspect_only = False
            return WorkingSession._fit_pages(staged, action, spans, handles, measure, False)
        return super()._fit_pages(action, spans, handles, measure, replace)
