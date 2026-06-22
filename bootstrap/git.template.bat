@echo off
setlocal
if not defined EDITOR set EDITOR=notepad
:: Exclude the current directory when searching for executables.
:: This is required for the SSO helper to run, which is written in Go.
:: Without this set, the SSO helper may throw an error when resolving
:: the `git` command (see https://pkg.go.dev/os/exec for more details).
set "NoDefaultCurrentDirectoryInExePath=1"
set "PATH=${GIT_PATH_PREPEND};%~dp0;%PATH%"
"${GIT_PROGRAM}" %*
