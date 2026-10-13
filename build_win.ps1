# MD Viewer Pro — Windows (x64) build script (portable ZIP + GUI installer).
# Requires: 64-bit Python 3.11+ (python.org), Windows 10/11 64-bit, NSIS (makensis).
# 32-bit Windows is NOT supported (Qt6/PySide6 ships no 32-bit binaries).
#
#   powershell -ExecutionPolicy Bypass -File build_win.ps1
#
# Outputs (version read from main.py APP_VERSION):
#   dist-win/MDViewerPro-<ver>-win64-portable.zip
#   dist-win/MDViewerPro-<ver>-win64-Setup.exe  (NSIS, per-user, JA/EN, uninstaller)
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# --- version (single source: main.py APP_VERSION) ---
$VER = ((Select-String -Path 'main.py' -Pattern 'APP_VERSION\s*=\s*\"([^\"]+)\"').Matches[0].Groups[1].Value).Trim()
if (-not $VER) { throw "APP_VERSION not found in main.py" }
Write-Output "Version: $VER"

$PY = "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $PY)) { $PY = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $PY) { throw "Python 3.11+ (64-bit) not found. Install from https://www.python.org/downloads/" }

& $PY -c 'import struct; assert struct.calcsize(chr(80))*8 == 64'
$VENV_PY = "..\build-win64\venv\Scripts\python.exe"
if (-not (Test-Path $VENV_PY)) {
  & $PY -m venv ..\build-win64\venv
}
# NOTE: build-win64\venv lives next to the repo checkout (see docs/Windows版実装書.md).
& $VENV_PY -m pip install -r requirements.txt
# 回帰テスト3本は独自ランナー形式 (pytest収集対象外) のため直接実行する
$env:QT_QPA_PLATFORM = "offscreen"
& $VENV_PY 資料箱/tests/test_pure_functions.py
& $VENV_PY 資料箱/tests/test_qt_widgets.py
& $VENV_PY 資料箱/tests/test_integration.py
& $VENV_PY -m PyInstaller MDViewerPro_win.spec --noconfirm --clean

$STAGE = "dist-win\portable\MDViewerPro"
New-Item -ItemType Directory -Force $STAGE | Out-Null
Copy-Item -Recurse -Force "dist\MDViewerPro\*" $STAGE
Copy-Item -Force "windows\FIRST_LAUNCH_WINDOWS.txt" "$STAGE\FIRST_LAUNCH_WINDOWS.txt"
New-Item -ItemType Directory -Force "$STAGE\windows" | Out-Null
Copy-Item -Force "windows\register_assoc.ps1", "windows\unregister_assoc.ps1" "$STAGE\windows\"

$ZIP = "dist-win\MDViewerPro-$VER-win64-portable.zip"
if (Test-Path $ZIP) { Remove-Item $ZIP }
Compress-Archive -Path "$STAGE\*" -DestinationPath $ZIP
Get-FileHash $ZIP -Algorithm SHA256 | Format-List
Write-Output "Built: $ZIP"

# --- NSIS GUI installer (per-user, JA/EN, uninstaller, file assoc option) ---
$MAKENSIS = "C:\Program Files (x86)\NSIS\makensis.exe"
if (-not (Test-Path $MAKENSIS)) {
  $cmd = Get-Command makensis -ErrorAction SilentlyContinue
  if ($cmd) { $MAKENSIS = $cmd.Source }
}
if (-not (Test-Path $MAKENSIS)) {
  Write-Warning "makensis not found; skipping Setup.exe (ZIP only). Install NSIS to build the installer."
  exit 0
}
$env:MDV_VERSION = $VER
$env:MDV_STAGE = (Resolve-Path $STAGE).Path
$env:MDV_OUT = (Join-Path (Resolve-Path "dist-win").Path "MDViewerPro-$VER-win64-Setup.exe")
& $MAKENSIS "/DVERSION=$VER" "/DSTAGE=$($env:MDV_STAGE)" "/DOUTFILE=$($env:MDV_OUT)" windows\installer.nsi
if ($LASTEXITCODE -ne 0) { throw "makensis failed with exit code $LASTEXITCODE" }
if (-not (Test-Path $env:MDV_OUT)) { throw "Setup.exe not created: $($env:MDV_OUT)" }
Get-FileHash $env:MDV_OUT -Algorithm SHA256 | Format-List
Write-Output "Built: $($env:MDV_OUT)"
