@echo off
:: Copyright 2019 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.
setlocal

:: Ensure that "depot_tools" is somewhere in PATH so this tool can be used
:: standalone (e.g. finding cipd.bat for on-demand Python exports), but allow
:: other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

call "%~dp0\cipd_bin_setup.bat" > nul 2>&1
"%~dp0\.cipd_bin\vpython3.exe" %*
