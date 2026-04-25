param(
    [ValidateSet("stable", "contract")]
    [string]$Mode = "stable"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")

function Invoke-Step {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string[]]$Command
    )

    Write-Host "==> $Name"
    Push-Location $WorkingDirectory
    try {
        & $Command[0] @($Command | Select-Object -Skip 1)
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Test-GoldenJson {
    $GoldenPath = Join-Path $Root "examples\crawler-selection\ecommerce-search-selection.json"
    $payload = Get-Content $GoldenPath -Raw | ConvertFrom-Json
    if ($payload.scenario -ne "ecommerce_listing") {
        throw "crawler-selection golden scenario mismatch"
    }
    if ($payload.crawler_type -ne "ecommerce_search") {
        throw "crawler-selection golden crawler_type mismatch"
    }
    if ($payload.recommended_runner -ne "browser") {
        throw "crawler-selection golden recommended_runner mismatch"
    }
    Write-Host "==> crawler-selection golden JSON parsed"
}

Test-GoldenJson

$PreviousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
    $Root
}
else {
    "$Root;$PreviousPythonPath"
}

Invoke-Step "PySpider crawler-selection contract" `
    $Root `
    @("python", "-m", "pytest", "pyspider\tests\test_crawler_selector.py", "-q")

if ($Mode -eq "contract") {
    $env:PYTHONPATH = $PreviousPythonPath
    Write-Host "Contract gate complete."
    exit 0
}

Invoke-Step "PySpider stable targeted regression" `
    $Root `
    @("python", "-m", "pytest", "pyspider\tests\test_crawler_selector.py", "pyspider\tests\test_video_downloader_facade.py", "pyspider\tests\test_dependencies.py", "-q")

$env:PYTHONPATH = $PreviousPythonPath

Invoke-Step "GoSpider full tests" `
    (Join-Path $Root "gospider") `
    @("go", "test", "./...")

Invoke-Step "RustSpider compile check" `
    (Join-Path $Root "rustspider") `
    @("cargo", "check", "--quiet")

Invoke-Step "RustSpider library tests" `
    (Join-Path $Root "rustspider") `
    @("cargo", "test", "--quiet", "--lib")

Invoke-Step "JavaSpider full tests" `
    (Join-Path $Root "javaspider") `
    @("mvn", "-q", "test")

Write-Host "Stable SuperSpider verification gate passed."
