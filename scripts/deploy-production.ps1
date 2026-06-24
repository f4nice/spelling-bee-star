param(
    [string]$HostName = "47.116.28.2",
    [string]$UserName = "root",
    [string]$ServiceName = "spelling-bee-star.service",
    [string]$RemoteProjectPath = "/opt/spelling-bee-star",
    [string]$NodeModulesPath = "C:\Users\admin\AppData\Local\Temp\codex-node-ssh\node_modules",
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$password = $env:SPEAKEASY_SSH_PASSWORD
if ([string]::IsNullOrWhiteSpace($password)) {
    throw "Set SPEAKEASY_SSH_PASSWORD before running this script."
}

if (-not (Test-Path $NodeModulesPath)) {
    throw "Node ssh dependencies not found at $NodeModulesPath"
}

$status = git -C $RepoRoot status --short
if (-not $AllowDirty -and -not [string]::IsNullOrWhiteSpace($status)) {
    throw "Working tree is not clean. Commit or stash changes before deploying, or pass -AllowDirty deliberately."
}

$commit = (git -C $RepoRoot rev-parse --short HEAD).Trim()
$archivePath = Join-Path $env:TEMP "spelling-bee-$commit.tar"
$remoteArchivePath = "/tmp/spelling-bee-$commit.tar"

Write-Host "==> Packaging $commit"
git -C $RepoRoot archive --format=tar -o $archivePath HEAD

$nodeScript = @'
const { Client } = require("ssh2");

const config = JSON.parse(process.env.SPEAKEASY_DEPLOY_CONFIG || "{}");
const password = process.env.SPEAKEASY_SSH_PASSWORD || "";

function sh(value) {
  return "'" + String(value).replace(/'/g, "'\\''") + "'";
}

function connect() {
  const conn = new Client();
  return new Promise((resolve, reject) => {
    conn.on("ready", () => resolve(conn)).on("error", reject).connect({
      host: config.hostName,
      port: 22,
      username: config.userName,
      password,
      readyTimeout: 20000,
    });
  });
}

async function upload(conn) {
  await new Promise((resolve, reject) => {
    conn.sftp((err, sftp) => {
      if (err) return reject(err);
      sftp.fastPut(config.localArchivePath, config.remoteArchivePath, (putErr) => {
        if (putErr) return reject(putErr);
        resolve();
      });
    });
  });
}

async function exec(conn, command) {
  return await new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    conn.exec(command, (err, stream) => {
      if (err) return reject(err);
      stream
        .on("close", (code) => {
          if (code !== 0) {
            reject(new Error(`exit ${code}\n${stdout}\n${stderr}`));
            return;
          }
          resolve(stdout + (stderr ? `\nSTDERR:\n${stderr}` : ""));
        })
        .on("data", (data) => {
          stdout += data.toString();
        });
      stream.stderr.on("data", (data) => {
        stderr += data.toString();
      });
    });
  });
}

async function main() {
  const deployCommand = [
    "set -e",
    `cd ${sh(config.remoteProjectPath)}`,
    `backup_dir="${config.remoteProjectPath}/.codex-backups/$(date +%Y%m%d-%H%M%S)"`,
    `mkdir -p "$backup_dir"`,
    `tar --exclude='./.venv' --exclude='./uploads' --exclude='./.codex-backups' -czf "$backup_dir/code-before.tar.gz" .`,
    `tar -xf ${sh(config.remoteArchivePath)} -C ${sh(config.remoteProjectPath)}`,
    `chown -R root:root ${sh(config.remoteProjectPath)}`,
    `chmod -R u+rwX,go+rX ${sh(config.remoteProjectPath)}`,
    `service_user="$(systemctl show ${sh(config.serviceName)} -p User --value 2>/dev/null || true)"; if [ -f .env ]; then if [ -n "$service_user" ] && id "$service_user" >/dev/null 2>&1; then chown root:"$service_user" .env && chmod 640 .env; else chown root:root .env && chmod 600 .env; fi; fi`,
    `if command -v fc-list >/dev/null 2>&1 && ! fc-list :lang=zh | grep -q . && command -v apt-get >/dev/null 2>&1; then apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq fonts-wqy-microhei; fi`,
    `if id spellingbee >/dev/null 2>&1; then mkdir -p uploads/previews uploads/images uploads/audio uploads/book-covers && chown -R spellingbee:spellingbee uploads && chmod -R u+rwX,go+rX uploads; fi`,
    `systemctl restart ${sh(config.serviceName)}`,
    "sleep 1",
    `printf 'status=' && systemctl is-active ${sh(config.serviceName)}`,
    "printf '\\n'",
    `printf 'backup=' && echo "$backup_dir/code-before.tar.gz"`,
    `printf 'commit=${config.commit}\\n'`,
    `printf 'project_status=' && test -f PROJECT_STATUS.md && echo ok`,
    `printf 'deploy_script=' && test -f scripts/deploy-production.ps1 && echo ok`,
  ].join("\n");

  const conn = await connect();
  try {
    await upload(conn);
    const output = await exec(conn, deployCommand);
    process.stdout.write(output);
  } finally {
    conn.end();
  }
}

main().catch((err) => {
  console.error(err.message || String(err));
  process.exit(1);
});
'@

$tempScript = Join-Path $env:TEMP "speakeasy-deploy-production.js"
Set-Content -LiteralPath $tempScript -Value $nodeScript -Encoding UTF8

$config = @{
    hostName = $HostName
    userName = $UserName
    serviceName = $ServiceName
    remoteProjectPath = $RemoteProjectPath
    localArchivePath = $archivePath
    remoteArchivePath = $remoteArchivePath
    commit = $commit
} | ConvertTo-Json -Compress

$env:SPEAKEASY_DEPLOY_CONFIG = $config
$env:NODE_PATH = $NodeModulesPath

Write-Host "==> Uploading and deploying $commit"
node $tempScript
