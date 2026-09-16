"""Project captured doctest failures as identified records, never one orphaned tail.

This changes no execution or pass criterion. Unknown textual report formats remain
available as exact observations without inferred example/outcome associations.
"""
import copy
import re

from . import feedback_assessment as prior
from .jsonutil import load_json_strict, sha256_bytes
from .observations import text_tail

HEADER = re.compile(
    r'^\*{70}\nFile "([^"\r\n]+)", line ([0-9]+), in ([^\r\n]+)\nFailed example:\n',
    re.MULTILINE)
OUTCOME = re.compile(r'^(Exception raised:|Expected:|Expected nothing)\n', re.MULTILINE)
MAX_SHOWN = 4
MAX_RECORD_BYTES = 4096


def failure_records(text, failures):
    """Recognize complete standard DocTestRunner blocks, or decline association."""
    if not text and failures == 0:
        return []
    if not isinstance(text, str) or type(failures) is not int:
        return None
    headers = list(HEADER.finditer(text))
    if not headers or headers[0].start() != 0 or len(headers) != failures:
        return None
    records = []
    for index, header in enumerate(headers):
        end = headers[index+1].start() if index+1 < len(headers) else len(text)
        block = text[header.start():end]
        body = text[header.end():end]
        outcome = OUTCOME.search(body)
        if not outcome:
            return None
        source = body[:outcome.start()]
        # The runner indents the exact example four spaces. Do not parse arbitrary
        # unindented text as an example or attach a later failure's header to it.
        if not source or any(line and not line.startswith('    ') for line in source.splitlines()):
            return None
        reported = body[outcome.end():]
        kind = 'unexpected_exception' if outcome[1] == 'Exception raised:' else 'output_mismatch'
        if kind == 'unexpected_exception':
            if not reported.startswith('    Traceback (most recent call last):\n'):
                return None
        elif not re.search(r'^Got(?::\n| nothing\n)', reported, re.MULTILINE):
            return None
        raw = block.encode('utf-8')
        records.append(dict(
            test=f'{header[1]}:{header[2]}',
            location=dict(path=header[1], line=int(header[2]), test_name=header[3]),
            failure_kind=kind,
            meaning=('The example raised an exception that doctest did not accept as its expected outcome.'
                     if kind == 'unexpected_exception' else 'The example output differed from the expected output.'),
            failed_example=text_tail(''.join(line[4:] for line in source.splitlines(True)).encode(), 1024),
            diagnostic=text_tail(raw, MAX_RECORD_BYTES),
            complete_record_sha256=sha256_bytes(raw),
            # Offsets refer to the decoded examples.details UTF-8 string, not the
            # enclosing serialized stdout stream. Recovery uses the observation.
            detail_start_byte=len(text[:header.start()].encode()),
            detail_end_byte=len(text[:end].encode())))
    return records


def assessment(store, handle, contract=None):
    value = prior.assessment(store, handle, contract)
    if not value['assessment_available']:
        return value
    full = load_json_strict((store.directory(handle) / 'stdout.bin').read_bytes())
    examples = full.get('examples')
    if not isinstance(examples, dict):
        return value
    records = failure_records(examples.get('details', ''), examples.get('failures'))
    for row in value['criteria']:
        if row['criterion'] != 'examples.execution':
            continue
        row.update(diagnostics=[] if records is None else records[:MAX_SHOWN],
                   diagnostic_parse_status='unsupported_format' if records is None else 'complete_failure_boundaries',
                   observed_failures=examples.get('failures'),
                   parsed_failure_records=0 if records is None else len(records),
                   unassociated_failures=examples.get('failures') if records is None else 0)
        prior.counts(row, 'diagnostics', 0 if records is None else len(records), MAX_SHOWN)
        row['diagnostic_access'] = dict(value['raw_access'])
        if records is None:
            row['diagnostic_note'] = ('No location/outcome associations inferred from this unsupported report. '
                                      'Inspect the exact preserved observation.')
    return value


def overview(value):
    result = prior.overview(value)
    by_name = {r['criterion']:r for r in value['criteria']}
    for row in result['criteria']:
        if row['criterion'] == 'examples.execution':
            original = by_name[row['criterion']]
            row['diagnostics'] = copy.deepcopy(original['diagnostics'])
            prior.counts(row, 'diagnostics', original['diagnostics_total'], MAX_SHOWN)
    return result


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete criterion records')
    page = rows[offset:offset+4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page, offset=offset,
                total_records=len(rows), next_offset=offset+len(page) if offset+len(page)<len(rows) else None,
                records_complete=True, all_records_shown=offset == 0 and len(page) == len(rows))
