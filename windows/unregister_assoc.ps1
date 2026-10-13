# MD Viewer Pro — ファイル関連付けの解除 (register_assoc.ps1 の逆操作)。
#   powershell -ExecutionPolicy Bypass -File windows\unregister_assoc.ps1
$ErrorActionPreference = "Stop"
$ProgID = "MDViewerPro.md"
Remove-Item -Path "HKCU:\Software\Classes\$ProgID" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\Software\Classes\Applications\MDViewerPro.exe" -Recurse -Force -ErrorAction SilentlyContinue
foreach ($ext in @(".md", ".markdown")) {
  Remove-ItemProperty -Path "HKCU:\Software\Classes\$ext\OpenWithProgids" -Name $ProgID -ErrorAction SilentlyContinue
}
Write-Output "解除しました。"
