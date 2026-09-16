"""Reuse exact replay; no model inference or checker execution."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_task as study
import verify_reference as verifier

verifier.study = study
result = verifier.verify(study.AREA/'run-001')
study.save(study.AREA/'review', 'VERIFICATION.json', result)
print(json.dumps(result, indent=2))
