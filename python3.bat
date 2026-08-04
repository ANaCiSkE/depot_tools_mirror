@echo off
:: Copyright 2026 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

setlocal
set "ROOT_DIR=%~dp0."
for %%d in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fd"

:: Forward directly to the hermetic CIPD CPython wrapper unless
:: DEPOT_TOOLS_PYTHON_BYPASS is set to a non-zero value, in which case
:: we fall back to locating a system-installed python3/python executable.
if defined DEPOT_TOOLS_PYTHON_BYPASS if not "%DEPOT_TOOLS_PYTHON_BYPASS%"=="" if not "%DEPOT_TOOLS_PYTHON_BYPASS%"=="0" goto :BYPASS

if not exist "%ROOT_DIR%\python3_bin_reldir.txt" (
  echo depot_tools: Error: python3_bin_reldir.txt not found. Initialize depot_tools by running gclient or update_depot_tools. >&2
  exit /b 1
)

for /f %%i in (%ROOT_DIR%\python3_bin_reldir.txt) do set "PYTHON_BIN_ABSDIR=%ROOT_DIR%\%%i"
set "PATH=%PYTHON_BIN_ABSDIR%;%PYTHON_BIN_ABSDIR%\Scripts;%PATH%"
"%PYTHON_BIN_ABSDIR%\python3.exe" %*
exit /b %ERRORLEVEL%

:BYPASS
:: Note: Filter out executables located under %ROOT_DIR% by combining
:: where.exe and findstr.exe so CIPD python directories are ignored.
for /f "delims=" %%i in ('where.exe python3.exe python.exe 2^>nul ^| findstr.exe /i /v /c:"%ROOT_DIR%"') do (
  set "SYS_PYTHON=%%~fi"
  goto :RUN_SYS_PYTHON
)
echo depot_tools: Error: System python3/python not found in PATH (bypass enabled). >&2
exit /b 1

:RUN_SYS_PYTHON
"%SYS_PYTHON%" %*
exit /b %ERRORLEVEL%
