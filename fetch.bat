@echo off
:: Copyright 2013 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.
setlocal

:: Synchronize the root directory before deferring control back to gclient.py.
:: Abort the script if we failed to update depot_tools.
call "%~dp0\update_depot_tools.bat" %* & IF ERRORLEVEL 1 (exit /b 1) ELSE (GOTO :CALL_FETCH)

:CALL_FETCH

:: Ensure that "depot_tools" is somewhere in PATH so this tool can be used
:: standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

:: Defer control.
call vpython3 "%~dp0\fetch.py" %*
