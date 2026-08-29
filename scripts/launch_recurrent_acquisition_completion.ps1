$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = 'C:\Users\danmc\Isolated experiments 8.24.2026\_venvs\qwen38_metadata_working_set\Scripts\python.exe'
$stdout = 'C:\e11-completion-runner.stdout.log'
$stderr = 'C:\e11-completion-runner.stderr.log'
$pidRecord = 'C:\e11-completion-runner.pid'

foreach ($path in @($stdout, $stderr, $pidRecord)) {
    if (Test-Path -LiteralPath $path) {
        throw "Completion launcher artifact already exists: $path"
    }
}
if (Test-Path -LiteralPath 'C:\e11-completion') {
    throw 'Completion output root already exists'
}

$env:PYTHONPATH = Join-Path $repo 'src'
$process = Start-Process -FilePath $python `
    -ArgumentList 'scripts\run_recurrent_acquisition_completion.py' `
    -WorkingDirectory $repo `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $pidRecord -Value ([string]$process.Id) -Encoding ascii -NoNewline
[pscustomobject]@{
    pid = $process.Id
    repository = $repo
    output_root = 'C:\e11-completion'
    stdout = $stdout
    stderr = $stderr
} | ConvertTo-Json -Compress
