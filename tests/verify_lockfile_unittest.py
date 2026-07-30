#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for verify_lockfile.py"""

import os
import shutil
import sys
import tempfile
import unittest

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEPOT_TOOLS_ROOT)

from testing_support import coverage_utils
import verify_lockfile


class VerifyLockfileTest(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="verify_lockfile_test_")
        self.addCleanup(shutil.rmtree, self.test_dir, ignore_errors=True)

    def test_normalize_name(self):
        self.assertEqual(
            verify_lockfile.normalize_name("Package_Name.Foo"),
            "package-name-foo",
        )
        self.assertEqual(verify_lockfile.normalize_name("six"), "six")
        self.assertEqual(verify_lockfile.normalize_name("Urllib3"), "urllib3")
        self.assertEqual(
            verify_lockfile.normalize_name("requests[security]"),
            "requests",
        )
        self.assertEqual(
            verify_lockfile.normalize_name("requests [security]"),
            "requests",
        )

    def test_normalize_name_consecutive_delimiters(self):
        self.assertEqual(
            verify_lockfile.normalize_name("foo__bar..baz"),
            "foo-bar-baz",
        )

    def test_parse_vpython_toml(self):
        toml_path = os.path.join(self.test_dir, "vpython.toml")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(
                "# Some comments\n"
                'requires-python = ">=3.8"\n'
                "dependencies = [\n"
                '    "six==1.15.0",\n'
                '    "requests>=2.28.0",\n'
                "]\n"
            )
        deps = verify_lockfile.parse_vpython_toml(toml_path)
        self.assertEqual(deps, ["six==1.15.0", "requests>=2.28.0"])

    def test_parse_vpython_toml_empty(self):
        toml_path = os.path.join(self.test_dir, "vpython.toml")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write("# Empty file\n")
        deps = verify_lockfile.parse_vpython_toml(toml_path)
        self.assertEqual(deps, [])

    def test_parse_vpython_toml_malformed(self):
        toml_path = os.path.join(self.test_dir, "vpython.toml")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write("invalid toml = [ unclosed array\n")
        deps = verify_lockfile.parse_vpython_toml(toml_path)
        self.assertIsNone(deps)

    def test_parse_vpython_toml_array_of_tables_root(self):
        toml_path = os.path.join(self.test_dir, "vpython.toml")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write("[[array_root]]\nfoo = 'bar'\n")
        deps = verify_lockfile.parse_vpython_toml(toml_path)
        self.assertIsNotNone(deps)

    def test_parse_vpython_toml_non_list_dependencies(self):
        toml_path = os.path.join(self.test_dir, "vpython.toml")
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write('dependencies = "six"\n')
        deps = verify_lockfile.parse_vpython_toml(toml_path)
        self.assertIsNone(deps)

    def test_parse_pep723_script_block(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env vpython3\n"
                "# /// script\n"
                "# dependencies = [\n"
                '#   "six==1.15.0",\n'
                '#   "requests>=2.28.0",\n'
                "# ]\n"
                "# ///\n"
                "import six\n"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, ["six==1.15.0", "requests>=2.28.0"])

    def test_parse_pep723_embedded_in_docstring(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                '"""\n'
                "Example of PEP 723 format:\n"
                "# /// script\n"
                "# dependencies = ['six']\n"
                "# ///\n"
                '"""\n'
                "print('Hello world')\n"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, ["six"])

    def test_parse_pep723_no_trailing_newline(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "# /// script\n"
                "# dependencies = [\n"
                '#   "six==1.15.0",\n'
                "# ]\n"
                "# ///"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, ["six==1.15.0"])

    def test_parse_pep723_indented_comment_lines(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "  # /// script\n"
                "  # dependencies = [\n"
                '  #   "six==1.15.0",\n'
                "  # ]\n"
                "  # ///\n"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, ["six==1.15.0"])

    def test_parse_pep723_tab_comment(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "# /// script\n"
                "#\tdependencies = [\n"
                '#\t  "six==1.15.0",\n'
                "#\t]\n"
                "# ///\n"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, ["six==1.15.0"])

    def test_parse_pep723_vpython_block(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "# /// vpython\n"
                "# dependencies = [\n"
                '#   "urllib3==2.0.0",\n'
                "# ]\n"
                "# ///\n"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, ["urllib3==2.0.0"])

    def test_parse_pep723_unclosed_block(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "# /// script\n"
                "# dependencies = [\n"
                '#   "six==1.15.0",\n'
                "# ]\n"
                "# missing closing tag\n"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, [])

    def test_parse_pep723_multiple_blocks(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "# /// script\n"
                "# dependencies = ['six']\n"
                "# ///\n\n"
                "# /// script\n"
                "# dependencies = ['requests']\n"
                "# ///\n"
            )
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertIsNone(deps)

    def test_parse_pep723_no_block(self):
        script_path = os.path.join(self.test_dir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("print('Hello world')\n")
        deps = verify_lockfile.parse_pep723(script_path)
        self.assertEqual(deps, [])

    def test_parse_uv_lock_requirements_style(self):
        lock_path = os.path.join(self.test_dir, "vpython.toml.uv.lock")
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "# UV lockfile (requirements format)\n"
                "six==1.15.0 # requested by dep\n"
                "requests==2.31.0; python_version < '4'\n"
                "urllib-3==2.0.0 \\\n"
                "    --hash=sha256:12345\n"
            )
        deps = verify_lockfile.parse_uv_lock(lock_path)
        self.assertEqual(
            deps,
            {
                "six": ["1.15.0"],
                "requests": ["2.31.0"],
                "urllib-3": ["2.0.0"],
            },
        )

    def test_parse_uv_lock_toml_style(self):
        lock_path = os.path.join(self.test_dir, "vpython.toml.uv.lock")
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n"
                "revision = 1\n\n"
                "[[package]]\n"
                'name = "requests"\n'
                'version = "2.31.0"\n\n'
                "[[package]]\n"
                'name = "six"\n'
                'version = "1.16.0"\n'
            )
        deps = verify_lockfile.parse_uv_lock(lock_path)
        self.assertEqual(
            deps,
            {
                "requests": ["2.31.0"],
                "six": ["1.16.0"],
            },
        )

    def test_parse_uv_lock_unversioned_package(self):
        lock_path = os.path.join(self.test_dir, "vpython.toml.uv.lock")
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "local-package"\n'
                "source = { path = '../local-package' }\n"
            )
        deps = verify_lockfile.parse_uv_lock(lock_path)
        self.assertEqual(deps, {"local-package": ["0.0.0"]})

    def test_parse_uv_lock_corrupted_toml(self):
        lock_path = os.path.join(self.test_dir, "vpython.toml.uv.lock")
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write("[[package]]\nname = [ invalid toml\n")
        deps = verify_lockfile.parse_uv_lock(lock_path)
        self.assertIsNone(deps)

    def test_parse_uv_lock_empty_toml(self):
        lock_path = os.path.join(self.test_dir, "vpython.toml.uv.lock")
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write("version = 1\nrevision = 1\n")
        deps = verify_lockfile.parse_uv_lock(lock_path)
        self.assertEqual(deps, {})

    def test_parse_uv_lock_multiple_package_versions(self):
        lock_path = os.path.join(self.test_dir, "vpython.toml.uv.lock")
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "six"\n'
                'version = "1.15.0"\n\n'
                "[[package]]\n"
                'name = "six"\n'
                'version = "1.16.0"\n'
            )
        deps = verify_lockfile.parse_uv_lock(lock_path)
        self.assertEqual(deps, {"six": ["1.15.0", "1.16.0"]})

    def test_parse_uv_lock_missing(self):
        lock_path = os.path.join(self.test_dir, "nonexistent.uv.lock")
        deps = verify_lockfile.parse_uv_lock(lock_path)
        self.assertIsNone(deps)

    def test_verify_success_toml(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(
                "dependencies = [\n"
                '    "six==1.15.0",\n'
                '    "requests>=2.28.0,<3.0.0",\n'
                "]\n"
            )

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "six"\n'
                'version = "1.15.0"\n\n'
                "[[package]]\n"
                'name = "requests"\n'
                'version = "2.31.0"\n'
            )

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 0)

    def test_verify_dependency_with_extras(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write('dependencies = ["requests[security]>=2.28.0"]\n')

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "requests"\n'
                'version = "2.31.0"\n'
            )

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 0)

    def test_verify_non_string_dependency(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write("dependencies = [123]\n")

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write("six==1.15.0\n")

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 1)

    def test_verify_success_pep723(self):
        spec_path = os.path.join(self.test_dir, "foo.py")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(
                "# /// script\n"
                "# dependencies = [\n"
                '#   "six==1.15.0",\n'
                "# ]\n"
                "# ///\n"
            )

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                'version = 1\n\n[[package]]\nname = "six"\nversion = "1.15.0"\n'
            )

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 0)

    def test_verify_no_deps_spec(self):
        spec_path = os.path.join(self.test_dir, "foo.py")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write("print('No dependencies here')\n")

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 0)

    def test_verify_missing_spec(self):
        spec_path = os.path.join(self.test_dir, "nonexistent.toml")
        lock_path = spec_path + ".uv.lock"
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write("version = 1\n")

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 1)

    def test_verify_both_deleted(self):
        spec_path = os.path.join(self.test_dir, "deleted.toml")
        lock_path = spec_path + ".uv.lock"

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 0)

    def test_verify_missing_lockfile(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write('dependencies = ["six==1.15.0"]\n')

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 1)

    def test_verify_missing_dep_in_lock(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write('dependencies = ["six==1.15.0", "requests>=2.28.0"]\n')

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                'version = 1\n\n[[package]]\nname = "six"\nversion = "1.15.0"\n'
            )

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 1)

    def test_verify_unsatisfied_version(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write('dependencies = ["requests>=2.28.0"]\n')

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "requests"\n'
                'version = "2.20.0"\n'
            )

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 1)

    def test_verify_unconstrained_dependency(self):
        spec_path = os.path.join(self.test_dir, "unconstrained.toml")
        lock_path = spec_path + ".uv.lock"
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write('dependencies = ["six"]\n')
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                'version = 1\n\n[[package]]\nname = "six"\nversion = "1.15.0"\n'
            )
        self.assertEqual(verify_lockfile.verify(spec_path, lock_path), 0)

    def test_verify_environment_marker_universal_lockfile(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(
                "dependencies = [\"pywin32>=300; sys_platform == 'win32'\"]\n"
            )

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "pywin32"\n'
                'version = "306"\n'
            )

        ret = verify_lockfile.verify(spec_path, lock_path)
        self.assertEqual(ret, 0)

    def test_parse_pep723_tab_indented_markers_and_bounds(self):
        script_path = os.path.join(self.test_dir, "script.py")
        lock_path = script_path + ".uv.lock"

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                "# /// script\n"
                "#\tdependencies = [\n"
                "#\t  \"requests>=2.28.0; sys_platform == 'win32'\",\n"
                "#\t]\n"
                "# ///\n"
            )

        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                "version = 1\n\n"
                "[[package]]\n"
                'name = "requests"\n'
                'version = "2.31.0"\n'
            )

        ret = verify_lockfile.verify(script_path, lock_path)
        self.assertEqual(ret, 0)

    def test_main_entrypoint(self):
        spec_path = os.path.join(self.test_dir, "vpython.toml")
        lock_path = spec_path + ".uv.lock"

        with open(spec_path, "w", encoding="utf-8") as f:
            f.write('dependencies = ["six==1.15.0"]\n')
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(
                'version = 1\n\n[[package]]\nname = "six"\nversion = "1.15.0"\n'
            )

        self.assertEqual(verify_lockfile.main([spec_path, lock_path]), 0)
        self.assertEqual(verify_lockfile.main([]), 1)


if __name__ == "__main__":
    sys.exit(
        coverage_utils.covered_main(
            [os.path.join(DEPOT_TOOLS_ROOT, "verify_lockfile.py")],
            required_percentage=85,
        )
    )
