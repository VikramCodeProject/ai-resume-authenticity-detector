$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$frontendServer = Join-Path $frontendDir "serve.py"
$venvDir = Join-Path $repoRoot ".venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$logDir = Join-Path $repoRoot "logs"
$backendStdOutLog = Join-Path $logDir "dev-backend.stdout.log"
$backendStdErrLog = Join-Path $logDir "dev-backend.stderr.log"
$frontendStdOutLog = Join-Path $logDir "dev-frontend.stdout.log"
$frontendStdErrLog = Join-Path $logDir "dev-frontend.stderr.log"
$healthUrl = "http://127.0.0.1:8000/api/health"
$frontendUrl = "http://127.0.0.1:3000/"

function Get-DotenvValue {
    param(
        [string]$FilePath,
        [string]$Key
    )

    if (-not (Test-Path $FilePath)) {
        return $null
    }

    $prefix = "$Key="
    $line = Get-Content $FilePath | Where-Object {
        $_ -and -not $_.TrimStart().StartsWith("#") -and $_.StartsWith($prefix)
    } | Select-Object -First 1

    if (-not $line) {
        return $null
    }

    return $line.Substring($prefix.Length).Trim()
}

# Ensure JWT uses a sufficiently strong key in local dev runs.
$dotenvJwt = Get-DotenvValue -FilePath (Join-Path $repoRoot ".env") -Key "JWT_SECRET"
$shouldInjectJwt = $true

if ($dotenvJwt -and $dotenvJwt.Length -ge 32) {
    $shouldInjectJwt = $false
}

if ($env:JWT_SECRET -and $env:JWT_SECRET.Length -ge 32) {
    $shouldInjectJwt = $false
}

if ($shouldInjectJwt) {
    $env:JWT_SECRET = "local-dev-jwt-secret-2026-03-13-strong-key-9a7c4d2f"
    Write-Host "Injected strong JWT_SECRET for local backend session"
}

if (-not $env:JWT_ALGORITHM) {
    $env:JWT_ALGORITHM = "HS256"
}

if (-not $env:ENVIRONMENT) {
    $env:ENVIRONMENT = "development"
}

function Stop-PortListeners {
    param(
        [int[]]$Ports
    )

    foreach ($port in $Ports) {
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if (-not $connections) {
            continue
        }

        $listenerPids = $connections |
            Where-Object { $_.OwningProcess -gt 0 } |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($listenerPid in $listenerPids) {
            try {
                Stop-Process -Id $listenerPid -Force -ErrorAction Stop
                Write-Host "Stopped process on port ${port} (PID: $listenerPid)"
            } catch {
                Write-Warning "Could not stop PID $listenerPid on port ${port}: $($_.Exception.Message)"
            }
        }
    }
}

function Wait-ForPortsToClear {
    param(
        [int[]]$Ports
    )

    for ($i = 0; $i -lt 10; $i++) {
        $busyPorts = @()
        foreach ($port in $Ports) {
            $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                Where-Object { $_.OwningProcess -gt 0 }
            if ($connections) {
                $busyPorts += $port
            }
        }

        if ($busyPorts.Count -eq 0) {
            return
        }

        Start-Sleep -Seconds 1
    }

    Write-Warning "Ports still busy after waiting: $($Ports -join ', ')"
}

function Ensure-Venv {
    if (Test-Path $pythonExe) {
        return
    }

    $bootstrapPython = Get-Command py -ErrorAction SilentlyContinue
    if ($bootstrapPython) {
        & py -3 -m venv $venvDir
    } else {
        $systemPython = Get-Command python -ErrorAction SilentlyContinue
        if (-not $systemPython) {
            throw "No Python interpreter found. Install Python 3 and rerun the launcher."
        }

        & python -m venv $venvDir
    }

    if (-not (Test-Path $pythonExe)) {
        throw "Failed to create virtual environment at $venvDir"
    }
}

function Ensure-StartupDependencies {
    $missingModules = & $pythonExe -c "import importlib.util; modules=['fastapi','uvicorn','multipart','email_validator','jwt','prometheus_client']; missing=[module for module in modules if importlib.util.find_spec(module) is None]; print(','.join(missing))"
    $missingModules = $missingModules.Trim()

    if (-not $missingModules) {
        return
    }

    $packageMap = @{
        fastapi = "fastapi==0.104.1"
        uvicorn = "uvicorn[standard]==0.24.0"
        multipart = "python-multipart==0.0.6"
        email_validator = "email-validator"
        jwt = "PyJWT==2.11.0"
        prometheus_client = "prometheus-client==0.21.1"
    }

    $packagesToInstall = @()
    foreach ($module in ($missingModules -split ',')) {
        if ($module -and $packageMap.ContainsKey($module)) {
            $packagesToInstall += $packageMap[$module]
        }
    }

    if ($packagesToInstall.Count -gt 0) {
        Write-Host "Installing startup dependencies into .venv..."
        & $pythonExe -m pip install $packagesToInstall
    }
}

function Wait-ForBackendHealth {
    param(
        [System.Diagnostics.Process]$Process
    )

    for ($i = 0; $i -lt 20; $i++) {
        if ($Process -and $Process.HasExited) {
            return $false
        }

        try {
            $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 2
            if ($response.status -eq "healthy") {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    return $false
}

function Start-Backend {
    param(
        [string]$ModuleName
    )

    return Start-Process -FilePath $pythonExe `
        -ArgumentList "-m", "uvicorn", "${ModuleName}:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $backendDir `
        -RedirectStandardOutput $backendStdOutLog `
        -RedirectStandardError $backendStdErrLog `
        -PassThru
}

Ensure-Venv
Ensure-StartupDependencies
Stop-PortListeners -Ports @(8000, 3000)
Wait-ForPortsToClear -Ports @(8000, 3000)
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
foreach ($logFile in @($backendStdOutLog, $backendStdErrLog, $frontendStdOutLog, $frontendStdErrLog)) {
    if (Test-Path $logFile) {
        try {
            Remove-Item $logFile -Force -ErrorAction Stop
        } catch {
            Write-Warning "Could not clear log file ${logFile}: $($_.Exception.Message)"
        }
    }
}

$backendProcess = Start-Backend -ModuleName "main"
Write-Host "Started backend (full app, PID: $($backendProcess.Id))"

$healthy = Wait-ForBackendHealth -Process $backendProcess
if (-not $healthy) {
    Write-Warning "Full backend did not become healthy in time. Falling back to minimal backend."
    try {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction Stop
    } catch {
        Write-Warning "Could not stop full backend PID $($backendProcess.Id): $($_.Exception.Message)"
    }

    $backendProcess = Start-Backend -ModuleName "main_minimal"
    Write-Host "Started backend (minimal app, PID: $($backendProcess.Id))"
    $healthy = Wait-ForBackendHealth -Process $backendProcess
}

if ($healthy) {
    Write-Host "Backend health check passed: $healthUrl"
} else {
    Write-Warning "Backend did not become healthy within timeout."
}

if (Test-Path $frontendServer) {
    $frontendProcess = Start-Process -FilePath $pythonExe `
        -ArgumentList "serve.py" `
        -WorkingDirectory $frontendDir `
        -RedirectStandardOutput $frontendStdOutLog `
        -RedirectStandardError $frontendStdErrLog `
        -PassThru
    Write-Host "Started frontend server (PID: $($frontendProcess.Id))"
    Start-Process $frontendUrl | Out-Null
    Write-Host "Opened frontend: $frontendUrl"
} else {
    Write-Warning "Frontend server script not found at $frontendServer"
}

Write-Host "Dev launcher completed."
