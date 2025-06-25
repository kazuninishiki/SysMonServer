# System Monitor Dashboard - Windows Installation Script
# PowerShell script for easy setup and launch

param(
    [switch]$SkipInstall,
    [switch]$RunOnly,
    [int]$Port = 9876,
    [int]$Interval = 1000
)

$ErrorActionPreference = "Stop"

function Write-Header {
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                   System Monitor Dashboard                    ║" -ForegroundColor Cyan
    Write-Host "║                     Windows Installer                        ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Test-PythonInstallation {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -eq 3 -and $minor -ge 7) {
                Write-Host "✓ Python $pythonVersion found" -ForegroundColor Green
                return $true
            }
        }
        Write-Host "✗ Python 3.7+ required. Found $pythonVersion" -ForegroundColor Red
        return $false
    }
    catch {
        Write-Host "✗ Python not found. Please install Python 3.7+ from https://python.org" -ForegroundColor Red
        return $false
    }
}

function Install-Dependencies {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    try {
        python -m pip install --upgrade pip
        python -m pip install -r requirements.txt
        Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ Failed to install dependencies. Error $_" -ForegroundColor Red
        return $false
    }
}

function Test-Dependencies {
    Write-Host "Checking dependencies..." -ForegroundColor Yellow
    $required = @("flask", "flask-socketio", "psutil", "pynvml", "python-socketio", "eventlet")
    $missing = @()
    
    foreach ($package in $required) {
        try {
            python -c "import $($package.Replace('-', '_'))" 2>$null
            Write-Host "  ✓ $package" -ForegroundColor Green
        }
        catch {
            Write-Host "  ✗ $package" -ForegroundColor Red
            $missing += $package
        }
    }
    
    return $missing.Count -eq 0
}

function Start-Server {
    param([int]$ServerPort, [int]$UpdateInterval)
    
    Write-Host "Starting System Monitor Dashboard..." -ForegroundColor Yellow
    Write-Host "Server will be available at http://localhost:$ServerPort" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    Write-Host ""
    
    try {
        python run.py --port $ServerPort --interval $UpdateInterval
    }
    catch {
        Write-Host "✗ Failed to start server. Error $_" -ForegroundColor Red
        exit 1
    }
}

function Show-Usage {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\install.ps1                    # Full install and run"
    Write-Host "  .\install.ps1 -SkipInstall       # Skip dependency installation"
    Write-Host "  .\install.ps1 -RunOnly           # Only run the server"
    Write-Host "  .\install.ps1 -Port 8080         # Use custom port"
    Write-Host "  .\install.ps1 -Interval 500      # 500ms update interval"
    Write-Host ""
}

# Main execution
Write-Header

if ($RunOnly) {
    if (Test-Path "main.py") {
        Start-Server -ServerPort $Port -UpdateInterval $Interval
    } else {
        Write-Host "✗ main.py not found. Run without -RunOnly to install first." -ForegroundColor Red
        exit 1
    }
    exit 0
}

# Check Python installation
if (-not (Test-PythonInstallation)) {
    Write-Host ""
    Write-Host "Please install Python 3.7+ and try again." -ForegroundColor Yellow
    Show-Usage
    exit 1
}

# Install dependencies unless skipped
if (-not $SkipInstall) {
    if (-not (Install-Dependencies)) {
        Write-Host ""
        Write-Host "Installation failed. Please check the error messages above." -ForegroundColor Red
        Show-Usage
        exit 1
    }
} else {
    if (-not (Test-Dependencies)) {
        Write-Host ""
        Write-Host "Some dependencies are missing. Run without -SkipInstall to install them." -ForegroundColor Yellow
        Show-Usage
        exit 1
    }
}

# Check if main files exist
if (-not (Test-Path "main.py")) {
    Write-Host "✗ main.py not found. Please ensure all files are in the current directory." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "run.py")) {
    Write-Host "✗ run.py not found. Please ensure all files are in the current directory." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Installation completed successfully!" -ForegroundColor Green
Write-Host ""

# Start the server
Start-Server -ServerPort $Port -UpdateInterval $Interval
