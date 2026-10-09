"""Original procedure plus independent behavior after exact closed replay."""
import argparse
from collections import Counter
import difflib
import importlib.util
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import compass_task as study
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load('compass_review_utilities', AREA.parent / 'recurrent_entries/review/post_run/assess.py')
save, execute = common.save, common.execute


def assess(version):
    task = study.Task(version)
    run, folder = task.RUN, AREA / 'review' / version
    verification = task.read(AREA / f'review/VERIFICATION-{version}.json')
    assert verification['status'] == 'replayed_exactly'
    assert verification['executed_manifest_sha256'] == sha256_file(run / 'EXECUTION_MANIFEST.json')
    task.verify_sources(task.read(run / 'EXECUTION_MANIFEST.json')['source_sha256'])
    metric = load('compass_cost_reader', study.ROOT / 'development/workload_requalification/url_port_continuation/review/measure_run.py')
    seal, records = metric.checked_seal(run), metric.records(run)
    calls = metric.calls(run, records)
    operations = [(r['payload']['id'], task.read(run / r['artifacts'][0]['path'])) for r in records
                  if r['record_type'] == 'contribution_operation']
    identity = dict(case=task.CASE, version=version, response_seal_sha256=sha256_file(run / 'RESPONSE_SEAL.json'),
        records_sha256=sha256_file(run / 'records.jsonl'), assessment_sha256=sha256_file(Path(__file__)),
        exact_replay_sha256=sha256_file(AREA / f'review/VERIFICATION-{version}.json'))
    save(folder / 'METRICS.json', dict(**identity, aggregate=metric.aggregate(calls), calls=calls,
        actual_operations=len(operations), operation_types=dict(Counter(o['action']['action'] for _,o in operations)),
        rejected=[dict(id=tag, operation=op) for tag,op in operations if not op['result']['accepted']],
        task_loop=[r['payload'] for r in records if r['record_type']=='task_loop_completed'],
        runtime=seal['runtime'], memory=seal['memory'],
        limits=['Costs exclude preparation, grading and reviewer work.', 'Checks/examples are not independent model trials.']))
    stem = 'final' if (run / 'final-state.json').exists() else 'stopped'
    candidate = task.candidate_from_snapshot(task.read(run / (stem+'-candidate.json')))
    session = task.restore(task.read(run / (stem+'-state.json')), candidate, run, replay=True)
    assert candidate.candidate_id == verification['final_candidate_id']
    before, after = task.starting_files(), candidate.file_map
    changed = [p for p in before if before[p] != after[p]]
    diff = ''.join(''.join(difflib.unified_diff(before[p].decode().splitlines(True), after[p].decode().splitlines(True),
        fromfile='original/'+p, tofile='saved/'+p)) for p in changed)
    save(folder / 'SAVED-PATCH.diff', diff.encode())
    decisions, boundaries, edits, productions, delivered = [], [], [], [], []
    for call in calls:
        tag, number = call['id'], int(call['id'][1:])
        wire = task.read(run / f'calls/{tag}-wire-request.json')
        packet = json.loads(wire['messages'][-1]['content']); view = packet['workspace']
        phase = view['phase']['current']
        assert view['task'] == task.task_text()
        prior = run / 'starting'
        if number > 1:
            states = sorted((run / 'after').glob(f'C{number-1:02d}-O*-state.json'))
            assert states
            prior = states[-1].with_name(states[-1].name.removesuffix('-state.json'))
        checkpoint = task.restore(task.read(Path(str(prior)+'-state.json')),
            task.read(Path(str(prior)+'-candidate.json')), run, replay=True)
        checkpoint.mark_delivered(view)
        pages = list(view['working_set']['saved_results'])
        feedback = [view['latest_feedback'], *packet['preceding_operation_feedback']]
        for receipt in feedback:
            result = (receipt or {}).get('result',{})
            pages.extend(result.get('saved_results',[]))
            if result.get('kind')=='saved_bytes':
                pages.append(result)
        seen = set()
        for page in pages:
            handle = page.get('handle','')
            if handle in seen or page.get('kind')!='saved_bytes' or not handle.startswith('RES-'):
                continue
            if page.get('offset')!=0 or page.get('next_offset') is not None:
                continue
            raw = checkpoint.payload(handle)
            if page.get('exact_utf8','').encode()!=raw or page.get('sha256')!=sha256_bytes(raw) or page.get('total_bytes')!=len(raw):
                continue
            body = load_json_strict(raw)
            if not (body.get('accepted') and body.get('probe_id')=='compatibility' and body.get('observation_kind')=='authored_fixture_output'):
                continue
            seen.add(handle)
            delivered.append(dict(id=tag, phase=phase, original_result=handle,
                producing_sequence=int(handle.split('-')[1]), raw_sha256=sha256_bytes(raw),
                observed_candidate_id=body['candidate_id'], input_candidate_id=view['candidate_id'],
                candidate_matches_current=body['candidate_id']==view['candidate_id'], observation=body['observation']))
        own = [op for selected,op in operations if selected==tag]
        for op in own:
            action,result = op['action'],op['result']
            if not result['accepted']:
                continue
            if action['action'] in ('patch','replace_region'):
                edits.append(dict(id=tag,phase=phase,path=result.get('path',action.get('path')),
                    predecessor=view['candidate_id'],successor=result['candidate_id']))
            if action['action']=='probe':
                scope = 'prefork' if phase=='A' else 'public'
                check = view['verification']['checks'][scope]
                productions.append(dict(id=tag,phase=phase,candidate_id=result['candidate_id'],result=result,
                    consumed_prior_current_pass=bool(check and check['passed'] and check['applies_to_current'])))
            if action['action'] in ('fork_ready','submit'):
                scope = 'prefork' if phase=='A' else 'public'
                check = view['verification']['checks'][scope]
                boundaries.append(dict(id=tag,phase=phase,action=action['action'],candidate_id=view['candidate_id'],
                    actual_receipt=result, consumed_current_active_pass=bool(check and check['passed'] and check['applies_to_current']
                    and check['assessment']['checker_sha256']==sha256_bytes(task.checker(phase)))))
        decisions.append(dict(id=tag,phase=view['phase'],candidate_id=view['candidate_id'],
            actions=[o['action'] for o in own], verification=view['verification'], account=view['working_account'],
            observation_directory=view['observation_directory'],
            source_extents=[{k:v for k,v in r.items() if k!='content'} for r in checkpoint.delivered_sources],
            presentation=view['presentation']))
    forks = [r for r in boundaries if r['action']=='fork_ready']
    submissions = [r for r in boundaries if r['action']=='submit']
    checks = [execute(session.versions[r['candidate_id']], 'original_'+r['phase'], task.checker(r['phase'])) for r in forks]
    checks.append(execute(candidate,'original_D_on_final',task.checker('D')))
    cases = "values=['',' a ',' MiX ',' Straße ',' Åß ','\\tNAME\\n',' İ ',' Σςσ ']\n"
    # These additional examples run in fresh ordinary candidate roots. Fixture
    # constants belong only to this post-run assessment, never actor inputs.
    for boundary in [*forks, dict(phase='D',candidate_id=candidate.candidate_id)]:
        phase = boundary['phase']
        script = 'from workflow.progress import completed_phases\nassert completed_phases()==1\n'+cases
        if phase in ('B','C','D'):
            script += "from codec.label import codec_label\nfor value in values: assert codec_label(value)=='A3::'+value.strip().upper()\n"
        if phase in ('C','D'):
            script += "from codec.header import codec_header\nfor value in values: assert codec_header(value)=='B6::'+value.strip().casefold()\n"
        if phase=='D':
            script += "from codec.footer import codec_footer\nfrom codec.wire import encode_wire\nfor value in values:\n assert codec_footer(value)=='C9::'+value.strip().upper()\n combined=codec_label(value)+'|'+codec_header(value)+'|'+codec_footer(value)\n if combined.isascii(): assert encode_wire(value)==combined.encode('ascii')\n"
        script += "print('independent normalization/preservation examples passed')\n"
        save(folder / ('independent-'+phase+'.py'),script.encode())
        checks.append(execute(session.versions[boundary['candidate_id']], 'independent_'+phase,script.encode()))
    recovery = []
    for phase,target,previous in (('B','codec/label.py','A'),('C','codec/header.py','B'),('D','codec/footer.py','C')):
        prior = next((r for r in forks if r['phase']==previous),None)
        changes = [r for r in edits if r['phase']==phase and r['path']==target]
        valid = [r for r in delivered if prior and r['phase']==phase and r['candidate_matches_current']
            and r['observed_candidate_id']==prior['candidate_id'] and changes and r['id']<=changes[0]['id']
            and r['observation']==task.exact(f'execution_only/{study.CASE}/probes/{previous}.txt').decode()]
        recovery.append(dict(phase=phase,target=target,exact_applicable_recovery_before_first_edit=bool(valid),support=valid))
    coverage = {phase:session.coverage_status(phase) for phase in study.ORDER}
    produced_at_boundaries = all(any(p['phase']==b['phase'] and p['candidate_id']==b['candidate_id']
        and p['id']<b['id'] and p['consumed_prior_current_pass'] for p in productions) for b in forks)
    complete = bool(session.submitted and [r['phase'] for r in forks]==['A','B','C']
        and len(submissions)==1 and submissions[0]['phase']=='D'
        and all(r['consumed_current_active_pass'] for r in boundaries)
        and all(r['complete'] for rows in coverage.values() for r in rows)
        and all(r['exact_applicable_recovery_before_first_edit'] for r in recovery)
        and produced_at_boundaries and all(r['returncode']==0 for r in checks)
        and set(changed)<= {'workflow/progress.py','codec/label.py','codec/header.py','codec/footer.py'})
    result = dict(**identity,candidate_id=candidate.candidate_id,changed_files=changed,
        unchanged_files=len(before)-len(changed),checks=checks,boundaries=boundaries,edits=edits,
        productions=productions,observations_actually_delivered=delivered,recovery=recovery,coverage=coverage,
        decisions=decisions,original_contract_screen_passed=complete,production_order_at_boundaries=produced_at_boundaries,
        environment=dict(interpreter=sys.executable,flags=['-B','-X','utf8'],cwd='fresh phase-candidate root'),
        limits=['Alternative legitimate exact-recovery routes need direct review if this screen fails.',
            'Exact delivery and production are not semantic understanding or account benefit.',
            'Original boundaries deliberately release selection; they are not natural pressure events.',
            'Intermediate checks use actual phase candidates; additional examples are not model trials.'])
    save(folder / 'ASSESSMENT.json',result)
    print(json.dumps(dict(case=task.CASE,original_contract_screen_passed=complete,changed_files=changed,
        checks=checks,recovery=recovery,metrics=metric.aggregate(calls)),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='001')
    assess(parser.parse_args().version)
