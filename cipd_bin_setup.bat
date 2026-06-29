@echo off
:: Copyright 2017 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

setlocal

set "ROOT=%~dp0\.cipd_bin"
set "ENSURE=%~dp0\cipd_manifest.txt"
set "CACHED_ENSURE=%ROOT%\.cipd_manifest.txt"
set "CACHED_VERSIONS=%ROOT%\.cipd_manifest.versions"
set "CACHED_CLIENT=%ROOT%\.cipd_client_version"

:: CIPD ensure is slow (hundreds of milliseconds). We cache the result by
:: storing copies of the input files and comparing them on subsequent runs.
:: We use `fc` (content-based) instead of `mtime` comparison to avoid
:: false-positive cache misses on CI bots where git checkouts reset mtimes.
if not exist "%CACHED_ENSURE%" goto :RUN_CIPD
fc /b "%ENSURE%" "%CACHED_ENSURE%" >nul 2>&1
if errorlevel 1 goto :RUN_CIPD
fc /b "%~dp0\cipd_manifest.versions" "%CACHED_VERSIONS%" >nul 2>&1
if errorlevel 1 goto :RUN_CIPD
fc /b "%~dp0\cipd_client_version" "%CACHED_CLIENT%" >nul 2>&1
if errorlevel 1 goto :RUN_CIPD

goto :SKIP_CIPD

:RUN_CIPD
del /f /q "%CACHED_ENSURE%" >nul 2>&1
call "%~dp0\cipd.bat" ensure -log-level warning -ensure-file "%ENSURE%" -root "%ROOT%"
if errorlevel 1 exit /b %ERRORLEVEL%

copy /y "%ENSURE%" "%CACHED_ENSURE%" >nul 2>&1
copy /y "%~dp0\cipd_manifest.versions" "%CACHED_VERSIONS%" >nul 2>&1
copy /y "%~dp0\cipd_client_version" "%CACHED_CLIENT%" >nul 2>&1

:SKIP_CIPD
endlocal
exit /b 0
