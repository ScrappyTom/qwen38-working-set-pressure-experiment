"""Scoped passive telemetry; absent Windows counters remain explicitly unavailable."""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent

@contextmanager
def monitor(folder, runtime_port, log):
    folder = Path(folder)
    command = ('Get-NetTCPConnection -LocalPort '+str(int(runtime_port))+
               " -State Listen | Select-Object -ExpandProperty OwningProcess -Unique | ConvertTo-Json -Compress")
    raw = subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],
        creationflags=subprocess.CREATE_NO_WINDOW)
    pid = json.loads(raw)
    if type(pid) is not int or pid<=0:
        raise ValueError('Owned runtime listening PID is not unambiguous')
    output, stop = folder/'process-memory.jsonl', folder/'MEMORY-MONITOR-STOP.txt'
    if output.exists() or stop.exists():
        raise ValueError('Memory monitor attempt already exists')
    error = (folder/'memory-monitor.stderr.log').open('xb')
    process = subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-File',
        str(HERE/'sample_memory.ps1'),'-ServerProcessId',str(pid),'-OutputPath',str(output),'-StopPath',str(stop)],
        stdout=subprocess.DEVNULL,stderr=error,creationflags=subprocess.CREATE_NO_WINDOW)
    log.append('process_memory_monitor_started',dict(server_pid=pid,sampling_seconds=2,
        pid_source='exclusively_owned_runtime_listening_port',missing_values_are_not_zero=True),[])
    try:
        yield pid
    finally:
        stop.write_text('Normal monitor closure\n',encoding='utf-8')
        try:
            returncode=process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.terminate()
            returncode=process.wait(timeout=10)
        error.close()
        log.append('process_memory_monitor_closed',dict(server_pid=pid,returncode=returncode,
            samples=sum(1 for _ in output.open(encoding='utf-8')) if output.exists() else 0,
            data_not_a_causal_diagnosis=True),[])

def summary(path, pid):
    rows=[json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()]
    def maximum(key):
        values=[row[key] for row in rows if key in row]
        return max(values) if values else None
    owned=[gpu for row in rows for gpu in row.get('gpu_process_memory',[])
           if gpu.get('name','').startswith('pid_'+str(pid)+'_')]
    return dict(samples=len(rows),server_pid=pid,
        max_server_working_set_bytes=maximum('server_working_set_bytes'),
        max_server_private_bytes=maximum('server_private_bytes'),
        owned_gpu_counter_samples=len(owned),
        max_owned_dedicated_bytes=max((g['dedicated_bytes'] for g in owned),default=None),
        max_owned_shared_bytes=max((g['shared_bytes'] for g in owned),default=None),
        counters_are_windows_allocation_measurements_not_proof_of_causation=True,
        unavailable_messages=sorted({str(v) for row in rows for k,v in row.items() if k.endswith('unavailable')}))
