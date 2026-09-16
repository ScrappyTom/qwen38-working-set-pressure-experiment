"""Prospective feedback/line-boundary repairs; historical DecisionSession unchanged."""
import copy

from . import decision_view, feedback_assessment
from .candidate import canonical_path
from .decision_session import DecisionSession
from .jsonutil import sha256_bytes
from .working_session import MAX_FRAGMENT_BYTES


class FeedbackSession(DecisionSession):
    assessment_api = feedback_assessment

    def source(self, span):
        value = super().source(span)
        total = len(self.candidate.file_map[value['path']].decode().splitlines(keepends=True))
        value.update(file_total_lines=total, returned_extent_complete=True,
            whole_file_shown=value['returned_start_line'] == 1 and value['returned_end_line'] == total)
        return value

    def selection_inventory(self, offset=0, count=8):
        result = super().selection_inventory(offset, count)
        for row in result['entries']:
            if row['kind'] == 'source':
                total = len(self.candidate.file_map[row['path']].decode().splitlines(keepends=True))
                row.update(file_total_lines=total, selected_extent=dict(start_line=row['start_line'], end_line=row['end_line']),
                           selected_extent_is_whole_file=row['start_line'] == 1 and row['end_line'] == total)
        return result

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value['schema_version'] = 'decision-feedback-v2'
        for row in value['visibility']['retained_inventory']['entries']:
            if row['kind'] == 'source':
                shown = row.pop('body_shown_in_full')
                row['selected_extent_shown_in_full'] = shown
                row['whole_file_shown'] = shown and row['selected_extent_is_whole_file']
        return value

    def resolve_region(self, reference):
        # Rejected ambiguous patches expose addresses, not source/edit authority.
        for pair in reversed(self.pairs):
            for region in pair['result'].get('match_regions', []):
                if region['region_ref'] == reference:
                    if self.candidate.file_sha256(region['path']) != region['file_sha256']:
                        raise ValueError('source region is stale; obtain a current source reference')
                    return {k:region[k] for k in ('path', 'start_line', 'end_line')}
        return super().resolve_region(reference)

    def summary(self, sequence):
        value = super().summary(sequence)
        result = self.pairs[sequence-1]['result']
        for key in ('rejection_code', 'match_count', 'proposed_old_sha256'):
            if key in result:
                value[key] = result[key]
        return value

    def _patch(self, action):
        if action['action'] == 'patch':
            path = canonical_path(action['path'])
            if (action['expected_candidate_id'] != self.candidate.candidate_id or
                    action['expected_file_sha256'] != self.candidate.file_sha256(path)):
                return dict(accepted=False, rejection_code='stale_binding', error='Candidate or pre-edit file binding is stale; no edit committed.')
            old, new = action['old'], action['new']
            if max(len(old.encode()), len(new.encode())) > MAX_FRAGMENT_BYTES:
                return dict(accepted=False, rejection_code='fragment_limit', error='Complete edit exceeds 65,536 UTF-8 bytes; no edit committed.')
            text = self.candidate.file_map[path].decode()
            count = text.count(old) if old else 0
            if not old or old == new or count != 1:
                code = ('empty_anchor' if not old else 'unchanged_replacement' if old == new else
                        'old_not_found' if count == 0 else 'ambiguous_old')
                result = dict(accepted=False, rejection_code=code, match_count=count, path=path,
                    proposed_old_sha256=sha256_bytes(old.encode()), proposed_new_sha256=sha256_bytes(new.encode()),
                    exact_action_handle=f'EVT-{len(self.pairs)+1:04d}', match_regions=[])
                reasons = dict(empty_anchor='The old text is empty; use a visible region or nonempty exact anchor.',
                    unchanged_replacement='The replacement equals the old text; no change was proposed.',
                    old_not_found='The exact old text occurs zero times in the current file.',
                    ambiguous_old=f'The exact old text occurs {count} times in the current file. No match was selected. Use an identified visible region or a unique exact anchor.')
                result['error'] = reasons[code]
                offset = 0
                if old:
                    for _ in range(min(count, 4)):
                        start = text.index(old, offset); end = start + len(old)
                        region = self.region(path, self.candidate.file_sha256(path),
                            text[:start].count('\n')+1, text[:end-1].count('\n')+1)
                        region['extent_kind'] = 'whole lines containing exact match; address only'
                        result['match_regions'].append(region)
                        offset = end
                result.update(matches_shown=len(result['match_regions']), matches_remaining=count-len(result['match_regions']))
                previous = next((i for i in range(len(self.pairs)-1, -1, -1)
                    if self.pairs[i]['response'].get('action') == 'patch'
                    and self.pairs[i]['response'].get('path') == path
                    and self.pairs[i]['response'].get('old') == old
                    and not self.pairs[i]['result'].get('accepted')), None)
                if previous is not None:
                    result['same_old_as_rejected_action'] = f'EVT-{previous+1:04d}'
                return result
            return super()._patch(action)
        span = self.resolve_region(action['region'])
        # A whole-line region owns its trailing separator before an unselected
        # following line. Preserve proposal custody separately from constructed text.
        lines = self.candidate.file_map[span['path']].decode().splitlines(keepends=True)
        raw = action['new']
        separator = ''
        if raw and span['end_line'] < len(lines) and not raw.endswith(('\n', '\r')):
            boundary = lines[span['end_line']-1] if span['end_line'] else ''
            separator = '\r\n' if boundary.endswith('\r\n') else '\n' if boundary.endswith('\n') else '\r' if boundary.endswith('\r') else ''
        if raw.endswith('\r') and span['end_line'] < len(lines) and lines[span['end_line']-1].endswith('\r\n'):
            separator = '\n'
        applied = raw + separator
        result = super()._patch({**action, 'new':applied})
        result.update(proposed_text_sha256=sha256_bytes(raw.encode()), applied_text_sha256=sha256_bytes(applied.encode()),
            supplied_boundary_separator=separator, boundary_policy='preserve_separator_before_unselected_line')
        return result


def operating_reference(checks):
    text = decision_view.operating_reference(checks)
    text = text.replace('Ordinary tests must pass; injected faults must make the new tests fail or error.',
        'Ordinary tests must pass before mutation failures count as detection. Each declared fault target must be detected by the new tests; normal failure blocks that assessment.')
    text = text.replace('Empty replacement deletes the region.',
        'This is a whole-line operation. Before an unselected following line, the host supplies a missing original line separator for nonempty replacement text and records it separately from your exact proposal. Empty replacement deletes the region; at EOF the text stays exact. Ordinary patch remains byte-exact.')
    text += ('\nPatch rejection names its cause and returns actual match counts and up to four reusable whole-line match regions. '
        'A region address alone does not grant editing authority; its source must be shown before editing. '
        'same_old_as_rejected_action identifies reuse of an earlier rejected anchor. '
        'file_total_lines and whole_file_shown describe the file; returned_extent_complete and selected_extent_shown_in_full describe only the indicated range. '
        'A complete range is not necessarily a complete file. Reports give total, shown and remaining entries for each shortened list, with exact observations available.')
    return text
