param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "status", "stop")]
    [string]$Action = "status",

    [string]$VmAddress = "192.168.1.186",
    [string]$SshUser = "qradmin",
    [string]$SshKey = "$HOME\.ssh\id_ed25519_quant_radar_local",
    [int]$Port = 8011
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-SshArguments {
    return @(
        "-i", $SshKey,
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-o", "StrictHostKeyChecking=accept-new"
    )
}

function Assert-RemoteRuntime {
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
        throw "OpenSSH client is unavailable."
    }
    if (-not (Test-Path -LiteralPath $SshKey)) {
        throw "Ubuntu SSH key is missing: $SshKey"
    }

    $sshArguments = Get-SshArguments
    & ssh @sshArguments "$SshUser@$VmAddress" "true"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to reach Ubuntu at $SshUser@$VmAddress."
    }
}

function Invoke-RemoteCommand {
    param([string]$Command)

    $sshArguments = Get-SshArguments
    $output = & ssh @sshArguments "$SshUser@$VmAddress" $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Ubuntu command failed: $Command"
    }
    return @($output)
}

function Invoke-RemoteAdminCommand {
    param([string]$Command)

    $sshArguments = Get-SshArguments
    & ssh @sshArguments -t "$SshUser@$VmAddress" "sudo $Command"
    if ($LASTEXITCODE -ne 0) {
        throw "Ubuntu administrator command failed."
    }
}

function Test-TcpPort {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $connect = $client.ConnectAsync($VmAddress, $Port)
        return $connect.Wait(1500) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Get-UnitState {
    param([string]$Unit)

    $result = Invoke-RemoteCommand "systemctl is-active $Unit 2>/dev/null || true"
    $state = ($result | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($state)) {
        return "unknown"
    }
    return $state.Trim()
}

function Show-RemoteStatus {
    $mysqlState = Get-UnitState "mysql"
    $appState = Get-UnitState "speakeasy-local.service"
    $appPortOpen = Test-TcpPort
    $appPid = (
        Invoke-RemoteCommand `
            "systemctl show speakeasy-local.service -p MainPID --value 2>/dev/null || true" |
            Select-Object -First 1
    )
    if ([string]::IsNullOrWhiteSpace($appPid) -or $appPid -eq "0") {
        $appPid = "-"
    }

    [pscustomobject]@{
        Component = "MySQL"
        Status = $mysqlState
        Endpoint = "127.0.0.1:3306 (inside VM)"
        Detail = "Ubuntu systemd"
    }
    [pscustomobject]@{
        Component = "App"
        Status = if ($appState -eq "active" -and $appPortOpen) { "ready" } else { $appState }
        Endpoint = "http://$VmAddress`:$Port/"
        Detail = "Ubuntu systemd; PID $appPid"
    }
}

Assert-RemoteRuntime

switch ($Action) {
    "start" {
        Invoke-RemoteAdminCommand "systemctl start mysql speakeasy-local.service"
        Show-RemoteStatus | Format-Table -AutoSize
    }
    "status" {
        Show-RemoteStatus | Format-Table -AutoSize
    }
    "stop" {
        Invoke-RemoteAdminCommand "systemctl stop speakeasy-local.service mysql"
        Show-RemoteStatus | Format-Table -AutoSize
    }
}
