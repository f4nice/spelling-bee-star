param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "status", "stop")]
    [string]$Action = "status",

    [int]$Port = 8011
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeRoot = Join-Path $RepoRoot ".local-sync"
$MySqlRoot = Join-Path $RuntimeRoot "mysql-8.4.9"
$MySqlBin = Join-Path $MySqlRoot "PFiles64\MySQL\MySQL Server 8.4\bin"
$MySqlServer = Join-Path $MySqlBin "mysqld.exe"
$MySqlClient = Join-Path $MySqlBin "mysql.exe"
$MySqlAdmin = Join-Path $MySqlBin "mysqladmin.exe"
$MySqlConfig = Join-Path $MySqlRoot "my.ini"
$MySqlData = Join-Path $MySqlRoot "data"
$RunDir = Join-Path $RuntimeRoot "run"
$LogDir = Join-Path $RuntimeRoot "logs"
$AppPidFile = Join-Path $RunDir "app.pid"
$EnvFile = Join-Path $RepoRoot ".env"

function Read-LocalDatabaseConfig {
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        throw "Local configuration is missing: $EnvFile"
    }

    $databaseUrlLines = @(
        Get-Content -LiteralPath $EnvFile |
            Where-Object { $_ -match "^\s*DATABASE_URL\s*=" }
    )
    if ($databaseUrlLines.Count -ne 1) {
        throw "The local .env must contain exactly one DATABASE_URL entry."
    }

    $databaseUrl = ($databaseUrlLines[0] -replace "^\s*DATABASE_URL\s*=", "").Trim()
    if (
        ($databaseUrl.StartsWith('"') -and $databaseUrl.EndsWith('"')) -or
        ($databaseUrl.StartsWith("'") -and $databaseUrl.EndsWith("'"))
    ) {
        $databaseUrl = $databaseUrl.Substring(1, $databaseUrl.Length - 2)
    }

    try {
        $uri = [Uri]$databaseUrl
    }
    catch {
        throw "DATABASE_URL in .env is not a valid URI."
    }

    $databaseName = [Uri]::UnescapeDataString($uri.AbsolutePath.TrimStart("/"))
    $allowedHost = $uri.Host -ieq "127.0.0.1" -or $uri.Host -ieq "localhost"
    if (
        $uri.Scheme -ine "mysql+pymysql" -or
        -not $allowedHost -or
        $uri.Port -ne 3306 -or
        $databaseName -cne "spelling_bee"
    ) {
        throw "Refusing DATABASE_URL: local mode requires mysql+pymysql on 127.0.0.1/localhost:3306/spelling_bee."
    }

    $separator = $uri.UserInfo.IndexOf(":")
    if ($separator -le 0) {
        throw "DATABASE_URL in .env must include a username and password."
    }
    $user = [Uri]::UnescapeDataString($uri.UserInfo.Substring(0, $separator))
    $password = [Uri]::UnescapeDataString($uri.UserInfo.Substring($separator + 1))
    if ([string]::IsNullOrWhiteSpace($user) -or [string]::IsNullOrEmpty($password)) {
        throw "DATABASE_URL in .env must include a username and password."
    }

    return [pscustomobject]@{
        Url = $databaseUrl
        Host = $uri.Host
        Port = $uri.Port
        Database = $databaseName
        User = $user
        Password = $password
    }
}

$LocalDatabase = Read-LocalDatabaseConfig

function Test-TcpPort {
    param([int]$TargetPort)

    $client = [Net.Sockets.TcpClient]::new()
    try {
        $connect = $client.ConnectAsync("127.0.0.1", $TargetPort)
        return $connect.Wait(1000) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Get-ListeningProcessId {
    param([int]$TargetPort)

    $pattern = "^\s*TCP\s+127\.0\.0\.1:$TargetPort\s+\S+\s+LISTENING\s+(\d+)\s*$"
    foreach ($line in (& netstat.exe -ano -p tcp)) {
        if ($line -match $pattern) {
            return [int]$matches[1]
        }
    }
    return $null
}

function Invoke-MySqlScalar {
    param([string]$Query)

    $previousPassword = $env:MYSQL_PWD
    try {
        $env:MYSQL_PWD = $LocalDatabase.Password
        $output = & $MySqlClient `
            "--defaults-file=$MySqlConfig" `
            "--host=$($LocalDatabase.Host)" `
            "--port=$($LocalDatabase.Port)" `
            "--user=$($LocalDatabase.User)" `
            "--batch" `
            "--skip-column-names" `
            "--database=$($LocalDatabase.Database)" `
            "--execute=$Query" 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Local MySQL query failed."
        }
        return ($output | Select-Object -First 1).Trim()
    }
    finally {
        $env:MYSQL_PWD = $previousPassword
    }
}

function Test-LocalDatabase {
    if (-not (Test-TcpPort -TargetPort 3306)) {
        return $false
    }
    try {
        return (Invoke-MySqlScalar "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='spelling_bee';") -eq "27"
    }
    catch {
        return $false
    }
}

function Get-AppProcess {
    if (Test-Path -LiteralPath $AppPidFile) {
        $savedPid = (Get-Content -LiteralPath $AppPidFile -Raw).Trim()
        if ($savedPid -match "^\d+$") {
            $savedProcess = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
            $listenerPid = Get-ListeningProcessId -TargetPort $Port
            if ($null -ne $savedProcess -and $listenerPid -eq [int]$savedPid) {
                return $savedProcess
            }
        }
        Remove-Item -LiteralPath $AppPidFile -Force -ErrorAction SilentlyContinue
    }

    $listenerPid = Get-ListeningProcessId -TargetPort $Port
    if ($null -eq $listenerPid) {
        return $null
    }
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$listenerPid" -ErrorAction SilentlyContinue
    if ($null -eq $candidate -or $candidate.CommandLine -notmatch "uvicorn\s+app\.main:app") {
        return $null
    }
    New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
    Set-Content -LiteralPath $AppPidFile -Value $listenerPid -Encoding ascii
    return Get-Process -Id $listenerPid -ErrorAction SilentlyContinue
}

function Get-PythonExecutable {
    $python = (& py -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1).Trim()
    if ([string]::IsNullOrWhiteSpace($python) -or -not (Test-Path -LiteralPath $python)) {
        throw "Python is unavailable. Install the project requirements first."
    }
    return $python
}

function Start-LocalMySql {
    if (Test-LocalDatabase) {
        return
    }
    if (Test-TcpPort -TargetPort 3306) {
        throw "Port 3306 is occupied by a server that is not the expected 27-table local database."
    }
    foreach ($requiredPath in @($MySqlServer, $MySqlClient, $MySqlAdmin, $MySqlConfig, $MySqlData)) {
        if (-not (Test-Path -LiteralPath $requiredPath)) {
            throw "Local MySQL runtime is incomplete: $requiredPath"
        }
    }

    New-Item -ItemType Directory -Force -Path $RunDir, $LogDir | Out-Null
    $outLog = Join-Path $LogDir "mysql.out.log"
    $errLog = Join-Path $LogDir "mysql.err.log"
    Start-Process `
        -FilePath $MySqlServer `
        -ArgumentList @("`"--defaults-file=$MySqlConfig`"", "--console") `
        -WorkingDirectory $MySqlBin `
        -WindowStyle Hidden `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog | Out-Null

    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        if (Test-LocalDatabase) {
            return
        }
    }
    throw "Local MySQL did not become ready. Check $errLog"
}

function Start-LocalApp {
    $existing = Get-AppProcess
    if ($null -ne $existing -and (Test-TcpPort -TargetPort $Port)) {
        return
    }
    if (Test-TcpPort -TargetPort $Port) {
        throw "Port $Port is already occupied by another process."
    }

    New-Item -ItemType Directory -Force -Path $RunDir, $LogDir | Out-Null
    $python = Get-PythonExecutable
    $outLog = Join-Path $LogDir "app.out.log"
    $errLog = Join-Path $LogDir "app.err.log"

    $previousDatabaseUrl = $env:DATABASE_URL
    try {
        # This explicit process environment override wins over any user/system
        # DATABASE_URL and prevents an accidental production RDS connection.
        $env:DATABASE_URL = $LocalDatabase.Url
        $process = Start-Process `
            -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $Port) `
            -WorkingDirectory $RepoRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $outLog `
            -RedirectStandardError $errLog `
            -PassThru
        Set-Content -LiteralPath $AppPidFile -Value $process.Id -Encoding ascii
    }
    finally {
        $env:DATABASE_URL = $previousDatabaseUrl
    }

    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        if (Test-TcpPort -TargetPort $Port) {
            return
        }
        if ($process.HasExited) {
            throw "Local app exited during startup. Check $errLog"
        }
    }
    throw "Local app did not become ready. Check $errLog"
}

function Stop-LocalApp {
    $process = Get-AppProcess
    if ($null -ne $process) {
        Stop-Process -Id $process.Id
        $process.WaitForExit(10000) | Out-Null
    }
    Remove-Item -LiteralPath $AppPidFile -Force -ErrorAction SilentlyContinue
}

function Stop-LocalMySql {
    if (-not (Test-TcpPort -TargetPort 3306)) {
        return
    }
    if (-not (Test-LocalDatabase)) {
        throw "Refusing to stop port 3306 because it is not the expected local database."
    }
    $previousPassword = $env:MYSQL_PWD
    try {
        $env:MYSQL_PWD = $LocalDatabase.Password
        & $MySqlAdmin `
            "--defaults-file=$MySqlConfig" `
            "--host=$($LocalDatabase.Host)" `
            "--port=$($LocalDatabase.Port)" `
            "--user=$($LocalDatabase.User)" `
            "shutdown" 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Local MySQL did not shut down cleanly."
        }
    }
    finally {
        $env:MYSQL_PWD = $previousPassword
    }
}

function Show-LocalStatus {
    $databaseReady = Test-LocalDatabase
    $appProcess = Get-AppProcess
    $appPortOpen = Test-TcpPort -TargetPort $Port
    $appReady = $appPortOpen -and $null -ne $appProcess
    $tableCount = if ($databaseReady) { Invoke-MySqlScalar "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='spelling_bee';" } else { "unavailable" }

    [pscustomobject]@{
        Component = "MySQL"
        Status = if ($databaseReady) { "ready" } else { "stopped" }
        Endpoint = "127.0.0.1:3306/spelling_bee"
        Detail = "$tableCount tables; loopback only"
    }
    [pscustomobject]@{
        Component = "App"
        Status = if ($appReady) { "ready" } elseif ($appPortOpen) { "conflict" } else { "stopped" }
        Endpoint = "http://127.0.0.1:$Port/"
        Detail = if ($appReady) { "PID $($appProcess.Id); local DATABASE_URL forced" } elseif ($appPortOpen) { "port occupied by an unmanaged process" } else { "no managed PID" }
    }
}

Push-Location $RepoRoot
try {
    switch ($Action) {
        "start" {
            Start-LocalMySql
            Start-LocalApp
            Show-LocalStatus | Format-Table -AutoSize
        }
        "status" {
            Show-LocalStatus | Format-Table -AutoSize
        }
        "stop" {
            Stop-LocalApp
            Stop-LocalMySql
            Show-LocalStatus | Format-Table -AutoSize
        }
    }
}
finally {
    Pop-Location
}
