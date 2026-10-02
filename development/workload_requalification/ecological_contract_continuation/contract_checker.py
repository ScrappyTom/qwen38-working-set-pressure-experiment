"""Declared E20 contract check over two unchanged constituent programs.

Each subprocess observation is emitted in exact byte encoding before derived
case rows. The common ObservationStore preserves this output before this module's
task-local assessment constructs the ordinary bounded view.
"""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL_PUBLIC = ROOT / ('experiments/020_owner_controlled_ecological_pilot_v2/'
    'fresh_bank/execution_only/E20-SOURCE-IMPORT-BOUNDARIES/public.py')
PROBE = ROOT / 'maintenance/resume_after_020/import_boundary_probe.py'
ORIGINAL_PUBLIC_SHA = 'e9a407cd0d0ddbafc7267dcf34fabb689afde8fc0bc49f8077a85e4d5fe59d59'
PROBE_SHA = 'b5a2ac3f21015dd15212a7fda5c99329cac3199a736d491e9d2c02be54a7c8b6'
SCOPE = 'original_E20_public_and_existing_12_case_import_boundary_probe'


def _exact(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Constituent checker bytes changed: ' + path.name)
    return raw


def constituent_programs():
    return {'original_public': _exact(ORIGINAL_PUBLIC, ORIGINAL_PUBLIC_SHA),
            'boundary_probe': _exact(PROBE, PROBE_SHA)}


# This is execution/reporting code only. It contains no repair, source location,
# evaluator candidate, or independent expected artifact list.
PROGRAM = r'''import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROGRAMS = @PROGRAMS@
REGISTERED_SCOPE = @SCOPE@

def emit(value):
    print(json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True), flush=True)

def exact_stream(raw):
    return dict(encoding='base64', content=base64.b64encode(raw).decode('ascii'),
                size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def run_subcheck(scope, body, folder):
    path = folder / (scope + '.py')
    path.write_bytes(body)
    record = dict(case=scope + '.execution', criterion_kind='execution',
        observed_scope=scope, registered_scope=REGISTERED_SCOPE,
        program_sha256=hashlib.sha256(body).hexdigest(), executed=False,
        complete=False, returncode=None)
    stdout = stderr = b''
    try:
        result = subprocess.run([sys.executable, '-I', '-S', str(path)],
            cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        stdout, stderr = result.stdout, result.stderr
        record.update(executed=True, complete=True, returncode=result.returncode,
                      termination='completed')
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b'', error.stderr or b''
        record.update(executed=True, termination='timeout')
    except OSError as error:
        record.update(termination='not_started', adapter_error=str(error))
    record.update(stdout=exact_stream(stdout), stderr=exact_stream(stderr),
                  passed=record['complete'] and record['returncode'] == 0)
    # Exact output is already in the parent's preserved stream before any
    # interpretation of the probe JSON, including when later derivation fails.
    emit(record)
    return record, stdout

execution_rows = []
with tempfile.TemporaryDirectory(prefix='e20-contract-subchecks-') as raw:
    folder = Path(raw)
    for scope, body in PROGRAMS:
        record, stdout = run_subcheck(scope, body, folder)
        execution_rows.append(record)
        if scope == 'boundary_probe':
            probe_stdout = stdout

case_rows = []
case_error = None
try:
    observed = json.loads(probe_stdout.decode('utf-8'))
    keys = {'max_files', 'max_file_bytes', 'expected', 'actual', 'passed'}
    if (not isinstance(observed, list) or len(observed) != 12
            or any(not isinstance(row, dict) or set(row) != keys
                or type(row['max_files']) is not int or type(row['max_file_bytes']) is not int
                or type(row['passed']) is not bool
                or not isinstance(row['expected'], list) or not isinstance(row['actual'], list)
                or row['passed'] != (row['actual'] == row['expected']) for row in observed)
            or len({(row['max_files'], row['max_file_bytes']) for row in observed}) != 12):
        raise ValueError('The preserved probe output is not its complete twelve-case report')
    for row in observed:
        item = dict(row, case='boundary_probe.max_files_%d.max_file_bytes_%d' % (
            row['max_files'], row['max_file_bytes']), criterion_kind='behavioral_case',
            observed_scope='boundary_probe', registered_scope=REGISTERED_SCOPE,
            program_sha256=hashlib.sha256(dict(PROGRAMS)['boundary_probe']).hexdigest())
        case_rows.append(item)
        emit(item)
except (UnicodeError, ValueError, TypeError) as error:
    case_error = str(error)

rows = execution_rows + case_rows
passed = all(row['passed'] for row in execution_rows)
summary = dict(registered_scope=REGISTERED_SCOPE,
    failed_cases=[row['case'] for row in rows if not row['passed']], passed=passed,
    constituent_program_sha256={name: hashlib.sha256(body).hexdigest() for name, body in PROGRAMS},
    probe_cases_available=len(case_rows) == 12,
    probe_cases_observed=len(case_rows),
    probe_cases_passed=sum(row['passed'] for row in case_rows),
    probe_cases_failed=sum(not row['passed'] for row in case_rows),
    probe_case_report_error=case_error,
    acceptance='Both unchanged constituent programs completed and exited with status zero; case extraction adds no acceptance predicate.')
emit(summary)
sys.exit(0 if passed else 1)
'''


def public_checker():
    programs = constituent_programs()
    pairs = [(name, programs[name]) for name in ('original_public', 'boundary_probe')]
    return PROGRAM.replace('@PROGRAMS@', repr(pairs)).replace('@SCOPE@', repr(SCOPE)).encode('utf-8')


def checker_sha256():
    return hashlib.sha256(public_checker()).hexdigest()


def contracts():
    return {'public': {'checker_sha256': checker_sha256(), 'registered_scope': SCOPE,
        'constituent_program_sha256': {'original_public': ORIGINAL_PUBLIC_SHA, 'boundary_probe': PROBE_SHA}}}


def _reports():
    path = ROOT / 'development/workload_requalification/small_repairs/case_reports.py'
    spec = importlib.util.spec_from_file_location('e20_contract_original_case_reports', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assessment(store, handle, contract=None):
    core = _reports()
    value = core.assessment(store, handle, contract)
    # Historical original checks keep the original report and identity. A new
    # assessment must not relabel the old passing observation as a combined pass.
    if not contract or contract.get('registered_scope') != SCOPE:
        return value
    executions, cases = [], []
    for row in value['criteria']:
        observed = row.get('observation', {})
        if observed.get('criterion_kind') == 'behavioral_case':
            row['meaning'] = 'Actual case emitted by the unchanged import-boundary probe.'
            cases.append(observed)
        elif observed.get('criterion_kind') == 'execution':
            row['meaning'] = 'Actual constituent execution status; its case rows identify behavioral disagreements.'
            executions.append({key: observed[key] for key in ('observed_scope',
                'program_sha256', 'executed', 'complete', 'termination', 'returncode', 'passed')})
    value['criteria'].sort(key=lambda row: (row['met'] is not False,
        row.get('observation', {}).get('criterion_kind') != 'behavioral_case'))
    value['failed_criteria'] = [row['criterion'] for row in value['criteria'] if row['met'] is False]
    value.update(registered_scope=SCOPE, constituent_executions=executions,
        probe_cases_observed=len(cases), probe_cases_passed=sum(row['passed'] for row in cases),
        probe_cases_failed=sum(not row['passed'] for row in cases),
        probe_case_records_available=len(cases) == 12,
        explanation=('Both unchanged constituent programs must complete and exit successfully. '
            'A failed probe-execution criterion and its failed behavioral rows are distinct records of the same execution; '
            'probe_cases_failed counts only the twelve behavioral cases. No injected faults or negative-count requirement.'))
    return value


def overview(value):
    return _reports().overview(value)


def inspect_check(store, handle, offset, contract=None):
    value = assessment(store, handle, contract)
    rows = value.pop('criteria')
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError('assessment offset is outside complete records')
    page = rows[offset:offset + 4]
    return dict(accepted=True, kind='check_criteria', **value, entries=page,
        offset=offset, total_records=len(rows),
        next_offset=offset + len(page) if offset + len(page) < len(rows) else None,
        records_complete=True, all_records_shown=offset == 0 and len(page) == len(rows))
