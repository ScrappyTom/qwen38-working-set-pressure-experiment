param([Parameter(Mandatory=$true)][int]$ServerProcessId,
      [Parameter(Mandatory=$true)][string]$OutputPath,
      [Parameter(Mandatory=$true)][string]$StopPath)
$ErrorActionPreference = 'Stop'
$writer = [System.IO.StreamWriter]::new($OutputPath,$false,[System.Text.UTF8Encoding]::new($false))
try {
    while (-not (Test-Path -LiteralPath $StopPath)) {
        $row = [ordered]@{timestamp_utc=[DateTime]::UtcNow.ToString('o');server_pid=$ServerProcessId}
        try {
            $serverProcess = Get-Process -Id $ServerProcessId -ErrorAction Stop
            $row.server_working_set_bytes = $serverProcess.WorkingSet64
            $row.server_private_bytes = $serverProcess.PrivateMemorySize64
            $row.server_cpu_seconds = $serverProcess.TotalProcessorTime.TotalSeconds
        } catch { $row.server_measurement_unavailable = $_.Exception.Message }
        try {
            $memory = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
            $row.system_available_bytes = [int64]$memory.AvailableBytes
            $row.system_committed_bytes = [int64]$memory.CommittedBytes
        } catch { $row.system_memory_unavailable = $_.Exception.Message }
        try {
            $gpuRows = @(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory)
            $row.gpu_process_memory = @($gpuRows | ForEach-Object {
                [ordered]@{name=$_.Name;dedicated_bytes=[int64]$_.DedicatedUsage;
                    shared_bytes=[int64]$_.SharedUsage;total_committed_bytes=[int64]$_.TotalCommitted}
            })
        } catch { $row.gpu_process_counters_unavailable = $_.Exception.Message }
        try {
            $gpuState = & nvidia-smi -i 0 --query-gpu=timestamp,memory.used,memory.free,utilization.gpu,utilization.memory,power.draw --format=csv,noheader,nounits 2>$null
            if ($LASTEXITCODE -ne 0) { throw 'nvidia-smi failed' }
            $row.nvidia_gpu_sample = [string]$gpuState
        } catch { $row.nvidia_gpu_sample_unavailable = $_.Exception.Message }
        $writer.WriteLine(($row | ConvertTo-Json -Depth 5 -Compress))
        $writer.Flush()
        Start-Sleep -Seconds 2
    }
} finally { $writer.Dispose() }
