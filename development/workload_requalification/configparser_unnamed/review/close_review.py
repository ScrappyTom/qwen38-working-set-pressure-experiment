"""CPU-only accounting and explicitly partial export after the owner's stop."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / 'run-001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(raw, bytes):
        raw = (json.dumps(raw, indent=2, sort_keys=True) + '\n').encode()
    if path.exists():
        assert path.read_bytes() == raw, 'Preserve differing reviewer outputs'
    else:
        path.write_bytes(raw)


def main():
    proof = read(HERE / 'VERIFICATION-001.json')
    assert proof['status'] == 'replayed_exactly' and not proof['submitted']
    seal = read(RUN / 'RESPONSE_SEAL.json')
    assert seal['port_free'] and seal['returned_responses'] == 17
    saved = read(RUN / 'stopped-candidate.json')
    initial = read(RUN / 'starting-candidate.json')
    assert saved['candidate_id'] == proof['final_candidate_id']
    before = {row['path']: row['content_utf8'].encode() for row in initial['files']}
    folder = (HERE / '001/partial-work').resolve()
    exported = []
    for row in saved['files']:
        target = (folder / row['path']).resolve()
        assert target.is_relative_to(folder)
        raw = row['content_utf8'].encode()
        save(target, raw)
        exported.append(dict(path=row['path'], bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(), changed=raw != before[row['path']]))
    records = [json.loads(line) for line in (RUN / 'records.jsonl').read_text().splitlines()]
    by_type = lambda kind: [row for row in records if row['record_type'] == kind]
    time = lambda row: datetime.fromisoformat(row['created_at_utc'])
    start, closed = by_type('attempt_reserved')[0], by_type('runtime_closed')[0]
    interrupted = by_type('transport_stopped')[0]
    last_start = by_type('invocation_started')[-1]
    assert last_start['payload']['id'] == interrupted['payload']['id'] == 'C18'
    wires = [read(RUN / f'calls/C{number:02}-wire-request.json') for number in range(1, 19)]
    assert all(wire['chat_template_kwargs'] == dict(enable_thinking=True, reasoning_effort='medium')
               and wire['seed'] == 314159 and wire['max_tokens'] == -1 for wire in wires)
    log = RUN / 'private-runtime/server.stderr.log'
    text = log.read_text(encoding='utf-8', errors='strict')
    generation_lines = [line for line in text.splitlines() if 'n_gen =' in line]
    last_generation = generation_lines[-1]
    token_lower_bound = int(re.search(r'n_gen =\s*(\d+)', last_generation).group(1))
    processes = subprocess.run(['powershell', '-NoProfile', '-Command',
        "@(Get-CimInstance Win32_Process -Filter 'ProcessId = 15072 OR ProcessId = 31392') | "
        'Select-Object ProcessId,Name | ConvertTo-Json -Compress'],
        capture_output=True, text=True, check=True)
    assert not processes.stdout.strip(), processes.stdout
    with socket.socket() as connection:
        connection.settimeout(2)
        port_open = connection.connect_ex(('127.0.0.1', 18124)) == 0
    assert not port_open
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.free,utilization.gpu',
        '--format=csv,noheader'], capture_output=True, text=True, check=True)
    result = dict(disposition='owner_stopped_incomplete', submitted=False,
        candidate_id=saved['candidate_id'],
        requested_stop=read(HERE / 'OPERATOR-STOP-001.json'),
        stop_record_sha256=digest(HERE / 'OPERATOR-STOP-001.json'),
        response_seal_sha256=digest(RUN / 'RESPONSE_SEAL.json'),
        exact_replay_sha256=digest(HERE / 'VERIFICATION-001.json'),
        script_sha256=digest(Path(__file__)), partial_export=exported,
        reserved_at_utc=start['created_at_utc'], closed_at_utc=closed['created_at_utc'],
        reservation_to_closure_seconds=(time(closed) - time(start)).total_seconds(),
        interrupted_request='C18',
        interrupted_request_wall_interval_seconds=(time(interrupted) - time(last_start)).total_seconds(),
        interrupted_complete_reply=None, interrupted_endpoint_usage=None,
        interrupted_last_logged_generation_counter=token_lower_bound,
        interrupted_last_generation_log_line=last_generation,
        runtime_log_sha256=digest(log),
        all_sent_requests_use_medium_uncapped=True,
        command_line_xhigh_default_overridden_in_each_native_template_request=True,
        verification_at_utc=datetime.now(timezone.utc).isoformat(),
        owned_processes_absent=True, dedicated_port_closed=True,
        gpu_after_shutdown=gpu.stdout.strip(),
        limitations=[
            'C18 output was not returned; its last logged counter is a lower bound, not complete endpoint usage.',
            'The interrupted wall interval is measured between custody timestamps, not endpoint timing.',
            'Reservation-to-closure is elapsed attempt time, not a fabricated task_loop_completed metric.',
            'Exported work is incomplete and unsubmitted. No hidden draft was executed.',
            'No new model request, native tokenization, GPU load or actor operation occurred during review.'])
    save(HERE / '001/CLOSURE.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
