"""Read sealed source/delivery/cost records; direct review remains separate."""
import importlib.util
from pathlib import Path

area = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'reference_assessor', area.parent / 'reference_repair/review/assess_run.py')
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)
auditor.AREA, auditor.RUN = area, area / 'run-001'
auditor.main()
