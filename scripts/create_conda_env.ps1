<#
Creates or updates the conda environment described by environment.yml

Usage (PowerShell):
  .\scripts\create_conda_env.ps1

This script will:
- Verify `conda` is available
- Check if an environment named `tdx-dev` exists and optionally remove it
- Create the environment from `environment.yml`
#>
try {
    conda --version > $null 2>&1
} catch {
    Write-Error "Conda not found in PATH. Please install Anaconda/Miniconda and ensure `conda` is available in your shell."
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$envFile = Resolve-Path (Join-Path $scriptDir '..\environment.yml') -ErrorAction Stop

Write-Host "Using environment file: $envFile"

# Determine env name from file (fallback to tdx-dev)
$envName = 'tdx-dev'
try {
    $y = Get-Content $envFile | Out-String
    if ($y -match "^name:\s*(\S+)") { $envName = $Matches[1] }
} catch {
    Write-Host "Couldn't read name from environment.yml; using default name '$envName'"
}

Write-Host "Target conda environment: $envName"

# Check if env exists
$exists = conda env list | Select-String "^$envName\s" -ErrorAction SilentlyContinue
if ($exists) {
    $reply = Read-Host "Environment '$envName' already exists. Remove and recreate? (y/N)"
    if ($reply -ne 'y' -and $reply -ne 'Y') {
        Write-Host "Skipping creation. Activate with: conda activate $envName"
        exit 0
    }
    Write-Host "Removing existing environment '$envName'..."
    conda env remove -n $envName -y
}

Write-Host "Creating conda environment '$envName' from $envFile ..."
conda env create -f $envFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "Installing project package and development extras ..."
    conda run -n $envName python -m pip install -r (Join-Path $scriptDir '..\requirements-dev.txt')

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Environment was created, but package installation failed. Check the output above."
        exit $LASTEXITCODE
    }

    Write-Host "Environment '$envName' created successfully. Activate it with:`n  conda activate $envName"
} else {
    Write-Error "Failed to create environment. See messages above for errors."
    exit $LASTEXITCODE
}
