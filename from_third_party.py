# Copyright 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper module to reliably import bundled dependencies from third_party.

Why this module exists:
External tools and repositories (such as Chromium's PRESUBMIT.py, recipe_engine,
and build scripts) frequently embed depot_tools by appending its directory to the
end of `sys.path`. In those environments, another `third_party` package or directory
(e.g., from a workspace root or virtualenv site-packages) might already be earlier on
`sys.path` or already cached inside `sys.modules['third_party']`.

Standard imports like `from third_party import schema` or `from third_party import colorama`
rely on top-level sys.path resolution. When depot_tools is at the tail of `sys.path`
or `sys.modules['third_party']` is already loaded from elsewhere, those imports fail
with `ImportError` or load conflicting external versions.

By using `importlib.util` to load modules directly from their file paths under
`depot_tools/third_party/` into an isolated namespace (`_depot_tools_third_party_*`),
we guarantee that depot_tools always imports its own bundled third-party dependencies
without namespace collisions or relying on sys.path ordering.

Usage:
  import from_third_party
  colorama = from_third_party.import_module('colorama')
  schema = from_third_party.import_module('schema')
  Progress = from_third_party.import_module('repo.progress').Progress
"""

import importlib.util
import os
import sys

_THIRD_PARTY_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "third_party"
)


def import_module(module_path):
    """Imports a module or dotted sub-module from depot_tools/third_party.

    Args:
        module_path: Dotted module path under third_party (e.g. 'schema',
                     'colorama', or 'repo.progress').

    Returns:
        The loaded module object.
    """
    parts = module_path.split(".")
    cur_dir = _THIRD_PARTY_ROOT
    cur_name = "_depot_tools_third_party"
    parent = None

    for part in parts:
        cur_name = (
            f"{cur_name}.{part}"
            if parent
            else f"_depot_tools_third_party_{part}"
        )
        if cur_name in sys.modules:
            parent = sys.modules[cur_name]
            cur_dir = os.path.join(cur_dir, part)
            continue

        pkg_path = os.path.join(cur_dir, part, "__init__.py")
        file_path = os.path.join(cur_dir, f"{part}.py")
        target_path = pkg_path if os.path.exists(pkg_path) else file_path

        if not os.path.exists(target_path):
            raise ImportError(
                f"Cannot find third_party module {module_path} "
                f"(looked for {target_path})"
            )

        spec = importlib.util.spec_from_file_location(cur_name, target_path)
        if not spec or not spec.loader:
            raise ImportError(
                f"Failed to create spec for {cur_name} from {target_path}"
            )

        mod = importlib.util.module_from_spec(spec)
        sys.modules[cur_name] = mod
        if parent:
            setattr(parent, part, mod)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            if cur_name in sys.modules:
                del sys.modules[cur_name]
            if parent and hasattr(parent, part):
                delattr(parent, part)
            raise
        parent = mod
        cur_dir = os.path.join(cur_dir, part)

    return parent


def get(module_path):
    """Returns the loaded module object if available in sys.modules, else None.

    Args:
        module_path: Dotted module path under third_party (e.g. 'colorama').

    Returns:
        The loaded module object, or None if it has not been imported.
    """
    cur_name = "_depot_tools_third_party"
    for part in module_path.split("."):
        cur_name = (
            f"{cur_name}_{part}"
            if cur_name == "_depot_tools_third_party"
            else f"{cur_name}.{part}"
        )
        if cur_name not in sys.modules:
            return sys.modules.get(module_path) or sys.modules.get(
                f"third_party.{module_path}"
            )
    return sys.modules[cur_name]
