$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Assert-File {
    param([string]$RelativePath)

    $path = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path $path)) {
        throw "Missing required file: $RelativePath"
    }
}

function Assert-Text {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Message
    )

    if ($Text -notmatch $Pattern) {
        throw $Message
    }
}

Write-Host "==> Checking Vue page coverage"

$requiredFiles = @(
    "app/templates/vue_app.html",
    "frontend/src/app/main.js",
    "frontend/src/app/App.vue",
    "frontend/src/app/pages/HomePage.vue",
    "frontend/src/app/pages/ListsPage.vue",
    "frontend/src/app/pages/ListDetailPage.vue",
    "frontend/src/app/pages/UploadPage.vue",
    "frontend/src/app/pages/PreviewPage.vue",
    "frontend/src/app/pages/WordDetailPage.vue",
    "frontend/src/app/pages/ChallengeDayPage.vue",
    "frontend/src/app/pages/WrongWordsPage.vue",
    "frontend/src/app/pages/NewspaperPage.vue",
    "frontend/src/app/pages/NewspaperArticlePage.vue",
    "frontend/src/app/pages/BooklearnerPage.vue",
    "frontend/src/challenge/main.js",
    "frontend/src/challenge/ChallengeApp.vue"
)

foreach ($file in $requiredFiles) {
    Assert-File $file
}

$templateFiles = Get-ChildItem (Join-Path $RepoRoot "app/templates") -File | Select-Object -ExpandProperty Name
$allowedTemplates = @("base.html", "vue_app.html")
$unexpectedTemplates = $templateFiles | Where-Object { $_ -notin $allowedTemplates }
if ($unexpectedTemplates) {
    throw "Unexpected server templates remain: $($unexpectedTemplates -join ', ')"
}

$mainPath = Join-Path $RepoRoot "app/main.py"
$mainText = Get-Content -LiteralPath $mainPath -Raw -Encoding UTF8

Assert-Text $mainText 'TemplateResponse\("vue_app\.html"' "vue_app.html is not the server shell template"

$templateResponseMatches = [regex]::Matches($mainText, 'TemplateResponse\("([^"]+)"')
foreach ($match in $templateResponseMatches) {
    if ($match.Groups[1].Value -ne "vue_app.html") {
        throw "Unexpected TemplateResponse target: $($match.Groups[1].Value)"
    }
}

$expectedVuePaths = @(
    'return vue_shell\(request, db\)',
    'return vue_shell\(request, db, "booklearner"\)',
    'return vue_shell\(request, db, "booklearner/upload"\)',
    'return vue_shell\(request, db, "booklearner/quotes"\)',
    'return vue_shell\(request, db, f"booklearner/detail/\{analysis_id\}"\)',
    'return vue_shell\(request, db, "newspaper"\)',
    'return vue_shell\(request, db, f"newspaper/\{section_key\}/\{article_index\}"\)',
    'return vue_shell\(request, db, "lists"\)',
    'return vue_shell\(request, db, "upload"\)',
    'return vue_shell\(request, db, f"lists/\{word_list_id\}"\)',
    'return vue_shell\(request, db, f"challenge/\{word_list_id\}"\)',
    'return vue_shell\(request, db, "wrong-words"\)',
    'return vue_shell\(request, db, f"challenge-calendar/\{day\}"\)',
    'return vue_shell\(request, db, f"words/\{word_id\}"\)',
    'return vue_shell\(request, db, f"upload/preview/\{preview_id\}"\)'
)

foreach ($pattern in $expectedVuePaths) {
    Assert-Text $mainText $pattern "Expected Vue shell route not found: $pattern"
}

$sourceRoots = @(
    (Join-Path $RepoRoot "frontend/src/app"),
    (Join-Path $RepoRoot "frontend/src/challenge"),
    (Join-Path $RepoRoot "frontend/src/shared"),
    (Join-Path $RepoRoot "app/templates")
)

$forbiddenPatterns = @(
    'x-data',
    'Alpine',
    'onclick=',
    'hx-get',
    'hx-post',
    'htmx'
)

foreach ($root in $sourceRoots) {
    if (-not (Test-Path $root)) {
        continue
    }

    Get-ChildItem $root -Recurse -File | ForEach-Object {
        $relative = Resolve-Path -Relative $_.FullName
        $text = Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8
        foreach ($pattern in $forbiddenPatterns) {
            if ($text -match [regex]::Escape($pattern)) {
                throw "Forbidden legacy frontend pattern '$pattern' found in $relative"
            }
        }
    }
}

Write-Host "Vue coverage check complete."
