"""Task-local native qualification of the source-selection reply boundary.

The unchanged action_lifecycle helper covers ordinary edits and literal SOURCE
transport but has no group-selection specimen. Extend its cases in an isolated
module, retaining its actual pinned vocabulary/sampler, decoder, bytes and seal.
No operation is executed and this module provides no standalone runtime launch.
"""
import importlib.util
import json
from pathlib import Path


def selection_cases(task):
    """Public synthetic decoder specimens, never an actor source arrangement."""
    def case(name, operation, accepted=True, account=None):
        fields = dict(discussion='Inspect the requested source selection.')
        if account is not None:
            fields['account'] = account
        fields['operation'] = operation
        final = json.dumps(fields, ensure_ascii=False, separators=(',', ':'))
        return dict(name=name, text='</think>\n'+final, final=final,
                    expected=accepted)

    sources = [dict(path=path, start_line=1, end_line=0)
               for path in task.REQUIRED_INSPECTION_PATHS[:4]]
    group = dict(action='work_on', sources=sources, results=[])
    exact = dict(action='work_on_exact', regions=['SRC-'+'a'*64], results=[])
    yield case('source_group_work_on', group)
    yield case('source_and_saved_record_group',
               dict(action='work_on', sources=sources[:1], results=['RES-0001']))
    yield case('identified_region_work_on_exact', exact)
    yield case('empty_group_release', dict(action='work_on', sources=[], results=[]))
    yield case('empty_exact_group_release', dict(action='work_on_exact', regions=[], results=[]))
    yield case('account_and_source_group', group,
               account='The selected sources remain to be examined; this is not a check.')
    yield case('account_and_exact_group', exact,
               account='Preserve the unresolved question while changing the selection.')
    yield case('selection_inventory_page', dict(action='selection_page', offset=0))
    yield case('archive_history_page', dict(action='history', before=0, path=''))
    yield case('group_missing_results', dict(action='work_on', sources=sources), False)
    yield case('group_wrong_source_shape',
               dict(action='work_on', sources=['src/example.py'], results=[]), False)
    yield case('exact_group_wrong_region_shape',
               dict(action='work_on_exact', regions=[dict(path='src/example.py')], results=[]), False)
    yield case('group_unsupported_field', {**group, 'automatically_check': True}, False)


def qualify(folder, *, task, request, decode_reply=None, source_identities=None):
    """Use the inherited keyword API; only the runtime owner calls qualification."""
    root = Path(task.ROOT)
    helper_path = root / 'development/workload_requalification/action_lifecycle/native_forms.py'
    spec = importlib.util.spec_from_file_location('ecological_import_native_base', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)

    schema = task.reply_schema()['json_schema']['schema']
    operation_forms = next(form['properties']['operation']['oneOf']
                           for form in schema['oneOf'] if 'operation' in form['properties'])
    names = {form['properties']['action']['const'] for form in operation_forms}
    if not {'work_on', 'work_on_exact', 'selection_page', 'history'} <= names:
        raise ValueError('Advertised selection/history action forms differ')
    identity = source_identities or task.implementation_identities
    wrapper = Path(__file__).resolve().relative_to(root.resolve()).as_posix()
    if wrapper not in identity():
        raise ValueError('Task-local native selection helper is not source-bound')

    inherited_cases = helper.cases
    def all_cases(checks, original_final):
        yield from inherited_cases(checks, original_final)
        yield from selection_cases(task)
    helper.cases = all_cases
    return helper.qualify(folder, task=task, request=request,
                          decode_reply=decode_reply, source_identities=identity)
