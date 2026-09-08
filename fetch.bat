@echo off
:: Copyright 2013 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.
setlocal

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: The colon-only lines above are temporary padding. Do not remove them,
:: change their length, or insert anything above them.
::
:: depot_tools checkouts predating crbug.com/542670559 run a version of this
:: script that calls update_depot_tools.bat on its own line. cmd.exe tracks a
:: byte offset into the batch file rather than loading it into memory, so when
:: the update rewrites this file those scripts resume at a stale offset and
:: execute whatever fragment of a line lands there (e.g. "date depot_tools."
:: out of a comment, which then blocks prompting for a new system date). The
:: padding parks every such offset (160..400) inside a run of colons, which is
:: a no-op label no matter which byte you enter it on, so the stale resume
:: falls through to the call below and the update completes cleanly.
::
:: This is only needed for checkouts that have not updated since 2026-08-05,
:: and can be deleted once those are gone.

:: Synchronize the root directory before deferring control back to gclient.py.
:: Abort the script if we failed to update depot_tools.
call "%~dp0\update_depot_tools.bat" %* & IF ERRORLEVEL 1 (exit /b 1) ELSE (GOTO :CALL_FETCH)

:CALL_FETCH

:: Ensure that "depot_tools" is somewhere in PATH so this tool can be used
:: standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

:: Defer control.
call "%~dp0python-bin\python3.bat" "%~dp0\fetch.py" %*
