@echo off
:: Copyright 2017 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

setlocal

set "ROOT=%~dp0\.cipd_bin"
set "ENSURE=%~dp0\cipd_manifest.txt"
set "CACHE_DIR=%ROOT%\.cipd\tmp"
set "CACHED_ENSURE=%CACHE_DIR%\.cipd_manifest.txt"
set "CACHED_VERSIONS=%CACHE_DIR%\.cipd_manifest.versions"
set "CACHED_CLIENT=%CACHE_DIR%\.cipd_client_version"

:: CIPD ensure is slow (hundreds of milliseconds). We cache the result by
:: storing copies of the input files and comparing them on subsequent runs.
:: We use `fc` (content-based) instead of `mtime` comparison to avoid
:: false-positive cache misses on CI bots where git checkouts reset mtimes.
:: Cache files live in `.cipd\tmp`, which `cipd ensure` automatically removes
:: whenever it modifies packages (even if invoked by an older checkout's
:: `cipd_bin_setup.bat` that predates this cache).
if not exist "%CACHED_ENSURE%" goto :RUN_CIPD
fc /b "%ENSURE%" "%CACHED_ENSURE%" >nul 2>&1
if errorlevel 1 goto :RUN_CIPD
fc /b "%~dp0\cipd_manifest.versions" "%CACHED_VERSIONS%" >nul 2>&1
if errorlevel 1 goto :RUN_CIPD
fc /b "%~dp0\cipd_client_version" "%CACHED_CLIENT%" >nul 2>&1
if errorlevel 1 goto :RUN_CIPD

goto :SKIP_CIPD

:RUN_CIPD
rmdir /s /q "%CACHE_DIR%" >nul 2>&1
del /f /q "%ROOT%\.cipd_manifest.txt" "%ROOT%\.cipd_manifest.versions" "%ROOT%\.cipd_client_version" >nul 2>&1
call "%~dp0\cipd.bat" ensure -log-level warning -ensure-file "%ENSURE%" -root "%ROOT%"
if errorlevel 1 exit /b %ERRORLEVEL%

mkdir "%CACHE_DIR%" >nul 2>&1
copy /y "%ENSURE%" "%CACHED_ENSURE%" >nul 2>&1
copy /y "%~dp0\cipd_manifest.versions" "%CACHED_VERSIONS%" >nul 2>&1
copy /y "%~dp0\cipd_client_version" "%CACHED_CLIENT%" >nul 2>&1

:SKIP_CIPD
endlocal
exit /b 0
