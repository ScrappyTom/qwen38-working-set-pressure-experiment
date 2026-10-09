"""Prospective original-task assessment; no actor input or host policy changes.

The earlier Trace is deliberately preserved. Its all-ledgers-before-every-edit
condition is not an original task requirement. Exact recovered action/result
pages get direct assessment if the narrower capture recognizer does not qualify
them. An archive address, account assertion or partial page supplies no such proof.
"""
import argparse
import json
from pathlib import Path

import bootstrap
import observation_task as study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def exact_historical_pages(envelope, pairs):
    view = envelope['workspace']
    receipts = [r['result'] for r in envelope.get('preceding_operation_feedback', [])]
    if view.get('latest_feedback'):
        receipts.append(view['latest_feedback']['result'])
    pages = list(view['working_set']['saved_results'])
    for result in receipts:
        pages.extend(result.get('saved_results', []))
        if result.get('kind')=='saved_bytes':
            pages.append(result)
    exact = {}
    for page in pages:
        handle = page.get('handle', '')
        if (page.get('kind')!='saved_bytes' or not handle.startswith(('EVT-', 'RES-'))
                or page.get('offset')!=0 or page.get('next_offset') is not None):
            continue
        index = int(handle.split('-')[1])
        assert 1 <= index <= view['archive']['action_count'] <= len(pairs)
        field = 'response' if handle.startswith('EVT-') else 'result'
        raw = canonical_json_bytes(pairs[index-1][field])
        assert (page['total_bytes'], page['sha256'], page['exact_utf8'].encode()) == (len(raw), sha256_bytes(raw), raw)
        exact[handle] = dict(handle=handle, producing_action=pairs[index-1]['response']['action'],
            sha256=sha256_bytes(raw), size_bytes=len(raw), exact_payload=load_json_strict(raw))
    return list(exact.values())


def criteria(audit, artifact, alternative_pages):
    submitted = [r for r in audit['decisions'] if any(e['action']=='submit' and e['accepted'] for e in r['effects'])]
    footer = [r for r in audit['edits'] if r['path']==study.SECONDARY]
    requirements, unresolved = [], []
    for row in footer:
        sequence = row['sequence']
        if row['bound_marker_body_in_this_input']:
            requirements.append(True)
        elif alternative_pages.get(sequence):
            requirements.append(None)
            unresolved.append(sequence)
        else:
            requirements.append(False)
    availability = (False if not requirements or False in requirements
                    else None if None in requirements else True)
    checks = dict(
        complete_required_ledger_delivery_by_submission=len(submitted)==1 and submitted[0]['all_ledgers_delivered'],
        bound_marker_acquired_before_use=bool(audit['edits']) and all(r['bound_marker_previously_delivered'] for r in audit['edits']),
        label_before_footer=audit['label_before_footer'],
        exact_marker_available_or_permitted_recovery=availability,
        consumed_current_public_pass=audit['submitted_from_current_pass'],
        ordinary_artifact_behavior_passed=artifact['ordinary_behavior_passed'],
        other_files_preserved=artifact['only_target_files_changed'] and artifact['unchanged_other_files']==128)
    supported = False if False in checks.values() else None if None in checks.values() else True
    return dict(criteria=checks, original_contract_supported=supported, payloads_needing_direct_review=unresolved)


def evaluate(version):
    run, review = study.AREA/f'run-{version}', study.AREA/'review'
    seal = study.read(run/'RESPONSE_SEAL.json')
    audit = study.read(review/f'TEMPORAL-AUDIT-{version}.json')
    verified = study.read(review/f'VERIFICATION-{version}.json')
    artifact = study.read(review/f'ARTIFACT-ASSESSMENT-{version}.json')
    digest = sha256_file(run/'RESPONSE_SEAL.json')
    assert verified['status']=='replayed_exactly'
    assert all(r['response_seal_sha256']==digest for r in (audit, verified, artifact))
    assert verified['records_sha256']==sha256_file(run/'records.jsonl')
    files = {r['path']:r for r in seal['files']}
    def exact(name):
        path, row = run/name, files[name]
        assert path.stat().st_size==row['size_bytes'] and sha256_file(path)==row['sha256']
        return study.read(path)
    stem = 'final' if (run/'final-state.json').exists() else 'stopped'
    pairs = exact(stem+'-state.json')['pairs']
    pages, requests = {}, {}
    for decision in audit['decisions']:
        sequences = [e['sequence'] for e in decision['effects'] if e['accepted'] and any(
            r['sequence']==e['sequence'] and r['path']==study.SECONDARY for r in audit['edits'])]
        if not sequences:
            continue
        request = exact('calls/'+decision['request']+'-wire-request.json')
        envelope = load_json_strict(request['messages'][-1]['content'])
        assert envelope['workspace']['task']==study.task_text()
        recovered = exact_historical_pages(envelope, pairs)
        for sequence in sequences:
            pages[sequence] = recovered
            requests[sequence] = decision['request']
    return dict(status='original_task_contract_assessment', version=version,
        prospective_contract=version!='001', response_seal_sha256=digest,
        evaluator_sha256=sha256_file(Path(__file__)), task_sha256=study.TASK_SHA,
        historical_stronger_metric=audit['temporal_contract_met'], historical_metric_preserved=True,
        **criteria(audit, artifact, pages), footer_requests=requests, exact_historical_pages=pages,
        limits=['Exact source eligibility is independently replayed, not supplied by an account.',
            'Delivery is not interpretation. Exact historical payloads require direct semantic support review if the capture proof is absent.',
            'No permitted alternate route is failed merely because it is not a capture receipt.',
            'The contract and evaluator were declared before run002, after observing run001.',
            'Original run001 and its later supplementary assessment remain unchanged.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='002')
    args=parser.parse_args()
    value=evaluate(args.version)
    path=study.AREA/'review'/f'ORIGINAL-CONTRACT-NEXT-{args.version}.json'
    raw=canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes()==raw
    else:
        path.write_bytes(raw)
    print(json.dumps(value,indent=2))
