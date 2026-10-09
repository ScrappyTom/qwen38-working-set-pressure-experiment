"""Post-seal correction: validate qualification envelope before domain comparison.

The original verifier and failed result remain unchanged. QualificationLog adds
two true transport facts that RunLog does not add. Check them explicitly, then
reuse the exact imported-body and semantic-payload comparison. Hash-chain and
inventory checks still operate on the original unmodified records.
"""
import argparse
import json
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import verify_preparation as original
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file

DOMAIN_CHECK=original.verify_run._imported_custody


def qualified_imports(module,root,records,prefixes):
    comparison=[]
    for record in records:
        if record['record_type']=='imported_capture_custody':
            payload=dict(record['payload'])
            assert payload.pop('qualification_only') is True
            assert payload.pop('completion_sent') is False
            comparison.append({**record,'payload':payload})
        else:
            comparison.append(record)
    return DOMAIN_CHECK(module,root,comparison,prefixes)


def verify(case,version):
    with patch.object(original.verify_run,'_imported_custody',qualified_imports):
        result=original.verify(case,version)
    result.update(post_seal_verifier_correction='validate_qualification_envelope_before_domain_payload',
        supplemental_verifier_sha256=sha256_file(Path(__file__)),
        unchanged_domain_verifier_sha256=sha256_file(Path(original.verify_run.__file__)))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',required=True,choices=tuple(original.study.CASES))
    parser.add_argument('--version',default='001')
    args=parser.parse_args()
    output=HERE.parent/f'PREPARATION-VERIFICATION-{args.case}-{args.version}-SUPPLEMENT.json'
    try:
        value=verify(args.case,args.version)
    except BaseException as error:
        failure=output.with_name(output.stem+'-FAILED.json')
        raw=canonical_json_bytes(dict(status='failed',type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        if failure.exists(): assert failure.read_bytes()==raw
        else: failure.write_bytes(raw)
        raise
    raw=canonical_json_bytes(value)
    if output.exists(): assert output.read_bytes()==raw
    else: output.write_bytes(raw)
    print(json.dumps(value,indent=2))
