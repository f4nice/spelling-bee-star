param(
    [switch]$SetupKey,
    [switch]$Check,
    [switch]$ListModels,
    [switch]$DryRun,
    [switch]$SmokeTest,
    [string]$RequestFile
)

$ErrorActionPreference = 'Stop'
$taskKeyPath = Join-Path $env:LOCALAPPDATA 'SpeakEasy\grok-api-key.xml'
$taskNodeScript = Join-Path $PSScriptRoot 'grok-dev.mjs'

if ($SetupKey) {
    $taskSecureKey = Read-Host 'Paste xAI API key (hidden; stored encrypted for this Windows user)' -AsSecureString
    if ($taskSecureKey.Length -eq 0) { throw 'Empty key was not saved.' }
    try {
        $taskKeyText = ([Net.NetworkCredential]::new('', $taskSecureKey)).Password.Trim()
        if ($taskKeyText -cnotmatch '^xai-[A-Za-z0-9_-]{20,}$') {
            throw 'Key format not recognized. Paste only the complete xai-... API key, without quotes or commands. Existing key was not changed.'
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $taskKeyPath) -Force | Out-Null
        $taskSecureKey | Export-Clixml -LiteralPath $taskKeyPath
    } finally {
        $taskKeyText = $null
        $taskSecureKey.Dispose()
    }
    Write-Output 'xAI key saved with Windows user encryption. No API request was made.'
    exit 0
}

$taskPreviousKey = $env:XAI_API_KEY
$taskKeySource = 'process environment'
$taskExitCode = 1
try {
    if (-not $DryRun -and [string]::IsNullOrWhiteSpace($env:XAI_API_KEY)) {
        $env:XAI_API_KEY = [Environment]::GetEnvironmentVariable('XAI_API_KEY', 'User')
        $taskKeySource = 'user environment'
        if ([string]::IsNullOrWhiteSpace($env:XAI_API_KEY) -and (Test-Path -LiteralPath $taskKeyPath)) {
            $taskKeySource = 'encrypted local file'
            $taskSecureKey = Import-Clixml -LiteralPath $taskKeyPath
            $taskPointer = [IntPtr]::Zero
            try {
                $taskPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($taskSecureKey)
                $env:XAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($taskPointer)
            } finally {
                if ($taskPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($taskPointer) }
                $taskSecureKey.Dispose()
            }
        }
    }
    $taskArguments = @($taskNodeScript)
    if ($Check) {
        Write-Output ('Credential source: ' + $(if ([string]::IsNullOrWhiteSpace($env:XAI_API_KEY)) { 'none' } else { $taskKeySource }))
        $taskArguments += '--check'
    }
    elseif ($ListModels) { $taskArguments += '--list-models' }
    elseif ($SmokeTest) { $taskArguments += '--smoke-test' }
    else {
        if ([string]::IsNullOrWhiteSpace($RequestFile)) { throw 'Provide -RequestFile, -Check, -ListModels, -SmokeTest, or -SetupKey.' }
        if ($DryRun) { $taskArguments += '--dry-run' }
        $taskArguments += $RequestFile
    }
    & node @taskArguments
    $taskExitCode = $LASTEXITCODE
} finally {
    $env:XAI_API_KEY = $taskPreviousKey
}
exit $taskExitCode
