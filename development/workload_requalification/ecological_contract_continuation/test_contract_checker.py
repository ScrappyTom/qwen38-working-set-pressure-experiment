"""CPU-only checker qualification on sealed, actual E20 candidates.

Subprocesses run only through the common ObservationStore. No model, GPU,
tokenizer, native decoder, invented source fixture, or actor setup is involved.
Full observations remain in a unique review directory, including failed tests.
"""
import ast
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(AREA))
import contract_checker as checker
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.observations import ObservationStore

OLD = ROOT / 'development/workload_requalification/ecological_import_entry'
RUN_SEAL = '6550a09cdadf7369e6151bcf39ec8baef11c855df08b10bfb5fa022ceaf1182b'
PREPARATION_SEAL = '1bc31cf1c583087f265743d9042c3031ec91dfd5c9210349f8d9ba559cfc4385'
EVALUATION_SEAL = 'b115fbb5dd5a35ca38b9ea222a4a125abecabded6f530d39f7dc4540e7679610'
REFERENCE_EVALUATION_SEAL = '77fb44b323a9d7f7102864208fa68418f63351d74918c19cbc8bb6a29de5f178'


def _sealed_bytes(folder, seal_name, seal_sha, relative):
    raw = (folder / seal_name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != seal_sha:
        raise AssertionError('Sealed evidence identity differs: ' + str(folder))
    seal = json.loads(raw)
    inventory = seal.get('files', seal.get('artifacts'))
    if hashlib.sha256(canonical_json_bytes(inventory)).hexdigest() != seal['aggregate_sha256']:
        raise AssertionError('Sealed inventory differs')
    rows = [row for row in inventory if row['path'] == relative]
    if len(rows) != 1:
        raise AssertionError('Sealed address is absent or ambiguous: ' + relative)
    body = (folder / relative).read_bytes()
    if len(body) != rows[0]['size_bytes'] or hashlib.sha256(body).hexdigest() != rows[0]['sha256']:
        raise AssertionError('Sealed evidence bytes differ: ' + relative)
    return body


def _candidate(raw):
    value = json.loads(raw)
    files = {}
    for row in value['files']:
        data = row['content_utf8'].encode('utf-8')
        if len(data) != row['size_bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise AssertionError('Candidate file bytes differ')
        if row['path'] in files:
            raise AssertionError('Duplicate candidate path')
        files[row['path']] = data
    candidate = Candidate.create(files, max_file_bytes=value['max_file_bytes'])
    if candidate.candidate_id != value['candidate_id']:
        raise AssertionError('Candidate identity differs')
    return candidate


class ContractCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = OLD / 'run-001'
        cls.final = _candidate(_sealed_bytes(run, 'RESPONSE_SEAL.json', RUN_SEAL,
                                            'final-candidate.json'))
        state = json.loads(_sealed_bytes(run, 'RESPONSE_SEAL.json', RUN_SEAL, 'final-state.json'))
        assert state['submitted'] and state['candidate_id'] == cls.final.candidate_id
        assert (state['requests_used'], len(state['pairs'])) == (19, 28)
        prep = OLD / 'preparation-001'
        seal = json.loads((prep / 'SEAL.json').read_bytes())
        assert seal['status'] == 'qualified_no_model_inference' and seal['completion_requests'] == 0
        stem = 'scripted/import_boundaries/steps/13-'
        cls.reference = _candidate(_sealed_bytes(prep, 'SEAL.json', PREPARATION_SEAL, stem + 'candidate.json'))
        reference_state = json.loads(_sealed_bytes(prep, 'SEAL.json', PREPARATION_SEAL, stem + 'state.json'))
        assert reference_state['submitted'] and reference_state['candidate_id'] == cls.reference.candidate_id
        cls.output = AREA / 'review' / ('checker-cpu-observations-' + str(time.time_ns()))
        cls.output.mkdir(parents=True, exist_ok=False)
        (cls.output / 'SOURCE.json').write_bytes(canonical_json_bytes({
            'checker_source_sha256': hashlib.sha256(Path(checker.__file__).read_bytes()).hexdigest(),
            'test_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'checker_sha256': checker.checker_sha256(), 'original_run_seal_sha256': RUN_SEAL,
            'original_preparation_seal_sha256': PREPARATION_SEAL,
            'final_candidate_id': cls.final.candidate_id, 'reference_candidate_id': cls.reference.candidate_id,
            'classification': 'CPU checker qualification only; no actor/model/native execution'}))
        print('Preserved CPU checker observations: ' + str(cls.output), flush=True)

    def test_exact_constituent_bytes_and_changed_checker_identity(self):
        body = checker.public_checker()
        tree = ast.parse(body.decode('utf-8'))
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'PROGRAMS' for target in node.targets))
        programs = dict(ast.literal_eval(assignment.value))
        self.assertEqual(programs, checker.constituent_programs())
        self.assertEqual(hashlib.sha256(programs['original_public']).hexdigest(), checker.ORIGINAL_PUBLIC_SHA)
        self.assertEqual(hashlib.sha256(programs['boundary_probe']).hexdigest(), checker.PROBE_SHA)
        self.assertNotEqual(checker.checker_sha256(), checker.ORIGINAL_PUBLIC_SHA)
        self.assertEqual(checker.contracts()['public']['checker_sha256'], hashlib.sha256(body).hexdigest())
        with tempfile.TemporaryDirectory() as raw:
            changed = Path(raw) / 'probe.py'
            changed.write_bytes(programs['boundary_probe'] + b'\n# changed\n')
            with patch.object(checker, 'PROBE', changed), self.assertRaisesRegex(ValueError, 'bytes changed'):
                checker.public_checker()

    def _execute(self, label, candidate, expected_cases):
        store = ObservationStore(self.output / label)
        record = store.execute(candidate, checker.public_checker(), 'public', 'CHK-0001')
        rows = [json.loads(line) for line in (store.directory('CHK-0001') / 'stdout.bin').read_bytes().splitlines()]
        executions, cases, summary = rows[:2], rows[2:-1], rows[-1]
        self.assertEqual(len(rows), 15)
        self.assertEqual(len(cases), 12)
        self.assertTrue(record['capture_complete'])
        self.assertEqual(record['checker_sha256'], checker.checker_sha256())
        for index, scope in enumerate(('original_public', 'boundary_probe')):
            observation = executions[index]
            self.assertEqual(observation['observed_scope'], scope)
            self.assertEqual(observation['criterion_kind'], 'execution')
            self.assertTrue(observation['executed'] and observation['complete'])
            self.assertEqual(observation['program_sha256'],
                             hashlib.sha256(checker.constituent_programs()[scope]).hexdigest())
            for name in ('stdout', 'stderr'):
                stream = observation[name]
                raw = base64.b64decode(stream['content'], validate=True)
                self.assertEqual(stream['encoding'], 'base64')
                self.assertEqual(stream['size_bytes'], len(raw))
                self.assertEqual(stream['sha256'], hashlib.sha256(raw).hexdigest())
        observed = [{key: row[key] for key in ('max_files', 'max_file_bytes', 'expected', 'actual', 'passed')}
                    for row in cases]
        self.assertEqual(observed, expected_cases)
        self.assertEqual(json.loads(base64.b64decode(executions[1]['stdout']['content'])), expected_cases)
        self.assertEqual(summary['failed_cases'], [row['case'] for row in rows[:-1] if not row['passed']])
        self.assertEqual(summary['passed'], all(row['passed'] for row in executions))
        self.assertEqual(summary['probe_cases_failed'], sum(not row['passed'] for row in expected_cases))
        self.assertEqual(record['passed'], summary['passed'])
        value = checker.assessment(store, 'CHK-0001', checker.contracts()['public'])
        (self.output / (label + '-assessment.json')).write_bytes(canonical_json_bytes(value))
        self.assertEqual(value['probe_cases_observed'], 12)
        self.assertEqual(value['probe_cases_failed'], summary['probe_cases_failed'])
        self.assertEqual(len(value['criteria']), 14)
        return store, executions, value

    def test_actual_submitted_candidate_failures_are_delivered_before_execution_status(self):
        old = OLD / 'review/evaluation-001'
        expected_cases = json.loads(_sealed_bytes(old, 'SEAL.json', EVALUATION_SEAL,
            'boundary-observations/CHK-0001/stdout.bin'))
        store, executions, value = self._execute('actual-submitted', self.final, expected_cases)
        self.assertTrue(executions[0]['passed'])
        self.assertFalse(executions[1]['passed'])
        self.assertEqual((value['probe_cases_passed'], value['probe_cases_failed']), (9, 3))
        view = checker.overview(value)
        self.assertEqual(view['failed_records_total'], 4)
        self.assertEqual(view['failed_records_shown'], 2)
        for row in view['criteria']:
            self.assertEqual(row['observation']['criterion_kind'], 'behavioral_case')
            self.assertEqual(row['observation']['max_files'], 0)
            self.assertEqual(row['observation']['expected'], [])
            self.assertEqual(row['observation']['actual'], [{'path': 'a.txt'}])
        page = checker.inspect_check(store, 'CHK-0001', 0, checker.contracts()['public'])
        self.assertEqual(len(page['entries']), 4)
        self.assertEqual([row['observation']['criterion_kind'] for row in page['entries']],
                         ['behavioral_case'] * 3 + ['execution'])
        self.assertEqual(page['total_records'], 14)
        self.assertEqual(page['next_offset'], 4)

    def test_actual_qualified_reference_has_full_scope_pass(self):
        old = OLD / 'review/reference-evaluation-001'
        expected_cases = json.loads(_sealed_bytes(old, 'SEAL.json', REFERENCE_EVALUATION_SEAL,
            'boundary-observations/CHK-0001/stdout.bin'))
        _, executions, value = self._execute('qualified-reference', self.reference, expected_cases)
        self.assertTrue(all(row['passed'] for row in executions))
        self.assertEqual((value['probe_cases_passed'], value['probe_cases_failed']), (12, 0))
        self.assertTrue(value['passed'])
        self.assertEqual(checker.overview(value)['criteria'], [])
        self.assertEqual(value['failed_criteria'], [])

    def test_historical_original_check_keeps_its_original_scope(self):
        old = ObservationStore(OLD / 'run-001/observations', replay=True)
        value = checker.assessment(old, 'CHK-0027', None)
        self.assertEqual(value['checker_sha256'], checker.ORIGINAL_PUBLIC_SHA)
        self.assertTrue(value['passed'])
        self.assertNotIn('registered_scope', value)
        self.assertNotIn('probe_cases_observed', value)


if __name__ == '__main__':
    unittest.main()
