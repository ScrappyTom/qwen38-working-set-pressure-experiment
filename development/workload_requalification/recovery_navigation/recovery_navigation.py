"""Optional exact recent navigation in the existing bounded recovery view."""
from __future__ import annotations

import copy

import navigation
import search_navigation
from working_set_exp.jsonutil import canonical_json_bytes


def project(view, pairs, candidate, summaries, *,
            page_limit=navigation.MAX_NAVIGATION_PAGES,
            byte_limit=navigation.NAVIGATION_BYTES):
    """Reuse the ordinary projection without making it required control state.

    Both the rows and their optional detail share the byte allowance. Oldest rows
    yield if even their summaries exceed it. The existing admission loop tries
    fewer detailed pages, then -1; that last choice preserves the original view
    exactly. This function never changes archived records or source authority.
    """
    if type(page_limit) is not int or not -1 <= page_limit <= navigation.MAX_NAVIGATION_PAGES:
        raise ValueError('navigation page limit outside the supported bounded range')
    if type(byte_limit) is not int or byte_limit < 0:
        raise ValueError('navigation byte limit invalid')
    result = copy.deepcopy(view)
    if view.get('presentation', {}).get('mode') != 'recovery' or page_limit < 0:
        return result
    if result.get('recent_activity'):
        raise ValueError('recovery predecessor already supplies recent activity')
    baseline_bytes = len(canonical_json_bytes(result))
    rows = copy.deepcopy(summaries[-navigation.MAX_NAVIGATION_PAGES:])
    # Do not resurrect old navigation merely because newer actions are not reads.
    first = max(1, len(pairs)-navigation.MAX_NAVIGATION_PAGES+1)
    if any(type(row.get('sequence')) is not int or
           not first <= row['sequence'] <= len(pairs) for row in rows):
        raise ValueError('summary outside the actual recent operation window')
    result['recent_activity'] = rows
    while rows and len(canonical_json_bytes(result))-baseline_bytes > byte_limit:
        rows.pop(0)
    row_bytes = len(canonical_json_bytes(result))-baseline_bytes
    assert 0 <= row_bytes <= byte_limit
    result = search_navigation.project(result, pairs, candidate,
        page_limit=page_limit, byte_limit=byte_limit-row_bytes)
    assert len(canonical_json_bytes(result))-baseline_bytes <= byte_limit
    return result


class RecoveryNavigationMixin:
    """Place before the already-qualified search/navigation-enabled session.

    The existing last-receipt setting and admission fallbacks control this view;
    no additional checkpoint field, model action, or acquisition is introduced.
    """
    def view(self, **kwargs):
        value = super().view(**kwargs)
        if not self.recovery:
            return value
        limit = self.last.get(navigation.SETTING, navigation.MAX_NAVIGATION_PAGES) if self.last else navigation.MAX_NAVIGATION_PAGES
        limit = limit if self.navigation_enabled else -1
        count = len(self.pairs)
        rows = [self.summary(i) for i in range(max(1, count-navigation.MAX_NAVIGATION_PAGES+1), count+1)]
        return project(value, self.pairs, self.candidate, rows,
                       page_limit=limit, byte_limit=self.navigation_byte_limit)
