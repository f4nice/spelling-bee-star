param(
    [string]$BaseUrl = "http://47.116.28.2:8010",
    [switch]$SkipBuild,
    [switch]$SkipHttp
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$FrontendRoot = Join-Path $RepoRoot "frontend"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Script
    )

    Write-Host "==> $Name"
    & $Script
}

Invoke-Step "Git status" {
    git -C $RepoRoot status --short
}

if (-not $SkipBuild) {
    Invoke-Step "Frontend build" {
        Push-Location $FrontendRoot
        try {
            npm run build
        }
        finally {
            Pop-Location
        }
    }
}

Invoke-Step "Python compile" {
    py -3 -m compileall -q (Join-Path $RepoRoot "app")
}

Invoke-Step "Markdown UTF-8 check" {
    $docs = @("README.md", "PROJECT_STATUS.md", "STYLE_GUIDE.md", "VUE_MIGRATION_STATUS.md")
    foreach ($doc in $docs) {
        $path = Join-Path $RepoRoot $doc
        if (Test-Path $path) {
            $text = Get-Content -LiteralPath $path -Raw -Encoding UTF8
            if ($text.Contains([char]0xfffd)) {
                throw "$doc contains Unicode replacement characters"
            }
        }
    }
}

if (-not $SkipHttp) {
    Invoke-Step "HTTP smoke checks" {
        $base = $BaseUrl.TrimEnd("/")
        $paths = @(
            "/",
            "/lists",
            "/words/1?edit=1&list_id=24",
            "/challenge/24",
            "/booklearner",
            "/challenge-calendar/2026-06-16"
        )

        foreach ($path in $paths) {
            $url = "$base$path"
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15
            if ($response.StatusCode -ne 200) {
                throw "$url returned HTTP $($response.StatusCode)"
            }
            Write-Host "200 $url"
        }
    }
}

Write-Host "Verification complete."
