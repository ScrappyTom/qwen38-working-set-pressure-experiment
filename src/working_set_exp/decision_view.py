"""One visible-source location and an optional literal replacement body."""
import copy
import re

from . import operable_view, working_view
from .accounted_contribution import operating_reference as base_reference
from .jsonutil import load_json_strict


def action_rule(checks):
    forms = copy.deepcopy(operable_view.action_rule(checks)['oneOf'])
    forms += [working_view.obj(dict(action=dict(type='string',const='inspect_check'),
                observation=dict(type='string',pattern='^CHK-[0-9]{4,}$'),offset=dict(type='integer',minimum=0))),
              working_view.obj(dict(action=dict(type='string',const='replace_region'),
                region=dict(type='string',pattern='^SRC-[0-9a-f]{64}$'),
                expected_candidate_id=dict(type='string',pattern='^[0-9a-f]{64}$'),new=dict(type='string')))]
    return dict(oneOf=forms)


def reply_schema(checks):
    schema = copy.deepcopy(operable_view.reply_schema(checks))
    schema['json_schema']['name'] = 'decision_contribution_v1'
    for form in schema['json_schema']['schema']['oneOf']:
        if 'operation' in form['properties']:
            form['properties']['operation'] = action_rule(checks)
    return schema


def source_header_schema():
    operation = working_view.obj(dict(action=dict(type='string',const='replace_region'),
        region=dict(type='string',pattern='^SRC-[0-9a-f]{64}$'),
        expected_candidate_id=dict(type='string',pattern='^[0-9a-f]{64}$')))
    return dict(oneOf=[working_view.obj(dict(discussion=dict(type='string'),operation=operation)),
                      working_view.obj(dict(discussion=dict(type='string'),account=dict(type='string'),operation=operation))])


def decode_reply(content):
    # JSON header is deliberately one line. Split only the first exact separator;
    # source may itself contain SOURCE, JSON, CRLF, quotes, backslashes or Unicode.
    if '\nSOURCE\n' not in content:
        return load_json_strict(content.encode())
    header, body = content.split('\nSOURCE\n', 1)
    if '\n' in header or '\r' in header:
        raise ValueError('literal source reply header must be one JSON line')
    reply = load_json_strict(header.encode())
    working_view.validate(reply, source_header_schema())
    reply['operation']['new'] = body
    return reply


def reply_grammar(checks, converter_class):
    converter = converter_class(prop_order={}, allow_fetch=False, dotall=False, raw_pattern=False)
    ordinary = converter.visit(reply_schema(checks)['json_schema']['schema'], 'ordinary-reply')
    header_converter = converter_class(prop_order={}, allow_fetch=False, dotall=False, raw_pattern=False)
    header = header_converter.visit(source_header_schema(), 'source-header')
    header_rules = header_converter.format_grammar()
    names = set(re.findall(r'^([\w-]+) ::=', header_rules, re.M))
    # Namespace header primitives so its whitespace can forbid actual newlines
    # without changing ordinary JSON. Quoted grammar literals stay byte-identical.
    header_rules = re.sub(r'"(?:\\.|[^"\\])*"|[A-Za-z_][\w-]*',
                         lambda m:'h-'+m[0] if m[0] in names else m[0], header_rules)
    header_rules = re.sub(r'^h-space ::=.*$', r'h-space ::= [ \t]*', header_rules, flags=re.M)
    return (converter.format_grammar() + '\n' + header_rules + '\nroot ::= ' + ordinary + ' | h-' + header +
            ' "\\nSOURCE\\n" [\\x00-\\U0010FFFF]*\n')


def operating_reference(checks):
    effects = dict(operable_view.EFFECTS)
    effects.update(
        search='Literal case-insensitive current-source search with offset/limit paging. Returns exact match locations and reusable context regions. For parseable Python, it also identifies the complete enclosing function region mechanically. A region address is not visible source: read or work_on_exact must actually deliver its body before editing.',
        read='Reads exact current source. Returned pages remain selected across later reads and operations until work_on replaces selection. Recovery retains its inspected pages together; bulk hidden designations remain stored. Actual visibility is listed in working_set.sources and visibility. A genuine capacity fallback explicitly marks retained bodies omitted; it never claims they remain visible. end_line=0 means onward, not a promise of the entire remainder; use actual returned extents.',
        check='Executes the named version-bound check. Preserves raw observations before deriving explicit assessment criteria. Ordinary tests must pass; injected faults must make the new tests fail or error. Mutation-run missing paths are not additional requirements. Applicable failed criteria remain in verification after subsequent operations. Use inspect_check for complete criterion records and inspect_observation for raw captured bytes.',
        inspect_check='Returns up to four complete assessment records, unmet criteria first. offset=0 starts; next_offset continues records, not bytes. Diagnostic text may be explicitly abbreviated with exact raw observation access. Never reruns a check or changes source selection.',
        inspect_observation='Advanced exact raw-byte access to stdout, stderr or outcome. Does not rerun a check. observation_capture_complete says whether capture finished; page_complete and shown_bytes describe this page. Prefer inspect_check for coherent diagnostic records. A raw page may end within serialized data and supplies no source-edit authority.',
        replace_region='Replaces the complete observed source region with literal new text. Copy its region reference and current candidate. The host resolves exact old bytes and file identity; no old-text repetition or file-hash copying is required. The entire region must be visible current source; stale bindings are rejected. Existing edit limits, atomic admission, source refresh and declared successor checks apply. Empty replacement deletes the region. Use the literal SOURCE reply to avoid JSON-escaping code.',
    )
    text = base_reference(checks, forms=action_rule(checks)['oneOf'], effect_overrides=effects)
    text = text.replace('Reply with one JSON object.', 'For ordinary actions, reply with one JSON object.')
    text = text.replace('it does not truncate accounts or silently release selected evidence.',
                        'it preserves exact stored account text. Full account display is attempted first; only actual capacity pressure permits a labelled display prefix. Stored text is never shortened.')
    text = text.replace('With work_on, account and replacement', 'With work_on or work_on_exact, account and replacement')
    text += ('\n\nAll visible current-source bodies are in working_set.sources, regardless of which operation delivered them. '
             'Feedback contains source references instead of duplicate bodies. visibility distinguishes shown evidence from retained but omitted designations. '
             'verification.checks contains all scopes with applicability; verification.submission states whether a current public pass exists. '
             'A failed check is an outstanding assessment, not a claim that every nested test execution should pass. '
             'Accounts remain authored interpretations and are never automatically endorsed.\n\n'
             'Optional literal source reply: emit a single-line JSON header with discussion, optional account, and '
             'operation {"action":"replace_region","region":"SRC-...","expected_candidate_id":"..."}, '
             'then a newline, the word SOURCE, another newline, and the exact replacement source through the end of the reply. '
             'Do not JSON-escape that source or wrap it in Markdown fences. The header has no new field; the host supplies it from the literal body. '
             'Trailing newlines are source bytes. Ordinary JSON replies remain valid. Only complete final replies execute; thinking is never used as a proposal.')
    # Inherited instructions describe legacy feedback source placement; remove it.
    text = text.replace(working_view.INPUT_INTERPRETATION, 'The working set is the actual content in this input; stored or designated content may be explicitly omitted.')
    return text


def present_receipts(view, receipts):
    return [receipt_view(r) for r in receipts if not view['latest_feedback'] or r['sequence']!=view['latest_feedback']['sequence']]


def receipt_view(receipt):
    if not receipt:
        return None
    value = copy.deepcopy(receipt)
    result = value['result']
    if result.get('kind')=='observation_bytes' and 'capture_complete' in result:
        result['observation_capture_complete']=result.pop('capture_complete')
        result['shown_bytes']=(result['next_offset'] or result['captured_bytes'])-result['offset']
        result['page_complete']=result['offset']==0 and result['next_offset'] is None
        result['raw_page_may_split_serialized_record']=not result['page_complete']
    sources = ([result.pop('source')] if 'source' in result else result.pop('sources', []))
    if sources:
        result['source_regions'] = [{k:s[k] for k in ('path','file_sha256','returned_start_line','returned_end_line','region_ref') if k in s} for s in sources]
        result['source_body_location'] = 'working_set.sources if shown; otherwise visibility marks omission'
    return value
