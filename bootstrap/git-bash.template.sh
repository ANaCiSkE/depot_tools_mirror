#!/usr/bin/env bash
export EDITOR=${EDITOR:=notepad}
WIN_BASE=`dirname $0`
UNIX_BASE=`cygpath "$WIN_BASE"`
export PATH="$PATH:$UNIX_BASE/${PYTHON3_BIN_RELDIR_UNIX}:$UNIX_BASE/${PYTHON3_BIN_RELDIR_UNIX}/Scripts"
export PYTHON_DIRECT=1
export PYTHONUNBUFFERED=1

GIT_BASH_EXE_WIN="${GIT_BASH_EXE}"
GIT_BASH_LAUNCHER_WIN="${GIT_BASH_LAUNCHER}"

if [[ $# > 0 ]]; then
  if [[ -z "$GIT_BASH_EXE_WIN" ]]; then
    echo "git-bash: no bash.exe was configured for this Git installation." >&2
    exit 1
  fi
  "`cygpath "$GIT_BASH_EXE_WIN"`" "$@"
else
  LAUNCHER="$GIT_BASH_LAUNCHER_WIN"
  if [[ -z "$LAUNCHER" ]]; then
    LAUNCHER="$GIT_BASH_EXE_WIN"
  fi
  if [[ -z "$LAUNCHER" ]]; then
    echo "git-bash: no launcher was configured for this Git installation." >&2
    exit 1
  fi
  "`cygpath "$LAUNCHER"`" &
fi
