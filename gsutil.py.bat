@echo off
:: Copyright 2018 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.
setlocal

:: Shall skip automatic update?
IF "%DEPOT_TOOLS_UPDATE%" == "0" GOTO :CALL_GSUTIL

:: Synchronize the root directory before deferring control back to gsutil.py.
:: Abort the script if we failed to update depot_tools.
call "%~dp0update_depot_tools.bat" %* & IF ERRORLEVEL 1 (exit /b 1) ELSE (GOTO :CALL_GSUTIL)

:CALL_GSUTIL
:: Ensure that "depot_tools" is somewhere in PATH so this tool can be used
:: standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

:: Defer control.
python3 "%~dp0gsutil.py" %*
