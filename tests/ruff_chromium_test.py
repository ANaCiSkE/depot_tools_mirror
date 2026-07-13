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
import sys
import unittest
from unittest.mock import Mock, patch
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
parse_range = depot_tools_ruff.parse_range
merge_ranges = depot_tools_ruff.merge_ranges
parse_ranges = depot_tools_ruff.parse_ranges
parse_formatting_options = depot_tools_ruff.parse_formatting_options
FormattingOptions = depot_tools_ruff.FormattingOptions
ParsedArguments = depot_tools_ruff.ParsedArguments
LineRange = depot_tools_ruff.LineRange
run_ruff_with_ranges = depot_tools_ruff.run_ruff_with_ranges
extract_root_flag = depot_tools_ruff.extract_root_flag


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

    def test_root_dir_boundary_stops_traversal(self):
        self.write_file("ruff.toml", "")
        self.write_file(".style.yapf", "")
        sub_dir = os.path.join(self.test_dir, "subrepo")
        os.makedirs(sub_dir, exist_ok=True)
        self.assertFalse(should_use_ruff("subrepo/foo.py", root_dir=sub_dir))
        self.assertFalse(has_yapf_config("subrepo/foo.py", root_dir=sub_dir))

    def test_extract_root_flag(self):
        asc_dir = "/foo/bar"
        if sys.platform == "win32":
            asc_dir = "C:\\foo\\bar"
        root, remaining = extract_root_flag(
            ["--root", "/foo/bar", "format", "baz.py"])
        self.assertEqual(root, asc_dir)
        self.assertEqual(remaining, ["format", "baz.py"])

        root2, remaining2 = extract_root_flag(
            ["--top-dir=/foo/bar", "format", "baz.py"])
        self.assertEqual(root2, asc_dir)
        self.assertEqual(remaining2, ["format", "baz.py"])


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


class TestParseRange(unittest.TestCase):

    def test_valid_ranges(self):
        self.assertEqual(parse_range("5:1-10:20"), LineRange(5, 10))
        self.assertEqual(parse_range("1-10"), LineRange(1, 10))

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
        self.assertEqual(
            merge_ranges([LineRange(1, 4), LineRange(5, 10)]),
            [LineRange(1, 10)],
        )
        # Test case where a smaller start line has a large end line spanning across multiple ranges
        self.assertEqual(
            merge_ranges([LineRange(10, 16), LineRange(12, 13), LineRange(15, 20)]),
            [LineRange(10, 20)],
        )


class TestParseRanges(unittest.TestCase):

    def test_parse_valid(self):
        res = parse_ranges(
            ["format", "--range", "1-2", "--range=3-4", "file.py"])
        self.assertIsInstance(res, ParsedArguments)
        self.assertEqual(res.ranges, [LineRange(1, 2), LineRange(3, 4)])
        self.assertEqual(res.pass_through_args, ["format", "file.py"])

    def test_parse_invalid(self):
        with self.assertRaises(ValueError):
            parse_ranges(["format", "--range=1:1"])


class TestParseFormattingOptions(unittest.TestCase):

    def test_parsing(self):
        opts = parse_formatting_options(
            ["format", "--config", "ruff.toml", "--diff", "file.py"])
        self.assertIsInstance(opts, FormattingOptions)
        self.assertTrue(opts.has_format)
        self.assertTrue(opts.has_diff)
        self.assertFalse(opts.has_check)
        self.assertEqual(opts.target_files, ["file.py"])
        self.assertEqual(opts.chain_base_args,
                         ["format", "--config", "ruff.toml"])
        self.assertEqual(opts.subcmd_idx, 0)


class TestRunRuffWithRanges(unittest.TestCase):

    def test_invalid_multi_range_invocations(self):
        # Non-format subcommands are rejected for multiple ranges
        self.assertEqual(
            run_ruff_with_ranges(
                ["check", "--range=1:1-2:1", "--range=5:1-6:1", "file.py"]),
            1,
        )
        # Multiple target files are rejected for multiple ranges
        self.assertEqual(
            run_ruff_with_ranges([
                "format", "--range=1:1-2:1", "--range=5:1-6:1", "file1.py",
                "file2.py"
            ]),
            1,
        )
        # Stdin ('-') is rejected for multiple ranges
        self.assertEqual(
            run_ruff_with_ranges(
                ["format", "--range=1:1-2:1", "--range=5:1-6:1", "-"]),
            1,
        )
        # Missing target is rejected
        self.assertEqual(
            run_ruff_with_ranges(
                ["format", "--range=1:1-2:1", "--range=5:1-6:1"]),
            1,
        )

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_target_file_named_format(self, mock_stdout, mock_run):
        # When a file is literally named "format", the single-pass argument scanner must not
        # strip the "format" subcommand token.
        with tempfile.NamedTemporaryFile(mode="wb",
                                         prefix="format",
                                         delete=False) as f:
            f.write(b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
            temp_path = f.name
        try:
            proc1 = Mock(
                returncode=0,
                stdout=
                b"line1\nline2_mod\nline3\nline4\nline5\nline6_mod\nline7\n")
            proc2 = Mock(
                returncode=0,
                stdout=
                b"line1\nline2_mod\nline3\nline4\nline5\nline6_mod\nline7\n")
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges(
                ["format", "--range=2:1-2:5", "--range=6:1-6:5", temp_path])
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            # Verify the first positional command-line argument is still the "format" subcommand
            self.assertEqual(mock_run.call_args_list[0][0][0][3], "format")
            self.assertEqual(mock_run.call_args_list[1][0][0][3], "format")
            # Verify --stdin-filename=temp_path was injected
            self.assertIn(f"--stdin-filename={temp_path}",
                          mock_run.call_args_list[0][0][0])
            self.assertIn(f"--stdin-filename={temp_path}",
                          mock_run.call_args_list[1][0][0])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_space_separated_flags(self, mock_stdout, mock_run):
        # Verify that flags like --config ruff.toml do not have their values
        # misidentified as target files.
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py",
                                         delete=False) as f:
            f.write(b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
            temp_path = f.name
        try:
            proc1 = Mock(returncode=0, stdout=b"int_out\n")
            proc2 = Mock(returncode=0, stdout=b"final_out\n")
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges([
                "format", "--config", "ruff.toml", "--range=1:1-3:1",
                "--range=5:1-7:1", temp_path
            ])
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            # Verify the --config ruff.toml is correctly passed through
            for call_args in mock_run.call_args_list:
                args_passed = call_args[0][0]
                self.assertIn("--config", args_passed)
                # find --config index and check next
                idx = args_passed.index("--config")
                self.assertEqual(args_passed[idx + 1], "ruff.toml")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_sequential_chaining_injects_stdin_filename(self, mock_stdout,
                                                        mock_run):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py",
                                         delete=False) as f:
            f.write(b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
            temp_path = f.name
        try:
            # 1st call (5:1-7:1) returns intermediate output, 2nd call (1:1-3:1) returns final output
            proc1 = Mock(returncode=0, stdout=b"int_out\n")
            proc2 = Mock(returncode=0, stdout=b"final_out\n")
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges(
                ["format", "--range=1:1-3:1", "--range=5:1-7:1", temp_path])
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            # Verify bottom-up execution (5:1-7:1 first, then 1:1-3:1) and --stdin-filename injection
            self.assertIn("--range=5:1-7:1", mock_run.call_args_list[0][0][0])
            self.assertIn(f"--stdin-filename={temp_path}",
                          mock_run.call_args_list[0][0][0])
            self.assertEqual(
                mock_run.call_args_list[0][1]["input"],
                b"line1\nline2\nline3\nline4\nline5\nline6\nline7\n")
            self.assertIn("--range=1:1-3:1", mock_run.call_args_list[1][0][0])
            self.assertIn(f"--stdin-filename={temp_path}",
                          mock_run.call_args_list[1][0][0])
            self.assertEqual(mock_run.call_args_list[1][1]["input"],
                             b"int_out\n")
            with open(temp_path, "rb") as f_out:
                self.assertEqual(f_out.read(), b"final_out\n")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("subprocess.run")
    @patch("sys.stdout")
    def test_sequential_chaining_diff(self, mock_stdout, mock_run):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py",
                                         delete=False) as f:
            f.write(
                b"line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n"
            )
            temp_path = f.name
        try:
            proc1 = Mock(
                returncode=0,
                stdout=
                b"line1\nline2\nline3\nline4\nline5_mod\nline6\nline7\nline8\nline9\nline10\n"
            )
            proc2 = Mock(
                returncode=0,
                stdout=
                b"line1_mod\nline2\nline3\nline4\nline5_mod\nline6\nline7\nline8\nline9\nline10\n"
            )
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges([
                "format", "--range=1:1-1:5", "--range=5:1-5:5", "--diff",
                temp_path
            ])
            self.assertEqual(ret, 0)
            self.assertEqual(mock_run.call_count, 2)
            self.assertIn(f"--stdin-filename={temp_path}",
                          mock_run.call_args_list[0][0][0])
            self.assertIn(f"--stdin-filename={temp_path}",
                          mock_run.call_args_list[1][0][0])
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
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py",
                                         delete=False) as f:
            f.write(b"line1\nline2\nline3\n")
            temp_path = f.name
        try:
            # Output differs from original (so check should return 1)
            proc1 = Mock(returncode=0, stdout=b"line1_mod\nline2\nline3\n")
            proc2 = Mock(returncode=0, stdout=b"line1_mod\nline2\nline3_mod\n")
            mock_run.side_effect = [proc1, proc2]

            ret = run_ruff_with_ranges([
                "format", "--range=1:1-1:5", "--range=3:1-3:5", "--check",
                "--diff", temp_path
            ])
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
