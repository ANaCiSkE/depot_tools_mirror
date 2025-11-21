# Copyright 2025 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess
import sys

_NO_CAFFEINATE_FLAG = '--no-caffeinate'

_HELP_MESSAGE = f"""\
caffeinate:
  {_NO_CAFFEINATE_FLAG}  do not prepend `caffeinate` to ninja command
"""


def call(args, **call_kwargs):
    """Runs a command (via subprocess.call) with `caffeinate` if it's on macOS."""
    if sys.platform == 'darwin':
        if isinstance(args, (str, bytes, os.PathLike)):
            args = [args]
        if '-h' in args or '--help' in args:
            print(_HELP_MESSAGE, file=sys.stderr)
        if _NO_CAFFEINATE_FLAG in args:
            args.remove(_NO_CAFFEINATE_FLAG)
        else:
            args = ['caffeinate'] + args
    return subprocess.call(args, **call_kwargs)
