param(
    [switch]$SetupKey,
    [switch]$Check,
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
    New-Item -ItemType Directory -Path (Split-Path -Parent $taskKeyPath) -Force | Out-Null
    $taskSecureKey | Export-Clixml -LiteralPath $taskKeyPath
    $taskSecureKey.Dispose()
    Write-Output 'xAI key saved with Windows user encryption. No API request was made.'
    exit 0
}

$taskPreviousKey = $env:XAI_API_KEY
$taskExitCode = 1
try {
    if (-not $DryRun -and [string]::IsNullOrWhiteSpace($env:XAI_API_KEY)) {
        $env:XAI_API_KEY = [Environment]::GetEnvironmentVariable('XAI_API_KEY', 'User')
        if ([string]::IsNullOrWhiteSpace($env:XAI_API_KEY) -and (Test-Path -LiteralPath $taskKeyPath)) {
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
    if ($Check) { $taskArguments += '--check' }
    elseif ($SmokeTest) { $taskArguments += '--smoke-test' }
    else {
        if ([string]::IsNullOrWhiteSpace($RequestFile)) { throw 'Provide -RequestFile, -Check, -SmokeTest, or -SetupKey.' }
        if ($DryRun) { $taskArguments += '--dry-run' }
        $taskArguments += $RequestFile
    }
    & node @taskArguments
    $taskExitCode = $LASTEXITCODE
} finally {
    $env:XAI_API_KEY = $taskPreviousKey
}
exit $taskExitCode
