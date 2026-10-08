"""Reuse native form evidence only when the actual decoder contract is identical."""
import closure_task as entry
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def qualify(folder, *, task, request, source_identities):
    old_task = entry.previous.Task('001')
    old = task.read(old_task.PACKAGE/'initial-wire-request.json')
    assert request['messages'][0] == old['messages'][0]
    assert {k:v for k,v in request.items() if k != 'messages'} == {k:v for k,v in old.items() if k != 'messages'}
    qualified = task.read(old_task.PACKAGE/'QUALIFICATION.json')['native_forms']
    assert qualified['status'] == 'passed'
    assert all(row['accepted_including_eos'] == row['expected'] for row in qualified['cases'])
    folder.mkdir(parents=True, exist_ok=False)
    result = dict(status='reused_exact_decoder_contract', previously_executed_cases=len(qualified['cases']),
        new_decoder_cases=0, completion_requests=0,
        preparation_seal_sha256=sha256_file(old_task.PACKAGE/'SEAL.json'),
        source_qualification_sha256=sha256_file(old_task.PACKAGE/'QUALIFICATION.json'),
        source_wire_sha256=sha256_file(old_task.PACKAGE/'initial-wire-request.json'),
        same_system_instruction=True, same_nonmessage_wire_fields=True,
        meaning='The new user input is measured through the actual native runtime; unchanged grammar specimens are not rerun.')
    (folder/'REUSE.json').write_bytes(canonical_json_bytes(result))
    return result
