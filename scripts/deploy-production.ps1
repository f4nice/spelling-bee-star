param(
    [string]$HostName = "192.168.1.186",
    [string]$UserName = "qradmin",
    [string]$ServiceName = "speakeasy-local.service",
    [string]$RemoteProjectPath = "/opt/speakeasy/current",
    [string]$SshKey = "$HOME\.ssh\id_ed25519_quant_radar_local",
    [string]$PublicBaseUrl = "https://www.newabby.com",
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw "OpenSSH client is unavailable."
}
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    throw "OpenSSH scp client is unavailable."
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

$status = git -C $RepoRoot status --short
if (-not $AllowDirty -and -not [string]::IsNullOrWhiteSpace($status)) {
    throw "Working tree is not clean. Commit changes before deploying, or pass -AllowDirty deliberately."
}

$commit = (git -C $RepoRoot rev-parse --short HEAD).Trim()
if ($commit -notmatch "^[0-9a-f]+$") {
    throw "Unable to resolve the Git commit."
}

$archivePath = Join-Path $env:TEMP "speakeasy-ubuntu-$commit.tar"
$remoteArchivePath = "/home/$UserName/speakeasy-staging/speakeasy-$commit.tar"
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
archive="$3"
commit="$4"
staging_root="$HOME/speakeasy-staging/deploy"
backup_dir="$HOME/speakeasy-staging/code-backups/$(date +%Y%m%d-%H%M%S)-$commit"

test -s "$archive"
test -d "$project/.venv"
test -f "$project/.env"

mkdir -p "$staging_root" "$backup_dir"
release_dir=$(mktemp -d "$staging_root/$commit.XXXXXX")

cleanup() {
  case "$release_dir" in
    "$staging_root"/*) rm -rf -- "$release_dir" ;;
  esac
}
trap cleanup EXIT

tar --exclude=.venv --exclude=uploads --exclude=.env \
  -czf "$backup_dir/code-before.tar.gz" -C "$project" .
tar -xf "$archive" -C "$release_dir"

rsync -a --delete \
  --exclude=.env \
  --exclude=.venv \
  --exclude=uploads \
  "$release_dir/" "$project/"

cd "$project"
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
.venv/bin/python -m compileall -q app

old_pid=$(systemctl show "$service_name" -p MainPID --value)
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
case "$old_command" in
  *"uvicorn app.main:app"*"--port 8011"*) kill -TERM "$old_pid" ;;
  *) echo "Refusing to stop unexpected service process: $old_command" >&2; exit 1 ;;
esac

for _ in $(seq 1 60); do
  new_pid=$(systemctl show "$service_name" -p MainPID --value)
  state=$(systemctl is-active "$service_name" 2>/dev/null || true)
  if [ "$state" = "active" ] &&
     [ "$new_pid" != "0" ] &&
     [ "$new_pid" != "$old_pid" ] &&
     curl -fsS -o /dev/null http://127.0.0.1:8011/login; then
    printf 'status=active\nold_pid=%s\nnew_pid=%s\nbackup=%s\ncommit=%s\n' \
      "$old_pid" "$new_pid" "$backup_dir/code-before.tar.gz" "$commit"
    exit 0
  fi
  sleep 1
done

journalctl -u "$service_name" -n 50 --no-pager
exit 1
'@
$remoteScript = $remoteScript -replace "`r`n", "`n"

try {
    Write-Host "==> Packaging $commit"
    git -C $RepoRoot archive --format=tar -o $archivePath HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the deployment archive."
    }

    Write-Host "==> Uploading $commit to Ubuntu $HostName"
    & scp @sshArguments $archivePath "${target}:$remoteArchivePath"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to upload the deployment archive."
    }

    Write-Host "==> Deploying and restarting $ServiceName"
    $remoteCommand = "bash -s -- $RemoteProjectPath $ServiceName $remoteArchivePath $commit"
    $remoteScript | & ssh @sshArguments $target $remoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Ubuntu deployment failed."
    }

    Write-Host "==> Checking public site"
    $response = Invoke-WebRequest -UseBasicParsing -Uri $PublicBaseUrl -TimeoutSec 20
    if ($response.StatusCode -ne 200) {
        throw "$PublicBaseUrl returned HTTP $($response.StatusCode)."
    }
    Write-Host "public_status=$($response.StatusCode)"
}
finally {
    Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
}
