"""Evaluator-only information-path qualification; never an actor input or oracle.

The report is derived from the exact capture bodies actually displayed together.
The original check's EXPECTED_REPORT and donor source are not consulted.
"""
import ast
import copy

from working_set_exp.accounted_contribution import process_reply
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes

TARGET, REPORT = 'compiler/unary.py', 'reports/incident.json'
OLD = '        if isinstance(node.op, (ast.UAdd, ast.USub)):\n'
GOOD = ('        if isinstance(node.op, ast.UAdd) and isinstance(node.operand, ast.Constant) '
        'and type(node.operand.value) in (int, float):\n')


def decode_tree(text):
    """Decode only the AST constructor notation present in the sealed captures."""
    parsed = ast.parse(text, mode='eval')
    proof = copy.deepcopy(parsed)
    # The preserved incident records are Python 3.12 notation. This evaluator
    # may run under 3.11; empty type-parameter fields have no comparison content.
    # Do not silently drop unknown or nonempty later-version syntax.
    for call in ast.walk(proof):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
            cls = getattr(ast, call.func.id, None)
            if isinstance(cls, type) and issubclass(cls, ast.AST) and 'type_params' not in cls._fields:
                compatible = [key for key in call.keywords if key.arg == 'type_params']
                if compatible:
                    if (call.func.id not in ('FunctionDef', 'AsyncFunctionDef', 'ClassDef')
                            or len(compatible) != 1 or not isinstance(compatible[0].value, ast.List)
                            or compatible[0].value.elts):
                        raise ValueError('unsupported captured type parameters')
                    call.keywords.remove(compatible[0])
    def decode(node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            cls = getattr(ast, node.func.id, None)
            if not (isinstance(cls, type) and issubclass(cls, ast.AST) and not node.args):
                raise ValueError('non-AST constructor')
            fields = [key.arg for key in node.keywords]
            if len(set(fields)) != len(fields) or any(name not in cls._fields for name in fields):
                raise ValueError('unknown or repeated AST field')
            return cls(**{key.arg: decode(key.value) for key in node.keywords})
        if isinstance(node, ast.List):
            return [decode(child) for child in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(decode(child) for child in node.elts)
        return ast.literal_eval(node)
    tree = decode(proof.body)
    if (not isinstance(tree, ast.Module)
            or ast.dump(ast.parse(ast.dump(tree), mode='eval')) != ast.dump(proof)):
        raise ValueError('captured tree does not round trip')
    return tree


def first_changed_expression(left, right):
    if isinstance(left, ast.expr) and isinstance(right, ast.expr) and type(left) is not type(right):
        return {'before': ast.unparse(left), 'after': ast.unparse(right)}
    if isinstance(left, ast.AST) and type(left) is type(right):
        for field in left._fields:
            found = first_changed_expression(getattr(left, field, None), getattr(right, field, None))
            if found:
                return found
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise ValueError('list cardinality changed; this qualification definition needs review')
        for before, after in zip(left, right):
            found = first_changed_expression(before, after)
            if found:
                return found
    return None


def derive_report(bodies):
    """Compare delivered observations, not requested scope or checker answers."""
    if set(bodies) != {'OBS-0001', 'OBS-0002', 'OBS-0003'}:
        raise ValueError('all three exact capture bodies are required')
    records = {handle: load_json_strict(raw) for handle, raw in bodies.items()}
    original = decode_tree(records['OBS-0001']['ast_dump'])
    functions = [node for node in original.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    rows = []
    for handle in ('OBS-0002', 'OBS-0003'):
        emitted = decode_tree(records[handle]['ast_dump'])
        successors = {node.name: node for node in emitted.body
                      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        changed = [node for node in functions if ast.dump(node) != ast.dump(successors[node.name])]
        first = None
        for node in changed:
            expression = first_changed_expression(node, successors[node.name])
            if expression:
                first = {'function': node.name, **expression}
                break
        if not first:
            raise ValueError('captured build lacks a changed expression')
        rows.append({'capture': handle, 'changed_functions': [node.name for node in changed],
                     'first_change': first})
    return {'builds': rows}


def delivered_capture_bodies(view):
    """Inspect explicit shown receipts and complete shown RES bodies only."""
    result = {}
    receipts = []
    pages = list(view['working_set']['saved_results'])
    latest = view.get('latest_feedback')
    if latest:
        receipt = latest['result']
        receipts.append(receipt)
        pages.extend(receipt.get('saved_results', []))
        if receipt.get('kind') == 'saved_bytes':
            pages.append(receipt)
    for page in pages:
        if (page.get('kind') == 'saved_bytes' and page.get('offset') == 0
                and page.get('next_offset') is None and 'exact_utf8' in page):
            raw = page['exact_utf8'].encode()
            if len(raw) != page['total_bytes'] or sha256_bytes(raw) != page['sha256']:
                raise ValueError('displayed saved result identity differs')
            receipts.append(load_json_strict(raw))
    for receipt in receipts:
        if receipt.get('accepted') and receipt.get('kind') == 'imported_observation':
            raw = receipt['content_utf8'].encode()
            if len(raw) != receipt['size_bytes'] or sha256_bytes(raw) != receipt['sha256']:
                raise ValueError('displayed capture identity differs')
            handle = receipt['handle']
            if handle in result and result[handle] != raw:
                raise ValueError('one capture has conflicting displayed bodies')
            result[handle] = raw
    return result


def delivered_sources(view):
    sources = list(view['working_set']['sources'])
    latest = view.get('latest_feedback')
    if latest:
        result = latest['result']
        sources.extend([result['source']] if 'source' in result else result.get('sources', []))
    return {row['path']: row for row in sources}


def qualify_contribution(session, measure, record=None, *, correction=False):
    """One researcher-selected route through real tools and actual input views.

    measure is the production request/template/tokenizer callback for native
    qualification. Unit tests use an explicitly synthetic zero-cost callback.
    Every saved before/after view can be independently checked for the evidence
    justifying that scripted choice; this is feasibility, not model selection.
    """
    snapshots, preceding = [], []
    initial = session.candidate

    def act(action, basis, account=None):
        before = session.view()
        count = measure(before)
        session.mark_delivered(before)
        session.begin_request()
        reply = {'discussion': basis, 'operation': action}
        if account is not None:
            reply['account'] = account
        outcome = process_reply(session, reply, measure, preceding)
        assert all(op['result'].get('accepted') for op in outcome['operations']), outcome
        after = session.view()
        next_count = measure(after)
        row = {'before_view': copy.deepcopy(before), 'reply': reply,
               'outcome': copy.deepcopy(outcome), 'after_view': copy.deepcopy(after),
               'input_tokens': count, 'next_input_tokens': next_count,
               'candidate_after': session.candidate.candidate_id,
               'basis_scope': 'researcher-selected engineering qualification, not actor trajectory'}
        snapshots.append(row)
        if record:
            record(row)
        return outcome['operations'][-1]['result']

    act({'action': 'read', 'path': 'README.md', 'start_line': 1, 'end_line': 0},
        'Root inventory names README.md; inspect the task contract and report definition.')
    act({'action': 'p0_page', 'path': 'compiler', 'offset': 0},
        'Root inventory identifies compiler; discover its actual source paths.')
    acquired = []
    for handle in ('OBS-0001', 'OBS-0002', 'OBS-0003'):
        act({'action': 'reopen_observation', 'handle': handle},
            'Initial imported inventory identifies this prior incident capture; retrieve its exact body.')
        acquired.append(f'RES-{len(session.pairs):04d}')
        assert delivered_capture_bodies(session.view())[handle] == session.imported_record(handle)[1]
    sources = [{'path': path, 'start_line': 1, 'end_line': 0}
               for path in ('README.md', 'compiler/api.py', 'compiler/selection.py', TARGET, REPORT)]
    act({'action': 'work_on', 'sources': sources, 'results': acquired},
        'README supplies the report contract; discovered compiler files supply implementation; '
        'the three acquired RES receipts supply original and both builds for comparison.')
    shown = session.view()
    bodies = delivered_capture_bodies(shown)
    assert bodies == {handle: session.imported_record(handle)[1] for handle in ('OBS-0001', 'OBS-0002', 'OBS-0003')}
    text = delivered_sources(shown)
    assert 'exact built-in integer and float literals' in text['README.md']['content']
    assert OLD in text[TARGET]['content']
    assert text[REPORT]['content'] == initial.file_map[REPORT].decode()
    report = derive_report(bodies)
    replacement = '        if isinstance(node.op, ast.UAdd):\n' if correction else GOOD
    act({'action': 'patch', 'path': TARGET, 'old': OLD, 'new': replacement,
         'expected_candidate_id': session.candidate.candidate_id,
         'expected_file_sha256': session.candidate.file_sha256(TARGET)},
        'Visible README requires literal-plus folding and preserving other dispatch; visible unary implementation removes both signs.')
    shown = session.view()
    assert delivered_capture_bodies(shown) == bodies
    assert delivered_sources(shown)[REPORT]['content'] == initial.file_map[REPORT].decode()
    act({'action': 'patch', 'path': REPORT, 'old': initial.file_map[REPORT].decode(),
         'new': canonical_json_bytes(report).decode()+'\n',
         'expected_candidate_id': session.candidate.candidate_id,
         'expected_file_sha256': session.candidate.file_sha256(REPORT)},
        'All three exact capture bodies remain displayed; compare ASTs in README-defined order rather than selected names or repair check.')
    check = {'action': 'check', 'check_id': 'public', 'expected_candidate_id': session.candidate.candidate_id}
    result = act(check, 'Both saved work products exist; execute the original acceptance check on this successor.')
    if correction:
        assert result['passed'] is False
        # The failing dispatch criterion establishes the broad UAdd rule is not
        # adequate. Exact current source and README remain available for repair.
        shown = session.view()
        assert replacement in delivered_sources(shown)[TARGET]['content']
        assert 'operator dispatch' in delivered_sources(shown)['README.md']['content']
        act({'action': 'patch', 'path': TARGET, 'old': replacement, 'new': GOOD,
             'expected_candidate_id': session.candidate.candidate_id,
             'expected_file_sha256': session.candidate.file_sha256(TARGET)},
            'Actual failed check rejects broad plus removal; still-visible contract requires preserving custom dispatch.')
        result = act({**check, 'expected_candidate_id': session.candidate.candidate_id},
                     'Consume the saved correction and check its actual successor.')
    assert result['passed'] is True
    act({'action': 'submit', 'expected_candidate_id': session.candidate.candidate_id},
        'The current candidate has the actual applicable public pass.')
    assert session.submitted
    assert all(session.candidate.file_map[path] == raw for path, raw in initial.files if path not in (TARGET, REPORT))
    return {'status': 'qualified_no_model_inference', 'completion_requests': 0,
            'scripted_requests': session.requests_used, 'scripted_operations': session.calls_used,
            'maximum_input_tokens': max(row['next_input_tokens'] for row in snapshots),
            'report_derived_from_delivered_captures': report, 'candidate_id': session.candidate.candidate_id,
            'snapshots': snapshots}


def qualify(module, loop, adapter, store, folder):
    """Native runner hook: direct route and real failed-check correction route."""
    trials, checks = [], []
    initial = module.initial_session()
    initial_bytes = canonical_json_bytes(module.snapshot(initial))
    for label, correction in (('direct', False), ('failed_check_correction', True)):
        session = module.initial_session()
        module.attach_observations(session, folder/'scripted'/label, loop.log)
        adapter.preceding_feedback.clear()
        loop.snapshot(session, f'scripted/{label}/starting')
        n = 0
        def record(row):
            nonlocal n
            n += 1
            artifact = store.put(f'scripted/{label}/steps/{n:02d}.json', canonical_json_bytes(row))
            loop.log.append('scripted_information_path_step',
                {'route': label, 'step': n, 'input_tokens': row['input_tokens'],
                 'next_input_tokens': row['next_input_tokens'], 'completion_sent': False}, [artifact])
        value = qualify_contribution(session, loop.measure, record, correction=correction)
        loop.snapshot(session, f'scripted/{label}/final')
        summary = {key: item for key, item in value.items() if key != 'snapshots'}
        store.put(f'scripted/{label}/RESULTS.json', canonical_json_bytes(summary))
        trials.append({'route': label, **summary})
        checks.extend({'route': label, 'step': i+1, 'passed': op['result']['passed'],
                       'candidate_id': op['result']['checked_candidate_id']}
                      for i,row in enumerate(value['snapshots'])
                      for op in row['outcome']['operations'] if op['action']['action'] == 'check')
    assert canonical_json_bytes(module.snapshot(initial)) == initial_bytes
    assert [row['passed'] for row in checks] == [True, False, True]
    # An inefficient but legal selection of actual repeated capture acquisitions
    # must produce useful recovery, rather than require a fitting normal body.
    # This is native capacity stress, not extra task evidence or model behavior.
    session = module.initial_session()
    module.attach_observations(session, folder/'scripted'/'capacity_recovery', loop.log)
    previous = []
    steps = []
    def act(action, accepted=True):
        session.mark_delivered(session.view())
        session.begin_request()
        reply = {'discussion':'Scripted native capacity transition qualification.', 'operation':action}
        outcome = process_reply(session, reply, loop.measure, previous)
        result = outcome['operations'][-1]['result']
        assert result['accepted'] is accepted, outcome
        count = loop.measure(session.view())
        row = {'reply':reply, 'outcome':outcome, 'next_view':copy.deepcopy(session.view()), 'input_tokens':count}
        steps.append(row)
        artifact = store.put(f'scripted/capacity_recovery/steps/{len(steps):02d}.json',canonical_json_bytes(row))
        loop.log.append('scripted_capacity_path_step',{'step':len(steps),'input_tokens':count,'completion_sent':False},[artifact])
        return result
    spans = [{'path':path,'start_line':1,'end_line':0} for path in ('README.md',TARGET,REPORT)]
    for span in spans:
        act({'action':'read',**span})
    handles=[];complete={}
    for handle in ('OBS-0001',)*6+('OBS-0002','OBS-0003'):
        act({'action':'reopen_observation','handle':handle})
        address=f'RES-{len(session.pairs):04d}'
        handles.append(address);complete[handle]=address
    before = (session.candidate,copy.deepcopy(session.ranges),copy.deepcopy(session.saved))
    result = act({'action':'work_on','sources':spans,'results':handles},accepted=False)
    assert 'fit' in result['error'] or 'place' in result['error'], result
    assert (session.candidate,session.ranges,session.saved)==before
    assert session.view()['presentation']['mode']=='recovery' and not session.delivery_blocked
    assert not delivered_capture_bodies(session.view())
    assert not session.view()['working_set']['sources']
    assert len(session.pairs)==12 and len(session._imported_bodies)==3
    # The inventory exposes the exact successful acquisition references; no
    # source coordinates or oracle report are supplied from a private solution.
    inventory=session.view()['imported_observations']['entries']
    assert {r['handle']:r['latest_acquisition_result'] for r in inventory}==complete
    act({'action':'work_on','sources':spans,'results':list(complete.values())})
    shown=session.view()
    assert shown['presentation']['mode']=='ordinary'
    report=derive_report(delivered_capture_bodies(shown))
    assert OLD in delivered_sources(shown)[TARGET]['content']
    act({'action':'patch','path':TARGET,'old':OLD,'new':GOOD,
         'expected_candidate_id':session.candidate.candidate_id,
         'expected_file_sha256':session.candidate.file_sha256(TARGET)})
    act({'action':'patch','path':REPORT,'old':session.candidate.file_map[REPORT].decode(),
         'new':canonical_json_bytes(report).decode()+'\n',
         'expected_candidate_id':session.candidate.candidate_id,
         'expected_file_sha256':session.candidate.file_sha256(REPORT)})
    checked=act({'action':'check','check_id':'public','expected_candidate_id':session.candidate.candidate_id})
    assert checked['passed']
    act({'action':'submit','expected_candidate_id':session.candidate.candidate_id})
    assert session.submitted
    loop.snapshot(session,'scripted/capacity_recovery/final')
    checks.append({'route':'capacity_recovery','passed':True,'candidate_id':session.candidate.candidate_id})
    trials.append({'route':'capacity_recovery','status':'qualified_no_model_inference','completion_requests':0,
        'scripted_requests':session.requests_used,'scripted_operations':session.calls_used,
        'maximum_input_tokens':max(r['input_tokens'] for r in steps),
        'oversized_group_rejected':True,'previous_selection_preserved':True,
        'complete_replacement_delivered':True,'checked_submission':True})
    adapter.preceding_feedback.clear()
    return {'trials': trials, 'checks': checks, 'checks_executed': 4,
            'completion_requests': 0, 'model_starting_state_untouched': True}
