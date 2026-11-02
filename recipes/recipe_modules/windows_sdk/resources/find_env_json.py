#!/usr/bin/env python3
# Copyright 2021 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
This script finds the SetEnv.*.json file from an unpacked Windows SDK.
"""

from __future__ import annotations

import argparse
import json
import ntpath
import os
import re
import sys
from typing import Any

POSSIBLE_BASE_LOCATIONS: list[str] = [
  # SDK versions 10.0.19041.0 and later
  os.path.join("Windows Kits", "10", "bin"),
  # Older SDKs used the legacy win_sdk/bin directory
  os.path.join("win_sdk", "bin"),
]

SDK_ARCHITECTURES: frozenset[str] = frozenset(
  [
    "x86",
    "x64",
    "arm64",
  ]
)


def _resolve_within_root(path: str, real_sdk_root: str) -> str | None:
  """Resolves `path` and returns its canonical path if within `real_sdk_root`.

  Returns None if `path` resolves outside `real_sdk_root` (or to the root
  directory itself).
  """
  real_path = os.path.realpath(path)
  try:
    common = os.path.commonpath([real_sdk_root, real_path])
  except ValueError:
    return None
  norm_root = os.path.normcase(real_sdk_root)
  if os.path.normcase(common) != norm_root:
    return None
  if os.path.normcase(real_path) == norm_root:
    return None
  return real_path


def _is_valid_rel_part(part: str) -> bool:
  """Returns True if `part` is a safe relative path component."""
  if not part or "\x00" in part:
    return False
  if ntpath.splitdrive(part)[0] or part.startswith(("/", "\\")):
    return False
  subparts = [p for p in re.split(r"[\\/]+", part) if p]
  return bool(subparts) and ".." not in subparts


def _validate_setenv_data(data: Any) -> None:
  """Validates that parsed SetEnv JSON matches the schema expected by api.py."""
  if not isinstance(data, dict):
    raise ValueError("root JSON value must be an object")
  env = data.get("env")
  if not isinstance(env, dict):
    raise ValueError("missing or invalid 'env' mapping")

  for key, entries in env.items():
    if not isinstance(key, str) or not key:
      raise ValueError("environment variable name must be a non-empty string")
    if not isinstance(entries, list):
      raise ValueError(
        f"entries for {key!r} must be a list, got {type(entries).__name__}"
      )
    for entry in entries:
      if not isinstance(entry, list) or not entry:
        raise ValueError(
          f"each path entry for {key!r} must be a non-empty list"
        )
      if not all(isinstance(p, str) and p for p in entry):
        raise ValueError(
          f"path components for {key!r} must be non-empty strings"
        )
      if entry[0] == "..":
        if len(entry) < 2 or entry[1] not in ("..", "..\\"):
          raise ValueError(f"invalid relative prefix in {key!r}: {entry!r}")
        tail = entry[2:]
      else:
        tail = entry

      for part in tail:
        if not _is_valid_rel_part(part):
          raise ValueError(f"invalid path component {part!r} in {key!r}")


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Find the SetEnv from a windows SDK"
  )
  parser.add_argument(
    "--sdk_root",
    metavar="PATH",
    required=True,
    help="The absolute path to the root of the unpacked SDK",
  )
  parser.add_argument(
    "--target_arch",
    choices=SDK_ARCHITECTURES,
    required=True,
    help="The target architecture",
  )
  parser.add_argument(
    "--output_json",
    required=True,
    help="The absolute path to an output json file",
  )
  args = parser.parse_args()

  if not os.path.isabs(args.sdk_root):
    parser.error(f"sdk_root must be absolute, got {args.sdk_root!r}")

  if not os.path.isabs(args.output_json):
    parser.error(f"output_json must be absolute, got {args.output_json!r}")

  real_sdk_root = os.path.realpath(args.sdk_root)
  found_by_loc: dict[str, dict[str, tuple[str, str]]] = {}
  for loc in POSSIBLE_BASE_LOCATIONS:
    for arch in sorted(SDK_ARCHITECTURES):
      cand = os.path.join(args.sdk_root, loc, f"SetEnv.{arch}.json")
      if arch == args.target_arch:
        print(f"Attempting: {cand}")
      if not os.path.lexists(cand):
        if arch == args.target_arch:
          print(">  Not found")
        continue
      real_cand = _resolve_within_root(cand, real_sdk_root)
      if real_cand is None:
        print(
          f"SetEnv candidate {cand!r} resolves outside sdk_root "
          f"{args.sdk_root!r}",
          file=sys.stderr,
        )
        sys.exit(1)
      if not os.path.isfile(real_cand):
        print(
          f"SetEnv candidate {cand!r} is not a regular file",
          file=sys.stderr,
        )
        sys.exit(1)
      if arch == args.target_arch:
        print(">  Found it!")
      found_by_loc.setdefault(loc, {})[arch] = (cand, real_cand)

  if len(found_by_loc) > 1:
    # Legitimate SDK packages ship SetEnv files in only one location.
    all_found = [
      pair[0]
      for arch_map in found_by_loc.values()
      for pair in arch_map.values()
    ]
    print(
      f"Multiple SetEnv files found; SDK root is ambiguous: {all_found}",
      file=sys.stderr,
    )
    sys.exit(1)

  target_entry: tuple[str, str] | None = None
  if found_by_loc:
    only_arch_map = next(iter(found_by_loc.values()))
    target_entry = only_arch_map.get(args.target_arch)

  if target_entry is None:
    print("Unable to locate SetEnv file", file=sys.stderr)
    sys.exit(1)

  target_file, real_target = target_entry
  try:
    with open(real_target, "r", encoding="utf-8") as set_env_json:
      content = set_env_json.read()
    data = json.loads(content)
    _validate_setenv_data(data)
    with open(args.output_json, "w", encoding="utf-8") as outf:
      outf.write(content)
  except (OSError, ValueError) as ex:
    print(
      f"Failed to read or validate {target_file!r}: {ex}",
      file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
  main()
