; NSIS installer hooks (see bundle.windows.nsis.installerHooks in tauri.conf.json).

; Releases up to 3.0.x shipped the server as a single file, installed next to the
; application. It is now a folder, so an upgrade would leave that old executable
; behind (about 58 MB, unused). Remove exactly that file, by its exact name.
; Delete does not set the error flag when the file does not exist, and nothing
; is removed on uninstall.
!macro NSIS_HOOK_POSTINSTALL
  Delete "$INSTDIR\fitstats-server.exe"
!macroend
