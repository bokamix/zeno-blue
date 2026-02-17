# ZENO Windows installer
# powershell -c "irm https://raw.githubusercontent.com/bokamix/zeno-blue/main/install.ps1 | iex"
$ErrorActionPreference = "Stop"

$ZENO_HOME = "$env:USERPROFILE\.zeno"
$ZENO_APP = "$ZENO_HOME\app"
$ZENO_BIN = "$ZENO_HOME\bin"
$ZIP_URL = "https://github.com/bokamix/zeno-blue/archive/refs/heads/main.zip"

Write-Host ""
Write-Host "  ███████╗███████╗███╗   ██╗ ██████╗ "
Write-Host "  ╚══███╔╝██╔════╝████╗  ██║██╔═══██╗"
Write-Host "    ███╔╝ █████╗  ██╔██╗ ██║██║   ██║"
Write-Host "   ███╔╝  ██╔══╝  ██║╚██╗██║██║   ██║"
Write-Host "  ███████╗███████╗██║ ╚████║╚██████╔╝"
Write-Host "  ╚══════╝╚══════╝╚═╝  ╚═══╝ ╚═════╝ "
Write-Host ""
Write-Host "  Installer (Windows)" -ForegroundColor White
Write-Host ""

# --- Install uv (Python manager) ---
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    $uvVersion = & uv --version 2>$null
    Write-Host "  uv:      $uvVersion" -ForegroundColor Green
} else {
    Write-Host "  Installing uv (Python manager)..." -ForegroundColor White
    try {
        irm https://astral.sh/uv/install.ps1 | iex
        # Refresh PATH
        $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
        $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uvCmd) { throw "uv not found after install" }
        Write-Host "  uv:      $(& uv --version)" -ForegroundColor Green
    } catch {
        Write-Host "  Failed to install uv." -ForegroundColor Red
        Write-Host "  Install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

# --- Check Node.js/npm ---
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($npmCmd) {
    $nodeVersion = & node --version 2>$null
    Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "  Node.js: not found (needed for frontend build on first run)" -ForegroundColor Yellow
    Write-Host "           Install later: https://nodejs.org/"
}

Write-Host ""

# --- Download and extract ---
Write-Host "  Downloading ZENO..." -ForegroundColor White

$tmpZip = Join-Path $env:TEMP "zeno-install-$(Get-Random).zip"
$tmpDir = Join-Path $env:TEMP "zeno-extract-$(Get-Random)"

try {
    Invoke-WebRequest -Uri $ZIP_URL -OutFile $tmpZip -UseBasicParsing
} catch {
    Write-Host "  Download failed: $_" -ForegroundColor Red
    exit 1
}

# Remove old app code (user data in .env, data/, workspace/ is preserved)
if (Test-Path $ZENO_APP) { Remove-Item $ZENO_APP -Recurse -Force }
New-Item -ItemType Directory -Path $ZENO_APP -Force | Out-Null

# Extract zip
Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force
# Move contents from nested folder (zeno-blue-main/) to app/
$nested = Get-ChildItem $tmpDir | Select-Object -First 1
Copy-Item "$($nested.FullName)\*" $ZENO_APP -Recurse -Force
Remove-Item $tmpDir -Recurse -Force
Remove-Item $tmpZip -Force

Write-Host "  Installed to ~\.zeno\app\" -ForegroundColor Green

# --- Create launcher (zeno.cmd) ---
New-Item -ItemType Directory -Path $ZENO_BIN -Force | Out-Null

$launcherContent = @'
@echo off
setlocal
set "ZENO_APP=%USERPROFILE%\.zeno\app"
set "TARBALL_URL=https://github.com/bokamix/zeno-blue/archive/refs/heads/main.zip"

if "%~1"=="update" goto :update
goto :run

:update
echo.
echo   Updating ZENO...
set "TMPZIP=%TEMP%\zeno-update-%RANDOM%.zip"
set "TMPDIR=%TEMP%\zeno-extract-%RANDOM%"
powershell -Command "try { Invoke-WebRequest -Uri '%TARBALL_URL%' -OutFile '%TMPZIP%' -UseBasicParsing } catch { Write-Host '  Download failed' -ForegroundColor Red; exit 1 }"
if errorlevel 1 (
    echo   Download failed.
    exit /b 1
)
if exist "%ZENO_APP%\frontend\node_modules" (
    move "%ZENO_APP%\frontend\node_modules" "%TEMP%\_zeno_node_modules" >nul 2>&1
)
rmdir /s /q "%ZENO_APP%" 2>nul
mkdir "%ZENO_APP%"
powershell -Command "Expand-Archive -Path '%TMPZIP%' -DestinationPath '%TMPDIR%' -Force; $n = Get-ChildItem '%TMPDIR%' | Select-Object -First 1; Copy-Item \"$($n.FullName)\*\" '%ZENO_APP%' -Recurse -Force; Remove-Item '%TMPDIR%' -Recurse -Force; Remove-Item '%TMPZIP%' -Force"
if exist "%TEMP%\_zeno_node_modules" (
    move "%TEMP%\_zeno_node_modules" "%ZENO_APP%\frontend\node_modules" >nul 2>&1
)
where npm >nul 2>&1
if not errorlevel 1 (
    if exist "%ZENO_APP%\frontend\package.json" (
        echo   Building frontend...
        cd /d "%ZENO_APP%\frontend" && npm install --silent 2>nul && npm run build --silent 2>nul
        echo   Frontend ready.
    )
)
echo   ZENO updated!
echo.
goto :eof

:run
uv run --python 3.12 "%ZENO_APP%\zeno.py" %*
'@

Set-Content -Path "$ZENO_BIN\zeno.cmd" -Value $launcherContent -Encoding ASCII

Write-Host ""

# --- Add to PATH ---
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*\.zeno\bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$ZENO_BIN;$currentPath", "User")
    $env:Path = "$ZENO_BIN;$env:Path"
    Write-Host "  Added to user PATH" -ForegroundColor Green
}

# --- Done ---
Write-Host ""
Write-Host "  ZENO installed!" -ForegroundColor Green
Write-Host ""
Write-Host "  Run:    " -NoNewline; Write-Host "zeno" -ForegroundColor White
Write-Host "  Update: " -NoNewline; Write-Host "zeno update" -ForegroundColor White
Write-Host ""
Write-Host "  Restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
Write-Host ""
