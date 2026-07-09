#!/usr/bin/env vpython3
#
# [VPYTHON:BEGIN]
# python_version: "3.11"
# wheel: <
#   name: "infra/python/wheels/ruff/${vpython_platform}"
#   version: "version:0.15.17"
# >
# [VPYTHON:END]

# Copyright 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import importlib.util
from importlib.machinery import SourceFileLoader
import os
import unittest
from unittest.mock import patch
import tempfile
import shutil

# Load depot_tools/ruff_chromium directly by file path to avoid naming collision with ruff package in site-packages
test_dir = os.path.dirname(os.path.abspath(__file__))
depot_tools_dir = os.path.dirname(test_dir)
ruff_path = os.path.join(depot_tools_dir, "ruff_chromium")
loader = SourceFileLoader("depot_tools_ruff_chromium", ruff_path)
spec = importlib.util.spec_from_loader("depot_tools_ruff_chromium",
                                       loader,
                                       origin=ruff_path)
assert spec is not None, f"Failed to load spec from {ruff_path}"
depot_tools_ruff = importlib.util.module_from_spec(spec)
loader.exec_module(depot_tools_ruff)

should_use_ruff = depot_tools_ruff.should_use_ruff
ruff_should_format = depot_tools_ruff.ruff_should_format
match_pattern = depot_tools_ruff.match_pattern
translate_args = depot_tools_ruff.translate_args
has_yapf_config = depot_tools_ruff.has_yapf_config


class TestHasYapfConfig(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ruff_test_")
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def write_file(self, rel_path, content=""):
        abs_path = os.path.join(self.test_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return abs_path

    def test_style_yapf_present(self):
        self.write_file(".style.yapf", "")
        self.assertTrue(has_yapf_config("foo.py"))
        self.assertTrue(has_yapf_config("a/b/foo.py"))

    def test_pyproject_toml_with_yapf(self):
        self.write_file("pyproject.toml", "[tool.yapf]\n")
        self.assertTrue(has_yapf_config("foo.py"))

    def test_ruff_only_no_yapf_config(self):
        self.write_file("ruff.toml", 'exclude = ["foo.py"]\n')
        self.assertFalse(has_yapf_config("foo.py"))

    def test_no_config(self):
        self.assertFalse(has_yapf_config("foo.py"))


class TestMatchPattern(unittest.TestCase):

    def test_directory_prefix_match(self):
        self.assertTrue(
            match_pattern("third_party/foo/bar.py", ".", "third_party"))
        self.assertTrue(
            match_pattern("/a/b/third_party/foo.py", "/a/b", "third_party"))
        self.assertFalse(match_pattern("src/foo.py", ".", "third_party"))
        self.assertFalse(
            match_pattern("third_party_test/foo.py", ".", "third_party"))

    def test_filename_glob_match(self):
        self.assertTrue(match_pattern("foo.py", ".", "*.py"))
        self.assertTrue(match_pattern("a/b/foo.py", ".", "*.py"))
        self.assertTrue(match_pattern("a/b/foo_test.py", ".", "*_test.py"))
        self.assertFalse(match_pattern("foo.txt", ".", "*.py"))

    def test_simple_path_glob_match(self):
        self.assertTrue(match_pattern("proto/foo.py", ".", "proto/*.py"))
        self.assertFalse(match_pattern("proto/a/foo.py", ".", "proto/*.py"))
        self.assertTrue(match_pattern("proto/a/foo.py", ".", "proto/*/*.py"))

    def test_double_star_ignored(self):
        self.assertFalse(match_pattern("a/b/foo.py", ".", "**/*.py"))

    def test_anchored_filename(self):
        self.assertTrue(match_pattern("a/foo.py", "a", "/foo.py"))
        self.assertFalse(match_pattern("a/b/foo.py", "a", "/foo.py"))


class TestRuffShouldFormat(unittest.TestCase):

    def test_exclude_directory_in_ruff_toml(self):
        config = b'exclude = ["third_party"]'
        self.assertFalse(
            ruff_should_format("third_party/foo.py", ".", config, False))
        self.assertFalse(
            ruff_should_format("third_party/a/b/foo.py", ".", config, False))
        self.assertTrue(ruff_should_format("src/foo.py", ".", config, False))

    def test_exclude_glob_in_pyproject_toml(self):
        config = b'[tool.ruff]\nexclude = ["*_test.py"]'
        self.assertFalse(ruff_should_format("foo_test.py", ".", config, True))
        self.assertFalse(
            ruff_should_format("a/b/foo_test.py", ".", config, True))
        self.assertTrue(ruff_should_format("foo.py", ".", config, True))

    def test_exclude_relative_path_glob_in_ruff_toml(self):
        config = b'exclude = ["proto/*.py"]'
        self.assertFalse(ruff_should_format("proto/foo.py", ".", config, False))
        self.assertTrue(ruff_should_format("proto/a/foo.py", ".", config,
                                           False))

    def test_include_directory_in_ruff_toml(self):
        config = b'include = ["src"]'
        self.assertTrue(ruff_should_format("src/foo.py", ".", config, False))
        self.assertFalse(ruff_should_format("tests/foo.py", ".", config, False))

    def test_include_and_extend_include_in_pyproject_toml(self):
        config = b'[tool.ruff]\ninclude = ["src/*.py"]\nextend-include = ["tests/*.py"]'
        self.assertTrue(ruff_should_format("src/foo.py", ".", config, True))
        self.assertTrue(ruff_should_format("tests/foo.py", ".", config, True))
        self.assertFalse(ruff_should_format("foo.py", ".", config, True))

    def test_malformed_toml_defaults_to_true(self):
        config = b'invalid toml [][['
        self.assertTrue(ruff_should_format("foo.py", ".", config, False))

    def test_double_star_in_exclude_ignored(self):
        config = b'exclude = ["**/*.py"]'
        self.assertTrue(ruff_should_format("a/b/foo.py", ".", config, False))

    def test_double_star_in_include_ignored(self):
        config = b'include = ["**/*.py"]'
        self.assertFalse(ruff_should_format("a/b/foo.py", ".", config, False))


class TestShouldUseRuffRouting(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ruff_test_")
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def write_file(self, rel_path, content=""):
        abs_path = os.path.join(self.test_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return abs_path

    def test_ruff_toml_only(self):
        self.write_file("ruff.toml", "")
        self.assertTrue(should_use_ruff("foo.py"))

    def test_pyproject_toml_with_ruff(self):
        self.write_file("pyproject.toml", "[tool.ruff]\n")
        self.assertTrue(should_use_ruff("foo.py"))

    def test_pyproject_toml_with_ruff_and_pyink(self):
        self.write_file("pyproject.toml", "[tool.ruff]\n[tool.pyink]\n")
        self.assertFalse(should_use_ruff("foo.py"))

    def test_pyproject_toml_with_ruff_and_black(self):
        self.write_file("pyproject.toml", "[tool.ruff]\n[tool.black]\n")
        self.assertFalse(should_use_ruff("foo.py"))

    def test_closest_config_wins(self):
        self.write_file("pyproject.toml", "[tool.black]\n")
        self.write_file("a/b/ruff.toml", "")
        self.assertTrue(should_use_ruff("a/b/foo.py"))

    def test_exclude_directory_yields_to_yapf(self):
        self.write_file("ruff.toml", 'exclude = ["third_party"]\n')
        self.assertFalse(should_use_ruff("third_party/foo.py"))
        self.assertTrue(should_use_ruff("src/foo.py"))

    def test_dot_ruff_toml_precedence(self):
        self.write_file("ruff.toml", 'exclude = ["foo.py"]\n')
        self.write_file(".ruff.toml", "")
        self.assertTrue(should_use_ruff("foo.py"))

    def test_ignore_child_directory_config(self):
        self.write_file("a/b/ruff.toml", "")
        self.write_file("a/.style.yapf", "")
        self.assertFalse(should_use_ruff("a/foo.py"))

    def test_ignore_child_directory_config_no_parent(self):
        self.write_file("a/b/ruff.toml", "")
        self.assertFalse(should_use_ruff("a/foo.py"))

    def test_unreadable_config_yields_to_yapf(self):
        self.write_file("ruff.toml", "")
        with patch("builtins.open",
                   side_effect=PermissionError("Permission denied")):
            self.assertFalse(should_use_ruff("foo.py"))


class TestTranslateArgs(unittest.TestCase):

    def test_translate_range_space(self):
        got = translate_args(["format", "--range", "5:1-10:1", "foo.py"])
        self.assertEqual(got, ["--line", "5-10", "foo.py", "-i"])

    def test_translate_range_equals(self):
        got = translate_args(["format", "--range=5:1-10:1", "foo.py"])
        self.assertEqual(got, ["--line", "5-10", "foo.py", "-i"])

    def test_translate_diff_and_stdin(self):
        got = translate_args(["format", "--diff", "--range=1:10-3:20", "-"])
        self.assertEqual(got, ["--diff", "--line", "1-3", "-"])


if __name__ == "__main__":
    unittest.main()
