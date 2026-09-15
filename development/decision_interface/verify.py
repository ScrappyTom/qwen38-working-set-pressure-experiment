"""Exact offline replay of decision inputs, literal replies, saved work and checks."""
import argparse
import json

import decision_task as study
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def verify(folder):
    seal=study.read(folder/'SEAL.json')
    assert sha256_bytes(canonical_json_bytes(seal['files']))==seal['aggregate_sha256']
    for row in seal['files']:
        p=folder/row['path']
        assert p.stat().st_size==row['size_bytes'] and sha256_file(p)==row['sha256'],row['path']
    study.verify_sources(seal['source_sha256'])
    for name,digest in seal.get('private_runtime_files_local_only',{}).items():
        assert sha256_file(folder/'private-runtime'/name)==digest
    records=verify_records(folder/'records.jsonl',folder)
    assert all(not r['payload'].get('completion_sent') for r in records)
    adapter=runner.Adapter(study.Task())
    counts={}
    for r in records:
        if r['record_type']!='native_input_prepared':
            continue
        row=r['payload'];stem=row['stem']
        request=study.read(folder/(stem+'-endpoint-request.json'))
        native=(folder/(stem+'-native.txt')).read_bytes()
        assert native==adapter.expected_native(request)==study.read(folder/(stem+'-template.json'))['prompt'].encode()
        assert row['prompt_tokens']==len(study.read(folder/(stem+'-tokens.json'))['tokens'])
        assert (folder/(stem+'-wire-request.json')).read_bytes()==completion_request_bytes(request)
        counts[sha256_bytes(canonical_json_bytes(request))]=row['prompt_tokens']
    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    session=study.from_checkpoint()
    session.observations=ObservationStore(folder/'observations',replay=True)
    assert canonical_json_bytes(study.snapshot(session))==(folder/'starting-state.json').read_bytes()
    completed=0
    for record in records:
        if record['record_type']!='invocation_started':
            continue
        tag=record['payload']['id']
        assert (folder/f'calls/{tag}-wire-request.json').read_bytes()==completion_request_bytes(adapter.request_for(session.view()))
        assert measure(session.view())==record['payload']['prompt_tokens']
        session.mark_delivered(session.view());session.begin_request()
        choice=study.read(folder/f'calls/{tag}-endpoint-response.json')['choices'][0]
        assert choice['finish_reason']=='stop'
        for field,suffix in (('content','content'),('reasoning_content','reasoning')):
            assert (choice['message'].get(field) or '').encode()==(folder/f'calls/{tag}-assistant-{suffix}.txt').read_bytes()
        reply=study.decode_reply(choice['message']['content'])
        assert reply==study.read(folder/f'calls/{tag}-reply.json')
        def intermediate(number,operation):
            assert operation==study.read(folder/f'calls/{tag}-operation-{number:02d}.json')
            stem=f'after/{tag}-O{number:02d}'
            assert canonical_json_bytes(study.snapshot(session))==(folder/(stem+'-state.json')).read_bytes()
            assert study.candidate_bytes(session.candidate)==(folder/(stem+'-candidate.json')).read_bytes()
        result=adapter.process_reply(session,reply,measure,adapter.preceding_feedback,intermediate)
        assert result==study.read(folder/f'calls/{tag}-host-result.json')
        completed+=1
    assert canonical_json_bytes(study.snapshot(session))==(folder/'final-state.json').read_bytes()
    assert study.candidate_bytes(session.candidate)==(folder/'final-candidate.json').read_bytes()
    observations=[r for r in records if r['record_type']=='check_observation_preserved']
    for r in observations:
        saved=session.observations.read(r['payload']['observation'])
        assert {k:r['payload'][k] for k in saved}==saved
    closed=[r['payload'] for r in records if r['record_type']=='runtime_closed']
    assert len(closed)==1 and closed[0]['owned_server_shutdown_verified'] and closed[0]['dedicated_port_free']
    return dict(status='replayed_exactly',scripted_replies=completed,actual_operations=session.calls_used,
        native_inputs=len(counts),custody_records=len(records),submitted=session.submitted,
        source_files=len(seal['source_sha256']),observations_replayed_without_execution=len(observations),
        private_runtime_files_verified=len(seal.get('private_runtime_files_local_only',{})),
        no_additional_model_inference=True,owned_runtime_closed=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',default='qualification-003')
    folder=study.AREA/p.parse_args().folder
    result=verify(folder)
    study.save(study.AREA,folder.name+'-VERIFICATION.json',result)
    print(json.dumps(result,indent=2))
