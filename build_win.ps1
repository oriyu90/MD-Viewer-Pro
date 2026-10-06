# MD Viewer Pro — Windows (x64) portable build script.
# Requires: 64-bit Python 3.11+ (python.org), Windows 10/11 64-bit.
# 32-bit Windows is NOT supported (Qt6/PySide6 ships no 32-bit binaries).
#
#   powershell -ExecutionPolicy Bypass -File build_win.ps1
#
# Output: dist-win/MDViewerPro-1.4.7-win64-portable.zip
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

$PY = "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $PY)) { $PY = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $PY) { throw "Python 3.11+ (64-bit) not found. Install from https://www.python.org/downloads/" }

& $PY -c "import struct; assert struct.calcsize('P')*8 -eq 64, 'requires 64-bit Python'"
if (-not (Test-Path "build-win64\venv")) {
  & $PY -m venv ..\build-win64\venv
}
# NOTE: build-win64\venv lives next to the repo checkout (see docs/Windows版実装書.md).
& ..\build-win64\venv\Scripts\python -m pip install -r requirements.txt
# 回帰テスト3本は独自ランナー形式 (pytest収集対象外) のため直接実行する
$env:QT_QPA_PLATFORM = "offscreen"
& ..\build-win64\venv\Scripts\python 資料箱/tests/test_pure_functions.py
& ..\build-win64\venv\Scripts\python 資料箱/tests/test_qt_widgets.py
& ..\build-win64\venv\Scripts\python 資料箱/tests/test_integration.py
& ..\build-win64\venv\Scripts\pyinstaller MDViewerPro_win.spec --noconfirm --clean

$STAGE = "dist-win\portable\MDViewerPro"
New-Item -ItemType Directory -Force $STAGE | Out-Null
Copy-Item -Recurse -Force "dist\MDViewerPro\*" $STAGE
Copy-Item -Force "windows\FIRST_LAUNCH_WINDOWS.txt" "$STAGE\FIRST_LAUNCH_WINDOWS.txt"
New-Item -ItemType Directory -Force "$STAGE\windows" | Out-Null
Copy-Item -Force "windows\register_assoc.ps1", "windows\unregister_assoc.ps1" "$STAGE\windows\"

$ZIP = "dist-win\MDViewerPro-1.4.7-win64-portable.zip"
if (Test-Path $ZIP) { Remove-Item $ZIP }
Compress-Archive -Path "$STAGE\*" -DestinationPath $ZIP
Get-FileHash $ZIP -Algorithm SHA256 | Format-List
Write-Output "Built: $ZIP"
