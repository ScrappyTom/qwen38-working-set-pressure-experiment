"""Ordinary standalone execution of the engineering addition; not actor work."""
import contextlib
import doctest
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import correction_task as entry
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.observations import ObservationStore

task = entry.Task()
source = entry.original.read(task.PACKAGE/'route/08-candidate.json')
candidate = entry.original.candidate_from_snapshot(source)
old = task.inherited_candidate.file_map[entry.DOC]
new = candidate.file_map[entry.DOC]
assert new.startswith(old)
addition = new[len(old):].decode()
results = []
checks = Path(__file__).parent/'ordinary-example-checks-001'
checks.mkdir(exist_ok=False)
with tempfile.TemporaryDirectory() as raw:
    folder = Path(raw)
    library = folder/'configparser.py'; library.write_bytes(candidate.file_map['Lib/configparser.py'])
    spec = importlib.util.spec_from_file_location('configparser', library)
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get('configparser'); sys.modules['configparser'] = module
    try:
        spec.loader.exec_module(module)
        for name, text, failed in (('actual', addition, False),
                ('deliberate_output_failure', addition.replace("   'supplied'\n", "   'not the observed result'\n", 1), True)):
            # This negative changes one expected output only. Verify it really
            # differs and fails rather than assuming a phrase exists.
            if failed and text == addition:
                raise ValueError('engineering negative did not change an example')
            document = folder/(name+'.txt'); document.write_text(text, encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                observed = doctest.testfile(str(document), module_relative=False, verbose=False)
            assert bool(observed.failed) == failed
            files = candidate.file_map
            files[entry.DOC] = old+text.encode()
            subject = Candidate.create(files, max_file_bytes=candidate.max_file_bytes)
            dest = checks/name; dest.mkdir()
            (dest/'candidate.json').write_bytes(task.candidate_bytes(subject))
            captured = ObservationStore(dest/'capture', timeout=120)
            receipt = captured.execute(subject, task.checker('examples'), 'examples', 'CHK-0001')
            report = json.loads((captured.directory('CHK-0001')/'stdout.bin').read_bytes())
            assert receipt['executed'] and receipt['capture_complete'] and receipt['passed'] == (not failed)
            assert observed.failed == report['examples']['failures']
            assert observed.attempted == report['examples']['examples']
            assert report['examples']['environment']['__name__'] == '__main__'
            results.append(dict(case=name, examples=observed.attempted, failures=observed.failed,
                                registered_passed=receipt['passed'], output=output.getvalue()))
    finally:
        if previous is None: sys.modules.pop('configparser', None)
        else: sys.modules['configparser'] = previous
(Path(__file__).parent/'ORDINARY_EXAMPLES.json').write_bytes(canonical_json_bytes(dict(
    classification='Reviewer engineering examples; no model contribution', results=results)))
print(results)
