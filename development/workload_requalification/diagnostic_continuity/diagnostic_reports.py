"""Opt-in complete diagnostic access; historical capture/acceptance are unchanged."""
import copy

import configparser_reports as legacy
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

FIELD_BYTES = 768
PAGE_RECORDS = 2
OVERVIEW_DETAIL_BYTES = 6144


def fragments(text):
    raw = text.encode('utf-8')
    start = 0
    while start < len(raw) or (start == 0 and not raw):
        end = min(len(raw), start + FIELD_BYTES)
        while end < len(raw) and raw[end] & 0xC0 == 0x80:
            end -= 1
        yield dict(text=raw[start:end].decode('utf-8'), start_byte=start,
                   end_byte=end, total_bytes=len(raw), complete=start == 0 and end == len(raw),
                   field_sha256=sha256_bytes(raw))
        if end == len(raw):
            break
        start = end


def assessment(store, handle, contract=None):
    value = legacy.assessment(store, handle, contract)
    pages, by_scope = [], []
    full = None
    if value['assessment_available']:
        full = load_json_strict((store.directory(handle) / 'stdout.bin').read_bytes())
    for criterion in value['criteria']:
        name = criterion['criterion'].removesuffix('.execution')
        if full is None or name not in legacy.SUITES[:3]:
            continue
        details = full[name]['details']
        displayed = []
        for number, detail in enumerate(details):
            start = len(pages)
            label = legacy.bounded_text(detail['test'].encode(), 240, 384)
            for field in ('test', 'trace'):
                for part in fragments(detail[field]):
                    pages.append(dict(criterion=criterion['criterion'], diagnostic_index=number,
                        field=field, test_label=label, **part))
            short = legacy.diagnostic(detail)
            short.update(criterion=criterion['criterion'], diagnostic_index=number,
                inspect=dict(action='inspect_check', observation=handle, offset=start),
                record_start=start, record_end_exclusive=len(pages))
            displayed.append(short)
        by_scope.append(displayed)
        # Scope outcomes stay visible; an edited-test expectation is not promoted
        # to a contract. Exact details have their own directly addressable pages.
        for key in ('diagnostics', 'diagnostics_shown', 'diagnostics_remaining', 'diagnostic_access'):
            criterion.pop(key, None)
        criterion['diagnostics_total'] = len(details)
        if displayed:
            criterion['diagnostic_access'] = displayed[0]['inspect']
    # Round-robin ordinary failing scopes, so one suite's many subtests cannot
    # hide the existence and first diagnostic of another current failing suite.
    diagnostics = []
    for index in range(max((len(rows) for rows in by_scope), default=0)):
        diagnostics.extend(rows[index] for rows in by_scope if index < len(rows))
    value.update(diagnostic_details=diagnostics, diagnostic_records=pages)
    return value


def public_metadata(value):
    return {key:copy.deepcopy(item) for key,item in value.items()
            if key not in ('diagnostic_details', 'diagnostic_records')}


def overview(value):
    result = public_metadata(value)
    details = value['diagnostic_details']
    shown = []
    for detail in details:
        if len(canonical_json_bytes([*shown,detail])) > OVERVIEW_DETAIL_BYTES:
            break
        shown.append(detail)
    result.update(diagnostics=copy.deepcopy(shown), diagnostics_total=len(details),
        diagnostics_shown=len(shown), diagnostics_remaining=len(details)-len(shown),
        diagnostic_record_count=len(value['diagnostic_records']),
        diagnostic_detail_serialized_byte_limit=OVERVIEW_DETAIL_BYTES,
        diagnostic_paging='inspect_check offset indexes exact diagnostic field fragments, not criteria; follow next_offset. Compact scope outcomes remain in criteria.')
    if len(details) > len(shown):
        result['next_unshown_diagnostic'] = copy.deepcopy(details[len(shown)]['inspect'])
    return result


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value['diagnostic_records']
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('diagnostic record offset is outside this observation')
    page = rows[offset:offset+PAGE_RECORDS]
    return dict(accepted=True, kind='check_diagnostic_fields', **public_metadata(value),
        entries=copy.deepcopy(page), offset=offset, total_records=len(rows),
        next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
        all_records_shown=offset == 0 and len(page) == len(rows),
        field_fragment_rule='Each entry contains exact UTF-8 bytes of its named test or trace field. Only complete=true establishes the whole field is shown; use byte extents and next_offset for the rest.')
