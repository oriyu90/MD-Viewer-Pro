# MD Viewer Pro — ファイル関連付けの登録 (Windows, 管理者権限不要)。
# HKCU (現在ユーザーのみ) に .md / .markdown を MDViewerPro.exe に関連付ける。
# 使い方: ポータブルZIPを展開した場所で実行する。
#   powershell -ExecutionPolicy Bypass -File windows\register_assoc.ps1
$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
# ZIP配置: <展開先>/MDViewerPro/{ MDViewerPro.exe, windows/*.ps1, ... }
$EXE = Join-Path $ROOT "MDViewerPro.exe"
if (-not (Test-Path $EXE)) { throw "MDViewerPro.exe が見つかりません: $ROOT" }

$ProgID = "MDViewerPro.md"
New-Item -Path "HKCU:\Software\Classes\$ProgID" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgID" -Name "(default)" -Value "Markdown Document (MD Viewer Pro)"
New-Item -Path "HKCU:\Software\Classes\$ProgID\DefaultIcon" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgID\DefaultIcon" -Name "(default)" -Value "`"$EXE`",0"
New-Item -Path "HKCU:\Software\Classes\$ProgID\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgID\shell\open\command" -Name "(default)" -Value "`"$EXE`" `"%1`""

foreach ($ext in @(".md", ".markdown")) {
  New-Item -Path "HKCU:\Software\Classes\$ext\OpenWithProgids" -Force | Out-Null
  New-ItemProperty -Path "HKCU:\Software\Classes\$ext\OpenWithProgids" -Name $ProgID -Value "" -PropertyType String -Force | Out-Null
}

# 「プログラムから開く」候補にも出す (Vista以降の推奨登録)。
New-Item -Path "HKCU:\Software\Classes\Applications\MDViewerPro.exe" -Force | Out-Null
New-Item -Path "HKCU:\Software\Classes\Applications\MDViewerPro.exe\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\Applications\MDViewerPro.exe\shell\open\command" -Name "(default)" -Value "`"$EXE`" `"%1`""
New-Item -Path "HKCU:\Software\Classes\Applications\MDViewerPro.exe\SupportedTypes" -Force | Out-Null
New-ItemProperty -Path "HKCU:\Software\Classes\Applications\MDViewerPro.exe\SupportedTypes" -Name ".md" -Value "" -PropertyType String -Force | Out-Null
New-ItemProperty -Path "HKCU:\Software\Classes\Applications\MDViewerPro.exe\SupportedTypes" -Name ".markdown" -Value "" -PropertyType String -Force | Out-Null

Write-Output "登録しました: $EXE"
Write-Output ".md ファイルを右クリック → プログラムから開く → MD Viewer Pro を選び、"
Write-Output "「常時このアプリを使って開く」にチェックすると標準のアプリになります。"
