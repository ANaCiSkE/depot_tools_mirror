#!/usr/bin/env vpython3
#
# [VPYTHON:BEGIN]
# python_version: "3.11"
# wheel: <
#   name: "infra/python/wheels/ruff/${vpython_platform}"
#   version: "version:0.15.17"
# >
# wheel: <
#   name: "infra/python/wheels/yapf-py3"
#   version: "version:0.40.2"
# >
# wheel: <
#   name: "infra/python/wheels/platformdirs-py3"
#   version: "version:4.1.0"
# >
# wheel: <
#   name: "infra/python/wheels/importlib-metadata-py3"
#   version: "version:7.0.0"
# >
# wheel: <
#   name: "infra/python/wheels/tomli-py3"
#   version: "version:2.0.1"
# >
# wheel: <
#  name: "infra/python/wheels/zipp-py3"
#  version: "version:3.7.0"
# >
# [VPYTHON:END]

# Copyright 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import importlib.util
from importlib.machinery import SourceFileLoader
import os
import sys
import json
import io
import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil

# Load depot_tools/ruff_chromium directly by file path to avoid naming collision with ruff package in site-packages
test_dir = os.path.dirname(os.path.abspath(__file__))
depot_tools_dir = os.path.dirname(test_dir)
ruff_path = os.path.join(depot_tools_dir, "ruff_chromium")
loader = SourceFileLoader("depot_tools_ruff_chromium", ruff_path)
spec = importlib.util.spec_from_loader(
    "depot_tools_ruff_chromium", loader, origin=ruff_path
)
assert spec is not None, f"Failed to load spec from {ruff_path}"
depot_tools_ruff = importlib.util.module_from_spec(spec)
sys.modules["depot_tools_ruff_chromium"] = depot_tools_ruff
loader.exec_module(depot_tools_ruff)

should_use_ruff = depot_tools_ruff.should_use_ruff
translate_args = depot_tools_ruff.translate_args
has_yapf_config = depot_tools_ruff.has_yapf_config
LineRange = depot_tools_ruff.LineRange
extract_root_flag = depot_tools_ruff.extract_root_flag
run_batch = depot_tools_ruff.run_batch
parse_range = depot_tools_ruff.parse_range
merge_ranges = depot_tools_ruff.merge_ranges
parse_ranges = depot_tools_ruff.parse_ranges
parse_formatting_options = depot_tools_ruff.parse_formatting_options
FormattingOptions = depot_tools_ruff.FormattingOptions
ParsedArguments = depot_tools_ruff.ParsedArguments
run_ruff_with_ranges = depot_tools_ruff.run_ruff_with_ranges


class TestHasYapfConfig(unittest.TestCase):
    def setUp(self):
        depot_tools_ruff._dir_config_cache.clear()
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


class TestShouldUseRuffRouting(unittest.TestCase):
    def setUp(self):
        depot_tools_ruff._dir_config_cache.clear()
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

    def test_closest_config_wins_with_unsupported(self):
        self.write_file("ruff.toml", "")
        self.write_file("a/b/pyproject.toml", "[tool.ruff]\n[tool.black]\n")
        self.assertFalse(should_use_ruff("a/b/foo.py"))

    def test_closest_config_wins_with_mixed(self):
        self.write_file("ruff.toml", "")
        self.write_file("a/b/pyproject.toml", "[tool.ruff]\n[tool.yapf]\n")
        self.assertFalse(should_use_ruff("a/b/foo.py"))
        self.assertTrue(has_yapf_config("a/b/foo.py"))

    def test_ignore_child_directory_config(self):
        self.write_file("a/b/ruff.toml", "")
        self.write_file("a/.style.yapf", "")
        self.assertFalse(should_use_ruff("a/foo.py"))

    def test_ignore_child_directory_config_no_parent(self):
        self.write_file("a/b/ruff.toml", "")
        self.assertFalse(should_use_ruff("a/foo.py"))

    def test_root_dir_boundary_stops_traversal(self):
        self.write_file("ruff.toml", "")
        self.write_file(".style.yapf", "")
        sub_dir = os.path.join(self.test_dir, "subrepo")
        os.makedirs(sub_dir, exist_ok=True)
        self.assertFalse(should_use_ruff("subrepo/foo.py", root_dir=sub_dir))
        self.assertFalse(has_yapf_config("subrepo/foo.py", root_dir=sub_dir))

    def test_cache_key_depends_on_root_dir(self):
        self.write_file("a/ruff.toml", "")
        sub_dir = os.path.join(self.test_dir, "a/b")
        os.makedirs(sub_dir, exist_ok=True)
        self.assertFalse(should_use_ruff("a/b/foo.py", root_dir=sub_dir))

        parent_dir = os.path.join(self.test_dir, "a")
        self.assertTrue(should_use_ruff("a/b/foo.py", root_dir=parent_dir))

    def test_extract_root_flag(self):
        asc_dir = "/foo/bar"
        if sys.platform == "win32":
            asc_dir = "C:\\foo\\bar"
        root, remaining = extract_root_flag(
            ["--root", "/foo/bar", "format", "baz.py"]
        )
        self.assertEqual(root, asc_dir)
        self.assertEqual(remaining, ["format", "baz.py"])

        root2, remaining2 = extract_root_flag(
            ["--top-dir=/foo/bar", "format", "baz.py"]
        )
        self.assertEqual(root2, asc_dir)
        self.assertEqual(remaining2, ["format", "baz.py"])


class TestTranslateArgs(unittest.TestCase):
    def test_translate_range_space(self):
        got = translate_args(["format", "--range", "5:1-10:1", "foo.py"])
        self.assertEqual(got, ["--line", "5-9", "foo.py", "-i"])

    def test_translate_range_equals(self):
        got = translate_args(["format", "--range=5:1-10:1", "foo.py"])
        self.assertEqual(got, ["--line", "5-9", "foo.py", "-i"])

    def test_translate_diff_and_stdin(self):
        got = translate_args(["format", "--diff", "--range=1:10-3:20", "-"])
        self.assertEqual(got, ["--diff", "--line", "1-3", "-"])

    def test_translate_single_line_range(self):
        got = translate_args(["format", "--range=1:10-1:20", "foo.py"])
        self.assertEqual(got, ["--line", "1-1", "foo.py", "-i"])


class TestBatchMode(unittest.TestCase):
    def setUp(self):
        depot_tools_ruff._dir_config_cache.clear()
        self.test_dir = tempfile.mkdtemp(prefix="ruff_batch_test_")
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        patcher = patch(
            "depot_tools_ruff_chromium.get_ruff_bin", return_value="ruff"
        )
        self.mock_get_ruff_bin = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def write_file(self, rel_path, content=""):
        abs_path = os.path.join(self.test_dir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return abs_path

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_json(self, mock_stderr):
        with patch("sys.stdin", io.StringIO("invalid json")):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Failed to parse batch config JSON",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_not_dict(self, mock_stderr):
        with patch("sys.stdin", io.StringIO(json.dumps([1, 2]))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Batch config must be a JSON object",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_root(self, mock_stderr):
        config = {"root": 123, "files": []}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Batch config 'root' must be a string",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_files(self, mock_stderr):
        config = {"files": "not a list"}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Batch config 'files' must be a list",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_file_entry(self, mock_stderr):
        config = {"files": ["not a dict"]}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Invalid file entry in batch config",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_file_entry_missing_path(self, mock_stderr):
        config = {"files": [{"no_path": "foo.py"}]}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Invalid file entry in batch config",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_file_entry_path_not_string(self, mock_stderr):
        config = {"files": [{"path": 123}]}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Invalid file entry in batch config",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_ranges_not_list(self, mock_stderr):
        config = {"files": [{"path": "foo.py", "ranges": "not a list"}]}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("File 'ranges' must be a list", mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_range_not_list(self, mock_stderr):
        config = {"files": [{"path": "foo.py", "ranges": ["not a list"]}]}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Invalid range entry in batch config",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_range_length(self, mock_stderr):
        config = {"files": [{"path": "foo.py", "ranges": [[1]]}]}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Invalid range entry in batch config",
                      mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_batch_invalid_range_elements(self, mock_stderr):
        config = {"files": [{"path": "foo.py", "ranges": [[1, "two"]]}]}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(1, ret)
        self.assertIn("Invalid range entry in batch config",
                      mock_stderr.getvalue())

    def test_batch_empty(self):
        config = {"files": []}
        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()
        self.assertEqual(0, ret)

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("subprocess.run")
    @patch("yapf.FormatFiles")
    def test_batch_ruff_no_range(self, mock_yapf, mock_run, mock_should_use):
        config = {
            "root": self.test_dir,
            "files": [{"path": "foo.py", "ranges": []}],
        }
        mock_should_use.return_value = True
        mock_run.return_value = Mock(returncode=0)

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        expected_path = os.path.join(self.test_dir, "foo.py")
        mock_run.assert_called_once_with(
            ["ruff", "format", "--force-exclude", expected_path], capture_output=True
        )
        mock_yapf.assert_not_called()

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("subprocess.run")
    def test_batch_ruff_with_ranges(self, mock_run, mock_should_use):
        config = {
            "root": self.test_dir,
            "files": [{"path": "foo.py", "ranges": [[1, 3]]}],
        }
        mock_should_use.return_value = True
        mock_run.return_value = Mock(returncode=0)

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        expected_path = os.path.join(self.test_dir, "foo.py")
        mock_run.assert_called_once_with(
            ["ruff", "format", "--force-exclude", expected_path], capture_output=True
        )

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    def test_batch_yapf(self, mock_format, mock_has_yapf, mock_should_use):
        foo_path = self.write_file("foo.py", "def foo():pass\n")
        config = {
            "root": self.test_dir,
            "files": [{"path": foo_path, "ranges": [[1, 3]]}],
        }
        mock_should_use.return_value = False
        mock_has_yapf.return_value = True
        mock_format.return_value = True

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        mock_format.assert_called_once_with(
            [foo_path],
            lines=[(1, 2)],
            style_config="pep8",
            in_place=True,
            print_diff=False,
            quiet=False,
        )

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    def test_batch_yapf_dry_run_changes(self, mock_format, mock_has_yapf, mock_should_use):
        foo_path = self.write_file("foo.py", "def foo():pass\n")
        config = {
            "root": self.test_dir,
            "dry_run": True,
            "files": [{"path": foo_path, "ranges": []}],
        }
        mock_should_use.return_value = False
        mock_has_yapf.return_value = True
        mock_format.return_value = True

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(2, ret)
        mock_format.assert_called_once_with(
            [foo_path],
            lines=None,
            style_config="pep8",
            in_place=False,
            print_diff=False,
            quiet=True,
        )
    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    @patch("subprocess.run")
    def test_batch_no_config_ignored(
        self, mock_run, mock_yapf, mock_has_yapf, mock_should_use
    ):
        config = {
            "root": self.test_dir,
            "files": [{"path": "foo.py", "ranges": []}],
        }
        mock_should_use.return_value = False
        mock_has_yapf.return_value = False

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        mock_run.assert_not_called()
        mock_yapf.assert_not_called()

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    def test_batch_yapf_empty_ranges_skipped(
        self, mock_yapf, mock_has_yapf, mock_should_use
    ):
        foo_path = self.write_file("foo.py", "def foo():pass\n")
        config = {
            "root": self.test_dir,
            "files": [{"path": foo_path, "ranges": [[5, 5]]}],
        }
        mock_should_use.return_value = False
        mock_has_yapf.return_value = True

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        mock_yapf.assert_not_called()

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    def test_batch_yapf_mixed_ranges_filtered(
        self, mock_yapf, mock_has_yapf, mock_should_use
    ):
        foo_path = self.write_file("foo.py", "def foo():pass\n")
        config = {
            "root": self.test_dir,
            "files": [{"path": foo_path, "ranges": [[5, 5], [6, 10]]}],
        }
        mock_should_use.return_value = False
        mock_has_yapf.return_value = True
        mock_yapf.return_value = True

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        mock_yapf.assert_called_once_with(
            [foo_path],
            lines=[(6, 9)],
            style_config="pep8",
            in_place=True,
            print_diff=False,
            quiet=False,
        )

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("subprocess.run")
    def test_batch_ruff_dry_run(self, mock_run, mock_should_use):
        config = {
            "root": self.test_dir,
            "dry_run": True,
            "files": [{"path": "foo.py", "ranges": []}],
        }
        mock_should_use.return_value = True
        mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        expected_path = os.path.join(self.test_dir, "foo.py")
        mock_run.assert_called_once_with(
            ["ruff", "format", "--force-exclude", "--check", expected_path],
            capture_output=True,
        )

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("subprocess.run")
    def test_batch_ruff_dry_run_changes(self, mock_run, mock_should_use):
        config = {
            "root": self.test_dir,
            "dry_run": True,
            "files": [{"path": "foo.py", "ranges": []}],
        }
        mock_should_use.return_value = True
        mock_run.return_value = Mock(returncode=1, stdout=b"", stderr=b"")

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(2, ret)

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("subprocess.run")
    def test_batch_ruff_diff(self, mock_run, mock_should_use):
        config = {
            "root": self.test_dir,
            "diff": True,
            "files": [{"path": "foo.py", "ranges": []}],
        }
        mock_should_use.return_value = True
        mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)
        expected_path = os.path.join(self.test_dir, "foo.py")
        mock_run.assert_called_once_with(
            ["ruff", "format", "--force-exclude", "--diff", expected_path],
            capture_output=True,
        )

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("subprocess.run")
    def test_batch_ruff_diff_changes(self, mock_run, mock_should_use):
        config = {
            "root": self.test_dir,
            "diff": True,
            "files": [{"path": "foo.py", "ranges": []}],
        }
        mock_should_use.return_value = True
        mock_run.return_value = Mock(returncode=1, stdout=b"diff output", stderr=b"")

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(0, ret)

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("subprocess.run")
    def test_batch_ruff_error_returns_1(self, mock_run, mock_should_use):
        config = {
            "root": self.test_dir,
            "files": [{"path": "foo.py", "ranges": []}],
        }
        mock_should_use.return_value = True
        mock_run.return_value = Mock(returncode=2, stdout=b"", stderr=b"some error")

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(1, ret)

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    def test_batch_yapf_error_returns_1(self, mock_format, mock_has_yapf, mock_should_use):
        foo_path = self.write_file("foo.py", "def foo():pass\n")
        config = {
            "root": self.test_dir,
            "files": [{"path": foo_path, "ranges": []}],
        }
        mock_should_use.return_value = False
        mock_has_yapf.return_value = True
        mock_format.side_effect = Exception("YAPF crash")

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(1, ret)

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    @patch("subprocess.run")
    def test_batch_mixed_error_takes_precedence_ruff_error_yapf_changes(
        self, mock_run, mock_format, mock_has_yapf, mock_should_use
    ):
        yapf_path = self.write_file("yapf.py", "def foo():pass\n")
        config = {
            "root": self.test_dir,
            "dry_run": True,
            "files": [
                {"path": "ruff.py", "ranges": []},
                {"path": yapf_path, "ranges": []},
            ],
        }
        def ruff_routing(path, root_dir=None):
            return "ruff.py" in path
        mock_should_use.side_effect = ruff_routing
        mock_has_yapf.return_value = True
        mock_run.return_value = Mock(returncode=2, stdout=b"", stderr=b"ruff error")
        mock_format.return_value = True

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(1, ret)

    @patch("depot_tools_ruff_chromium.should_use_ruff")
    @patch("depot_tools_ruff_chromium.has_yapf_config")
    @patch("yapf.FormatFiles")
    @patch("subprocess.run")
    def test_batch_mixed_error_takes_precedence_ruff_changes_yapf_error(
        self, mock_run, mock_format, mock_has_yapf, mock_should_use
    ):
        yapf_path = self.write_file("yapf.py", "def foo():pass\n")
        config = {
            "root": self.test_dir,
            "dry_run": True,
            "files": [
                {"path": "ruff.py", "ranges": []},
                {"path": yapf_path, "ranges": []},
            ],
        }
        def ruff_routing(path, root_dir=None):
            return "ruff.py" in path
        mock_should_use.side_effect = ruff_routing
        mock_has_yapf.return_value = True
        mock_run.return_value = Mock(returncode=1, stdout=b"", stderr=b"")
        mock_format.side_effect = Exception("YAPF crash")

        with patch("sys.stdin", io.StringIO(json.dumps(config))):
            ret = run_batch()

        self.assertEqual(1, ret)
class TestParseRange(unittest.TestCase):
    def test_valid_ranges(self):
        # end_col > 1 -> end_line incremented (exclusive end)
        self.assertEqual(parse_range("5:1-10:20"), LineRange(5, 11))
        # end_col == 1 -> end_line NOT incremented
        self.assertEqual(parse_range("5:1-10:1"), LineRange(5, 10))
        # no column specified -> assumed inclusive, end_line incremented
        self.assertEqual(parse_range("1-10"), LineRange(1, 11))

    def test_invalid_ranges(self):
        with self.assertRaises(ValueError):
            parse_range("5:1")
        with self.assertRaises(ValueError):
            parse_range("0:1-5:1")
        with self.assertRaises(ValueError):
            parse_range("10:1-5:1")
        with self.assertRaises(ValueError):
            parse_range("abc-def")


class TestMergeRanges(unittest.TestCase):
    def test_merge(self):
        self.assertEqual(
            merge_ranges([LineRange(1, 5), LineRange(10, 15)]),
            [LineRange(1, 5), LineRange(10, 15)],
        )
        self.assertEqual(
            merge_ranges([LineRange(1, 6), LineRange(5, 10)]),
            [LineRange(1, 10)],
        )
        # Adjacent ranges with a gap (line 4 is not formatted) should not merge
        self.assertEqual(
            merge_ranges([LineRange(1, 4), LineRange(5, 10)]),
            [LineRange(1, 4), LineRange(5, 10)],
        )
        # Adjacent ranges without a gap should merge
        self.assertEqual(
            merge_ranges([LineRange(1, 4), LineRange(4, 10)]),
            [LineRange(1, 10)],
        )
        # Test case where a smaller start line has a large end line spanning across multiple ranges
        self.assertEqual(
            merge_ranges(
                [LineRange(10, 16), LineRange(12, 13), LineRange(15, 20)]
            ),
            [LineRange(10, 20)],
        )


class TestParseRanges(unittest.TestCase):
    def test_parse_valid(self):
        res = parse_ranges(
            ["format", "--range", "1-2", "--range=3-4", "file.py"]
        )
        self.assertIsInstance(res, ParsedArguments)
        self.assertEqual(res.ranges, [LineRange(1, 3), LineRange(3, 5)])
        self.assertEqual(res.pass_through_args, ["format", "file.py"])

    def test_parse_invalid(self):
        with self.assertRaises(ValueError):
            parse_ranges(["format", "--range=1:1"])


class TestParseFormattingOptions(unittest.TestCase):
    def test_parsing(self):
        opts = parse_formatting_options(
            ["format", "--config", "ruff.toml", "--diff", "file.py"]
        )
        self.assertIsInstance(opts, FormattingOptions)
        self.assertTrue(opts.has_format)
        self.assertTrue(opts.has_diff)
        self.assertFalse(opts.has_check)
        self.assertEqual(opts.target_files, ["file.py"])
        self.assertEqual(
            opts.chain_base_args, ["format", "--config", "ruff.toml"]
        )
        self.assertEqual(opts.subcmd_idx, 0)


class TestRunRuffWithRanges(unittest.TestCase):
    def test_invalid_multi_range_invocations(self):
        # Non-format subcommands are rejected for multiple ranges
        self.assertEqual(
            run_ruff_with_ranges(
                ["check", "--range=1:1-2:1", "--range=5:1-6:1", "file.py"]
            ),
            1,
        )
        # Multiple target files are rejected for multiple ranges
        self.assertEqual(
            run_ruff_with_ranges(
                [
                    "format",
                    "--range=1:1-2:1",
                    "--range=5:1-6:1",
                    "file1.py",
                    "file2.py",
                ]
            ),
            1,
        )
        # Stdin ('-') is rejected for multiple ranges
        self.assertEqual(
            run_ruff_with_ranges(
                ["format", "--range=1:1-2:1", "--range=5:1-6:1", "-"]
            ),
            1,
        )
        # Missing target is rejected
        self.assertEqual(
            run_ruff_with_ranges(
                ["format", "--range=1:1-2:1", "--range=5:1-6:1"]
            ),
            1,
        )

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_target_file_named_format(self, mock_stdout, mock_run):
        # When a file is literally named "format", the single-pass argument scanner must not
        # strip the "format" subcommand token.
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix="format", delete=False
        ) as f:
            f.write(b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
            temp_path = f.name
        try:
            proc1 = Mock(
                returncode=0,
                stdout=b"line1\nline2_mod\nline3\nline4\nline5\nline6_mod\nline7\n",
            )
            proc2 = Mock(
                returncode=0,
                stdout=b"line1\nline2_mod\nline3\nline4\nline5\nline6_mod\nline7\n",
            )
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges(
                ["format", "--range=2:1-2:5", "--range=6:1-6:5", temp_path]
            )
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            # Verify the first positional command-line argument is still the "format" subcommand
            self.assertEqual(mock_run.call_args_list[0][0][0][1], "format")
            self.assertEqual(mock_run.call_args_list[1][0][0][1], "format")
            # Verify --stdin-filename=temp_path was injected
            self.assertIn(
                f"--stdin-filename={temp_path}",
                mock_run.call_args_list[0][0][0],
            )
            self.assertIn(
                f"--stdin-filename={temp_path}",
                mock_run.call_args_list[1][0][0],
            )
            # Verify --force-exclude was injected
            self.assertIn("--force-exclude", mock_run.call_args_list[0][0][0])
            self.assertIn("--force-exclude", mock_run.call_args_list[1][0][0])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_space_separated_flags(self, mock_stdout, mock_run):
        # Verify that flags like --config ruff.toml do not have their values
        # misidentified as target files.
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".py", delete=False
        ) as f:
            f.write(b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
            temp_path = f.name
        try:
            proc1 = Mock(returncode=0, stdout=b"int_out\n")
            proc2 = Mock(returncode=0, stdout=b"final_out\n")
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges(
                [
                    "format",
                    "--config",
                    "ruff.toml",
                    "--range=1:1-3:1",
                    "--range=5:1-7:1",
                    temp_path,
                ]
            )
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            # Verify the --config ruff.toml is correctly passed through
            for call_args in mock_run.call_args_list:
                args_passed = call_args[0][0]
                self.assertIn("--config", args_passed)
                # find --config index and check next
                idx = args_passed.index("--config")
                self.assertEqual(args_passed[idx + 1], "ruff.toml")
                # Verify --force-exclude was injected
                self.assertIn("--force-exclude", args_passed)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_sequential_chaining_injects_stdin_filename(
        self, mock_stdout, mock_run
    ):
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".py", delete=False
        ) as f:
            f.write(b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
            temp_path = f.name
        try:
            # 1st call (5:1-7:1) returns intermediate output, 2nd call (1:1-3:1) returns final output
            proc1 = Mock(returncode=0, stdout=b"int_out\n")
            proc2 = Mock(returncode=0, stdout=b"final_out\n")
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges(
                ["format", "--range=1:1-3:1", "--range=5:1-7:1", temp_path]
            )
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            # Verify bottom-up execution (5:1-7:1 first, then 1:1-3:1) and --stdin-filename injection
            self.assertIn("--range=5:1-7:1", mock_run.call_args_list[0][0][0])
            self.assertIn(
                f"--stdin-filename={temp_path}",
                mock_run.call_args_list[0][0][0],
            )
            self.assertIn("--force-exclude", mock_run.call_args_list[0][0][0])
            self.assertEqual(
                mock_run.call_args_list[0][1]["input"],
                b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n",
            )
            self.assertIn("--range=1:1-3:1", mock_run.call_args_list[1][0][0])
            self.assertIn(
                f"--stdin-filename={temp_path}",
                mock_run.call_args_list[1][0][0],
            )
            self.assertIn("--force-exclude", mock_run.call_args_list[1][0][0])
            self.assertEqual(
                mock_run.call_args_list[1][1]["input"], b"int_out\n"
            )
            with open(temp_path, "rb") as f_out:
                self.assertEqual(f_out.read(), b"final_out\n")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_sequential_chaining_diff(self, mock_stdout, mock_run):
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".py", delete=False
        ) as f:
            f.write(
                b"line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n"
            )
            temp_path = f.name
        try:
            proc1 = Mock(
                returncode=0,
                stdout=b"line1\nline2\nline3\nline4\nline5_mod\nline6\nline7\nline8\nline9\nline10\n",
            )
            proc2 = Mock(
                returncode=0,
                stdout=b"line1_mod\nline2\nline3\nline4\nline5_mod\nline6\nline7\nline8\nline9\nline10\n",
            )
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges(
                [
                    "format",
                    "--range=1:1-1:5",
                    "--range=5:1-5:5",
                    "--diff",
                    temp_path,
                ]
            )
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            self.assertIn(
                f"--stdin-filename={temp_path}",
                mock_run.call_args_list[0][0][0],
            )
            self.assertIn(
                f"--stdin-filename={temp_path}",
                mock_run.call_args_list[1][0][0],
            )
            # Verify diff output was written to stdout
            self.assertTrue(mock_stdout.buffer.write.called)
            diff_output = mock_stdout.buffer.write.call_args[0][0]
            self.assertIn(b"--- " + temp_path.encode("utf-8"), diff_output)
            self.assertIn(b"+line1_mod", diff_output)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_sequential_chaining_check_and_diff(self, mock_stdout, mock_run):
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".py", delete=False
        ) as f:
            f.write(b"line1\nline2\nline3\n")
            temp_path = f.name
        try:
            # Output differs from original (so check should return 1)
            proc1 = Mock(returncode=0, stdout=b"line1_mod\nline2\nline3\n")
            proc2 = Mock(returncode=0, stdout=b"line1_mod\nline2\nline3_mod\n")
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges(
                [
                    "format",
                    "--range=1:1-1:5",
                    "--range=3:1-3:5",
                    "--check",
                    "--diff",
                    temp_path,
                ]
            )
            # Verify exit code is 1 (due to --check detecting modifications)
            self.assertEqual(ret, 1)
            self.assertEqual(mock_run.call_count, 2)
            # Verify diff output was still generated and written to stdout
            self.assertTrue(mock_stdout.buffer.write.called)
            diff_output = mock_stdout.buffer.write.call_args[0][0]
            self.assertIn(b"--- " + temp_path.encode("utf-8"), diff_output)
            self.assertIn(b"+line1_mod", diff_output)
            self.assertIn(b"+line3_mod", diff_output)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
