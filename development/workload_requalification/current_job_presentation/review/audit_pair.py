"""Post-seal exact replay plus artifact/ordinary-example verification."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import overlap_task as entry
study=entry.study
sys.path.insert(0,str(study.AREA/'review'))
from verify_dispatch import verify
from working_set_exp.jsonutil import load_json_strict,sha256_bytes


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('condition',choices=('control','current_job'))
    parser.add_argument('--version',default='002')
    args=parser.parse_args()
    task=entry.Task(args.condition,args.version)
    output=entry.HERE/'review'/f'{args.condition}-{args.version}'
    assert not output.exists(),'Audit exists; preserve the first result.'
    verify(task,output)
    seal=study.read(task.RUN/'RESPONSE_SEAL.json')
    stem='stopped' if seal['disposition']=='stopped_without_retry' else 'final'
    candidate=study.candidate_from_snapshot(study.read(task.RUN/f'{stem}-candidate.json'))
    state=study.read(task.RUN/f'{stem}-state.json')
    protected={p:candidate.file_map[p]==raw for p,raw in task.inherited_candidate.file_map.items()
               if p not in (entry.DOC,entry.TEST)}
    assert len(protected)==6 and all(protected.values())
    original_doc=task.inherited_candidate.file_map[entry.DOC]
    original_tests=task.inherited_candidate.file_map[entry.TEST]
    prefix,suffix=original_tests.split(b'\n\nif __name__ == "__main__":',1)
    doc_preserved=candidate.file_map[entry.DOC].startswith(original_doc)
    tests_preserved=candidate.file_map[entry.TEST].startswith(prefix) and candidate.file_map[entry.TEST].endswith(b'\n\nif __name__ == "__main__":'+suffix)
    store=entry.ObservationStore(output/'postseal-check',timeout=60)
    observation=store.execute(candidate,entry.checker(task.inherited_candidate),'public','CHK-0001')
    rows=[load_json_strict(line) for line in (store.directory('CHK-0001')/'stdout.bin').read_bytes().splitlines()]
    summary=dict(condition=args.condition,disposition=seal['disposition'],
        candidate_id=candidate.candidate_id,protected_files_exact=protected,
        previous_document_prefix_exact=doc_preserved,previous_tests_preserved=tests_preserved,
        changed_files=[p for p,raw in candidate.file_map.items() if task.inherited_candidate.file_map[p]!=raw],
        file_sha256={p:sha256_bytes(raw) for p,raw in candidate.file_map.items()},
        postseal_public_pass=observation['passed'],checker_records=rows,
        repeated_checker_is_not_new_coverage=True,prose_and_authored_coverage_require_direct_review=True,
        final_account=task.restore(state,candidate,task.RUN,replay=True).working_account())
    study.save(output,'ARTIFACT_AUDIT.json',summary)
    study.save(output,'saved-union-dispatch.rst',candidate.file_map[entry.DOC])
    study.save(output,'saved-test_virtual_registration.py',candidate.file_map[entry.TEST])
    print({k:summary[k] for k in ('condition','disposition','candidate_id','changed_files','postseal_public_pass')})


if __name__=='__main__':main()
