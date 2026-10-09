"""Post-run public-boundary faults, independent of actor implementation layout."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unnamed_task as task
import unnamed_material as material
import unnamed_cpu as checks
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


FAULTS = {
    'header_before_unnamed_output': r'''

# Evaluator-only fault, appended to an isolated copy; never saved to actor work.
import io as _fault_io
_original_writers = [(cls, cls.write) for cls in (RawConfigParser, ConfigParser)]
for _fault_cls, _fault_original in _original_writers:
    def _fault_write(self, fp, space_around_delimiters=True, _original=_fault_original):
        target = _fault_io.StringIO()
        _original(self, target, space_around_delimiters=space_around_delimiters)
        text = target.getvalue()
        if text and not text.lstrip().startswith('['):
            text = '[injected_header]\n' + text
        fp.write(text)
    _fault_cls.write = _fault_write
''',
    'sentinel_dictionary_key_stringified': r'''

# Evaluator-only fault at the public dictionary-input boundary.
_original_readers = [(cls, cls.read_dict) for cls in (RawConfigParser, ConfigParser)]
for _fault_cls, _fault_original in _original_readers:
    def _fault_read_dict(self, dictionary, source='<dict>', _original=_fault_original):
        if UNNAMED_SECTION in dictionary:
            dictionary = {str(key) if key is UNNAMED_SECTION else key: value
                          for key, value in dictionary.items()}
        return _original(self, dictionary, source=source)
    _fault_cls.read_dict = _fault_read_dict
''',
}


def main():
    area = material.AREA
    verification = task.read(area/'review/VERIFICATION-001.json')
    assert verification['status'] == 'replayed_exactly'
    value = task.read(area/'run-001/final-candidate.json')
    assert value['candidate_id'] == verification['final_candidate_id']
    files = {row['path']: row['content_utf8'].encode() for row in value['files']}
    folder = area/'review/001/sensitivity'
    folder.mkdir(exist_ok=False)
    rows = {}
    for name, suffix in [('control', ''), *FAULTS.items()]:
        modified = {**files, material.LIBRARY: files[material.LIBRARY]+suffix.encode()}
        result = checks.run(modified)
        (folder/f'{name}-execution.json').write_bytes(canonical_json_bytes(result))
        report = json.loads(result['stdout'])
        rows[name] = {k: report[k] for k in ('passed', 'upstream', 'contract', 'candidate_tests')}
        if name == 'control':
            assert result['returncode'] == 0 and report['passed']
    result = dict(candidate_id=value['candidate_id'], evaluator_only=True,
        returned_to_actor=False, model_requests=0, script_sha256=sha256_file(Path(__file__)),
        faults={name: suffix for name, suffix in FAULTS.items()}, results=rows,
        authored_tests_detected={name: not row['candidate_tests']['successful']
                                for name, row in rows.items() if name != 'control'})
    (folder/'RESULTS.json').write_bytes(canonical_json_bytes(result))
    print(result['authored_tests_detected'])


if __name__ == '__main__':
    main()
