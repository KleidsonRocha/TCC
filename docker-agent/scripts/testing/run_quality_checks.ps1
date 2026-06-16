param(
    [switch]$SkipPytest,
    [switch]$Mutation,
    [string]$MutationProfile = "all_curated",
    [switch]$MutationResults,
    [switch]$CleanMutation,
    [string]$PytestArgs = "-q"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name"
    & $Command
}

function Invoke-DockerCompose {
    param([string[]]$Arguments)

    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "Docker availability" {
    & docker --version
    if ($LASTEXITCODE -ne 0) {
        throw "docker is not available"
    }
}

Invoke-Step "Build docker-agent image" {
    Invoke-DockerCompose @("build", "docker-agent")
}

if (-not $SkipPytest) {
    Invoke-Step "Pytest" {
        $pytestParts = @()
        if (-not [string]::IsNullOrWhiteSpace($PytestArgs)) {
            $pytestParts = $PytestArgs.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
        }
        $pytestCommand = @("run", "--rm", "-v", "${ProjectRoot}:/app", "docker-agent", "pytest")
        $pytestCommand += $pytestParts
        Invoke-DockerCompose $pytestCommand
    }
}

if ($Mutation) {
    Invoke-Step "Mutation testing ($MutationProfile)" {
        $mutationArgs = @(
            "run",
            "--rm",
            "-v",
            "${ProjectRoot}:/app",
            "docker-agent",
            "python",
            "scripts/testing/run_mutation_tests.py",
            $MutationProfile
        )
        if ($CleanMutation) {
            $mutationArgs += "--clean"
        }
        if ($MutationResults) {
            $mutationArgs += "--results"
        }
        Invoke-DockerCompose $mutationArgs
    }
}

Write-Host ""
Write-Host "Quality checks finished."
