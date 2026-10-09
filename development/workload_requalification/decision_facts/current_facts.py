"""Opt-in decision facts; frozen historical renderers and ledgers stay unchanged."""
from working_set_exp.jsonutil import sha256_bytes


def merge_ranges(ranges):
    merged = []
    for first, last in sorted(ranges):
        if not merged or first > merged[-1][1] + 1:
            merged.append([first, last])
        else:
            merged[-1][1] = max(merged[-1][1], last)
    return merged


class CurrentFactsMixin:
    def source_in_view(self, view):
        """Use the existing delivery routes, never selection inventory or accounts."""
        sources = list(view['working_set']['sources'])
        pages = list(view['working_set']['saved_results'])
        if view['latest_feedback']:
            result = view['latest_feedback']['result']
            pages.extend(result.get('saved_results', []))
            if result.get('kind') == 'saved_bytes':
                pages.append(result)
        for page in pages:
            sources.extend(self._archived_sources_visible(page))
        exact = []
        for source in sources:
            raw = self.candidate.file_map.get(source.get('path'))
            if raw is None or source.get('file_sha256') != sha256_bytes(raw):
                continue
            lines = raw.decode().splitlines(keepends=True)
            first, last = source.get('returned_start_line'), source.get('returned_end_line')
            valid = (type(first) is int and type(last) is int and
                     (1 <= first <= last <= len(lines) or not lines and (first, last) == (1, 0)))
            if not valid or source.get('content') != ''.join(lines[first-1:last]):
                raise ValueError('coverage projection differs from exact current source')
            exact.append(source)
        return exact

    def view(self, **kwargs):
        value = super().view(**kwargs)
        exact = self.source_in_view(value)
        rows = []
        for prior in value['phase']['required_source_delivery']:
            ranges = [*prior['previously_presented_ranges'], *[
                [s['returned_start_line'], s['returned_end_line']] for s in exact
                if s['path'] == prior['path'] and s['file_sha256'] == prior['file_sha256']]]
            merged = merge_ranges(ranges)
            row = {k: v for k, v in prior.items() if k not in ('previously_presented_ranges', 'complete')}
            row.update(presented_ranges_including_this_input=merged,
                complete=bool(merged and merged[0][0] == 1 and merged[0][1] >= prior['file_total_lines']))
            rows.append(row)
        value['phase']['required_source_delivery'] = rows
        value['phase']['coverage_meaning'] = (
            'Exact current-file extents in earlier delivered inputs plus this input. '
            'Historical extents need not remain visible. Coverage is not edit authority '
            'or proof of understanding.')
        value['schema_version'] = 'decision-facts-v1'
        return value

    def summary(self, sequence):
        row = super().summary(sequence)
        pair = self.pairs[sequence-1]
        if (pair['response']['action'] == 'replace_region' and pair['result'].get('accepted')
                and 'path' in pair['result']):
            # A recorded effect remains identifiable after its region becomes stale.
            row['path'] = pair['result']['path']
        return row


def operating_reference(text):
    old = ('Coverage records previously delivered exact source on unchanged file bytes, not current '
           'visibility or understanding.')
    if text.count(old) != 1:
        raise ValueError('expected one original recurrent coverage description')
    return text.replace(old,
        'Phase coverage includes earlier delivered exact current-file extents plus the source '
        'actually in this input. It does not grant editing authority or establish understanding. '
        'The host commits delivery only at the ordinary presentation boundary.')
