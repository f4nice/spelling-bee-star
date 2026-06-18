param(
    [string]$HostName = "47.116.28.2",
    [string]$UserName = "root",
    [string]$ServiceName = "spelling-bee-star.service",
    [string]$Since = "15 minutes ago",
    [string]$RemoteProjectPath = "/opt/spelling-bee-star",
    [string]$NodeModulesPath = "C:\Users\admin\AppData\Local\Temp\codex-node-ssh\node_modules"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$password = $env:SPEAKEASY_SSH_PASSWORD
if ([string]::IsNullOrWhiteSpace($password)) {
    throw "Set SPEAKEASY_SSH_PASSWORD before running this script."
}

if (-not (Test-Path $NodeModulesPath)) {
    throw "Node ssh dependencies not found at $NodeModulesPath"
}

$nodeScript = @'
const { Client } = require("ssh2");

const config = JSON.parse(process.env.SPEAKEASY_LOG_CHECK_CONFIG || "{}");
const password = process.env.SPEAKEASY_SSH_PASSWORD || "";

function sh(value) {
  return "'" + String(value).replace(/'/g, "'\\''") + "'";
}

const command = [
  "set -e",
  `printf 'status=' && systemctl is-active ${sh(config.serviceName)}`,
  "printf '\\n'",
  `cd ${sh(config.remoteProjectPath)} && printf 'project=' && pwd`,
  "printf '\\n'",
  `if [ -f PROJECT_STATUS.md ]; then printf 'project_status=ok\\n'; else printf 'project_status=missing\\n'; fi`,
  `matches=$(journalctl -u ${sh(config.serviceName)} --since ${sh(config.since)} --no-pager | grep -E 'Traceback|Internal Server Error|ERROR|Exception|Failed' || true)`,
  `if [ -n "$matches" ]; then printf 'log_errors=found\\n%s\\n' "$matches"; exit 2; else printf 'log_errors=none\\n'; fi`,
].join("\n");

const conn = new Client();
let stdout = "";
let stderr = "";

conn
  .on("ready", () => {
    conn.exec(command, (err, stream) => {
      if (err) throw err;
      stream
        .on("close", (code) => {
          conn.end();
          if (code !== 0) {
            console.error(stderr || stdout);
            process.exit(code || 1);
          }
          process.stdout.write(stdout.trim() || "no output");
          if (stderr.trim()) {
            process.stderr.write(`\n${stderr.trim()}`);
          }
        })
        .on("data", (data) => {
          stdout += data.toString();
        });
      stream.stderr.on("data", (data) => {
        stderr += data.toString();
      });
    });
  })
  .on("error", (err) => {
    console.error(err.message);
    process.exit(1);
  })
  .connect({
    host: config.hostName,
    port: 22,
    username: config.userName,
    password,
    readyTimeout: 20000,
  });
'@

$tempScript = Join-Path $env:TEMP "speakeasy-check-production-logs.js"
Set-Content -LiteralPath $tempScript -Value $nodeScript -Encoding UTF8

$config = @{
    hostName = $HostName
    userName = $UserName
    serviceName = $ServiceName
    since = $Since
    remoteProjectPath = $RemoteProjectPath
} | ConvertTo-Json -Compress

$env:SPEAKEASY_LOG_CHECK_CONFIG = $config
$env:NODE_PATH = $NodeModulesPath

Write-Host "==> Checking production service and logs"
node $tempScript
