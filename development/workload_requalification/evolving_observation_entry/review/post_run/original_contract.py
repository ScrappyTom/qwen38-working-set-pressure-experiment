"""Supplement the frozen overstrict ledger-order metric; do not replace it."""
import json
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AREA))
import observation_task as study
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def evaluate():
    review = AREA / 'review'
    audit = study.read(review / 'TEMPORAL-AUDIT-001.json')
    verification = study.read(review / 'VERIFICATION-001.json')
    artifact = study.read(review / 'ARTIFACT-ASSESSMENT-001.json')
    assert verification['status'] == 'replayed_exactly'
    assert audit['response_seal_sha256'] == verification['response_seal_sha256'] == artifact['response_seal_sha256']
    task = study.task_text()
    assert 'Read every listed required ledger completely. Read exact current source before mutation.' in task
    submission = [row for row in audit['decisions'] if any(
        effect['action'] == 'submit' and effect['accepted'] for effect in row['effects'])]
    ledgers_by_submit = len(submission) == 1 and submission[0]['all_ledgers_delivered']
    criteria = dict(
        complete_required_ledger_delivery_by_submission=bool(ledgers_by_submit),
        marker_acquired_before_mutations=bool(audit['edits']) and all(
            row['bound_marker_previously_delivered'] for row in audit['edits']),
        label_before_footer=audit['label_before_footer'],
        exact_marker_capture_available_at_footer=audit['exact_marker_available_at_footer'],
        consumed_current_public_pass=audit['submitted_from_current_pass'],
        ordinary_artifact_behavior_passed=artifact['ordinary_behavior_passed'],
        other_files_preserved=artifact['only_target_files_changed'] and artifact['unchanged_other_files']==128)
    return dict(status='separate_original_contract_assessment',
        response_seal_sha256=audit['response_seal_sha256'],
        task_sha256=study.TASK_SHA, original_task_unchanged=True,
        evaluator_source_sha256=sha256_file(Path(__file__)),
        frozen_temporal_audit_sha256=sha256_file(review / 'TEMPORAL-AUDIT-001.json'),
        frozen_temporal_contract_met=audit['temporal_contract_met'],
        frozen_before_every_mutation_predicate=audit['mutation_prerequisites_supported'],
        frozen_metric_preserved=True, criteria=criteria,
        original_contract_supported=all(criteria.values()),
        reason_for_supplement='The original task requires complete ledger delivery and exact target source before mutation; it does not explicitly require all unrelated ledgers before every edit. Original E18 specification measures ledger completion; the original patch operation has no required-ledger prerequisite.',
        reference_sources={str(p.relative_to(study.ROOT)):sha256_file(p) for p in [
            study.ROOT/'experiments/018_large_world_event_frame_v2/SPEC.md',
            study.ROOT/'src/working_set_exp/large_world_event_v2.py',
            study.ROOT/'src/working_set_exp/tools.py']},
        limits=['The frozen evaluator/specification remains unchanged and its result is reported, not erased.',
            'This supplementary criterion was recorded after observing C04; it is not a prospectively matched experiment.',
            'No live prompt, action, reasoning policy, opportunity or host behavior changed.',
            'Exact source eligibility is checked by the independently replayed host; delivery is not semantic understanding.',
            'The capture predicate is sufficient for the conditional requirement. A different exact recovered action/result route would require direct separate assessment, not automatic failure from this predicate alone.'])


if __name__ == '__main__':
    value = evaluate()
    path = AREA/'review/ORIGINAL-CONTRACT-001.json'
    raw = canonical_json_bytes(value)
    if path.exists():
        assert path.read_bytes()==raw
    else:
        path.write_bytes(raw)
    print(json.dumps(value, indent=2))
