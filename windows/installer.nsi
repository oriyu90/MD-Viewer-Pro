; MD Viewer Pro — Windows GUI installer (NSIS 3, per-user, JA/EN).
; Build via build_win.ps1:
;   makensis /DVERSION=1.5.3 /DSTAGE=C:\...\dist-win\portable\MDViewerPro /DOUTFILE=C:\...\dist-win\MDViewerPro-1.5.3-win64-Setup.exe windows\installer.nsi
; Design notes (safe defaults):
; - Per-user install (%LOCALAPPDATA%\Programs\MDViewerPro), RequestExecutionLevel user.
;   No admin rights required, no machine-wide changes, clean uninstall.
; - Registry writes are HKCU only. File association (.md/.markdown) is an
;   OPTIONAL section (default unchecked) so the installer never hijacks
;   associations without explicit consent. Single-instance exe reuses the
;   running app when a document is opened from an association.
; - Unsigned build: SmartScreen may appear on first run. This is documented
;   (FIRST_LAUNCH_WINDOWS.txt, README, website) — never claim otherwise.

Unicode True
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 64

!ifndef VERSION
  !define VERSION "1.5.3"
!endif
!ifndef STAGE
  !define STAGE "dist-win\portable\MDViewerPro"
!endif
!ifndef OUTFILE
  !define OUTFILE "dist-win\MDViewerPro-${VERSION}-win64-Setup.exe"
!endif

Name "MD Viewer Pro ${VERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\MDViewerPro"
InstallDirRegKey HKCU "Software\MDViewerPro" "InstallDir"
Icon "..\favicon.ico"
UninstallIcon "..\favicon.ico"

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "MD Viewer Pro"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "CompanyName" "Yuki_Orita"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "(c) 2026 Yuki_Orita (MIT License)"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "..\favicon.ico"
!define MUI_UNICON "..\favicon.ico"
!define MUI_LANGDLL_ALLLANGUAGES

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\MDViewerPro.exe"
!define MUI_FINISHPAGE_RUN_TEXT "$(MUI_TEXT_FINISH_RUN)"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Japanese"
!insertmacro MUI_LANGUAGE "English"

; --- language strings ---
LangString DESC_Main ${LANG_JAPANESE} "MD Viewer Pro 本体 (必須)"
LangString DESC_Main ${LANG_ENGLISH} "MD Viewer Pro application (required)"
LangString DESC_Shortcuts ${LANG_JAPANESE} "スタートメニューとデスクトップにショートカットを作成"
LangString DESC_Shortcuts ${LANG_ENGLISH} "Create Start Menu and Desktop shortcuts"
LangString DESC_Assoc ${LANG_JAPANESE} ".md / .markdown を MD Viewer Pro に関連付け (現在のユーザーのみ、管理者権限不要)"
LangString DESC_Assoc ${LANG_ENGLISH} "Associate .md / .markdown with MD Viewer Pro (current user only, no admin needed)"
LangString MUI_TEXT_FINISH_RUN ${LANG_JAPANESE} "MD Viewer Pro を実行する"
LangString MUI_TEXT_FINISH_RUN ${LANG_ENGLISH} "Run MD Viewer Pro"
LangString TEXT_UNINSTALL_CONFIRM ${LANG_JAPANESE} "MD Viewer Pro をアンインストールしますか？設定 (%APPDATA%\\MDViewerPro) は残ります。"
LangString TEXT_UNINSTALL_CONFIRM ${LANG_ENGLISH} "Uninstall MD Viewer Pro? Settings (%APPDATA%\\MDViewerPro) will be kept."
LangString TEXT_ASSOC_DONE ${LANG_JAPANESE} "関連付けを登録しました。"
LangString TEXT_ASSOC_DONE ${LANG_ENGLISH} "File association registered."

Function .onInit
  !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

Function un.onInit
  !insertmacro MUI_UNGETLANGUAGE
FunctionEnd

Section "$(DESC_Main)" SEC_Main
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "${STAGE}\*.*"
  WriteRegStr HKCU "Software\MDViewerPro" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\MDViewerPro" "Version" "${VERSION}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "DisplayName" "MD Viewer Pro ${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "Publisher" "Yuki_Orita"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "URLInfoAbout" "https://github.com/oriyu90/MD-Viewer-Pro"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "NoModify" "1"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "NoRepair" "1"
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro" "EstimatedSize" "$0"
SectionEnd

Section "$(DESC_Shortcuts)" SEC_Shortcuts
  CreateDirectory "$SMPROGRAMS\MD Viewer Pro"
  CreateShortcut "$SMPROGRAMS\MD Viewer Pro\MD Viewer Pro.lnk" "$INSTDIR\MDViewerPro.exe"
  CreateShortcut "$SMPROGRAMS\MD Viewer Pro\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\MD Viewer Pro.lnk" "$INSTDIR\MDViewerPro.exe"
SectionEnd

Section /o "$(DESC_Assoc)" SEC_Assoc
  ; ProgID + HKCU association (same layout as windows\register_assoc.ps1)
  WriteRegStr HKCU "Software\Classes\MDViewerPro.md" "" "Markdown Document (MD Viewer Pro)"
  WriteRegStr HKCU "Software\Classes\MDViewerPro.md\DefaultIcon" "" '"$INSTDIR\MDViewerPro.exe",0'
  WriteRegStr HKCU "Software\Classes\MDViewerPro.md\shell\open\command" "" '"$INSTDIR\MDViewerPro.exe" "%1"'
  WriteRegStr HKCU "Software\Classes\.md\OpenWithProgids" "MDViewerPro.md" ""
  WriteRegStr HKCU "Software\Classes\.markdown\OpenWithProgids" "MDViewerPro.md" ""
  WriteRegStr HKCU "Software\Classes\Applications\MDViewerPro.exe\shell\open\command" "" '"$INSTDIR\MDViewerPro.exe" "%1"'
  WriteRegStr HKCU "Software\Classes\Applications\MDViewerPro.exe\SupportedTypes" ".md" ""
  WriteRegStr HKCU "Software\Classes\Applications\MDViewerPro.exe\SupportedTypes" ".markdown" ""
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_Main} $(DESC_Main)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_Shortcuts} $(DESC_Shortcuts)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_Assoc} $(DESC_Assoc)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  ; Silent uninstall (/S) must not prompt (enterprise/scripted removal).
  ; Interactive uninstall keeps the confirmation.
  IfSilent +3
    MessageBox MB_OKCANCEL|MB_ICONQUESTION "$(TEXT_UNINSTALL_CONFIRM)" IDOK +2
      Abort
  ; Remove association only if it points to this install (never touch foreign settings)
  ReadRegStr $0 HKCU "Software\Classes\MDViewerPro.md\shell\open\command" ""
  ${If} $0 == '"$INSTDIR\MDViewerPro.exe" "%1"'
    DeleteRegKey HKCU "Software\Classes\MDViewerPro.md"
    DeleteRegValue HKCU "Software\Classes\.md\OpenWithProgids" "MDViewerPro.md"
    DeleteRegValue HKCU "Software\Classes\.markdown\OpenWithProgids" "MDViewerPro.md"
    DeleteRegKey HKCU "Software\Classes\Applications\MDViewerPro.exe"
  ${EndIf}
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MDViewerPro"
  DeleteRegKey HKCU "Software\MDViewerPro"
  Delete "$SMPROGRAMS\MD Viewer Pro\MD Viewer Pro.lnk"
  Delete "$SMPROGRAMS\MD Viewer Pro\Uninstall.lnk"
  RMDir "$SMPROGRAMS\MD Viewer Pro"
  Delete "$DESKTOP\MD Viewer Pro.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
