param(
    [string]$HostName = "192.168.1.186",
    [string]$UserName = "qradmin",
    [string]$ServiceName = "speakeasy-local.service",
    [string]$Since = "15 minutes ago",
    [string]$RemoteProjectPath = "/opt/speakeasy/current",
    [string]$SshKey = "$HOME\.ssh\id_ed25519_quant_radar_local"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw "OpenSSH client is unavailable."
}
if (-not (Test-Path -LiteralPath $SshKey)) {
    throw "Ubuntu SSH key is missing: $SshKey"
}
if ($HostName -notmatch "^[A-Za-z0-9.-]+$") {
    throw "Invalid Ubuntu host name."
}
if ($UserName -notmatch "^[A-Za-z0-9_-]+$") {
    throw "Invalid Ubuntu user name."
}
if ($ServiceName -notmatch "^[A-Za-z0-9_.@-]+$") {
    throw "Invalid systemd service name."
}
if ($RemoteProjectPath -notmatch "^/[A-Za-z0-9_./-]+$") {
    throw "Invalid Ubuntu project path."
}
if ($Since -notmatch "^[A-Za-z0-9 .:+-]+$") {
    throw "Invalid journal time range."
}

$target = "$UserName@$HostName"
$sshArguments = @(
    "-i", $SshKey,
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    "-o", "StrictHostKeyChecking=accept-new"
)

$remoteScript = @'
set -euo pipefail

project="$1"
service_name="$2"
since="$3"

printf 'status='
systemctl is-active "$service_name"
printf 'enabled='
systemctl is-enabled "$service_name"
printf 'project=%s\n' "$project"
test -f "$project/PROJECT_STATUS.md"

matches=$(journalctl -u "$service_name" --since "$since" --no-pager |
  grep -E 'Traceback|Internal Server Error|ERROR|Exception|Failed' || true)
if [ -n "$matches" ]; then
  printf 'log_errors=found\n%s\n' "$matches"
  exit 2
fi

printf 'log_errors=none\n'
'@
$remoteScript = $remoteScript -replace "`r`n", "`n"

Write-Host "==> Checking Ubuntu production service and logs"
$remoteCommand = "bash -s -- $RemoteProjectPath $ServiceName '$Since'"
$remoteScript | & ssh @sshArguments $target $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Production log check failed."
}
