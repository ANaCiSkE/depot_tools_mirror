#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from types import ModuleType
from typing import Any
import unittest
import unittest.mock

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(
    DEPOT_TOOLS_ROOT,
    "recipes",
    "recipe_modules",
    "windows_sdk",
    "resources",
    "find_env_json.py",
)


def _load_find_env_json_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("find_env_json", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FindEnvJsonTest(unittest.TestCase):
    module: ModuleType

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_find_env_json_module()

    def setUp(self) -> None:
        super().setUp()
        self._temp_dir = tempfile.TemporaryDirectory()
        self.td = self._temp_dir.name
        self.out_json = os.path.join(self.td, "out.json")

    def tearDown(self) -> None:
        self._temp_dir.cleanup()
        super().tearDown()

    def _run_script(
        self, sdk_root: str, target_arch: str, output_json: str
    ) -> subprocess.CompletedProcess[str]:
        cmd = [
            sys.executable,
            SCRIPT_PATH,
            "--sdk_root",
            sdk_root,
            "--target_arch",
            target_arch,
            "--output_json",
            output_json,
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_possible_base_locations_priority(self) -> None:
        expected_modern = os.path.join("Windows Kits", "10", "bin")
        expected_legacy = os.path.join("win_sdk", "bin")
        self.assertEqual(
            self.module.POSSIBLE_BASE_LOCATIONS,
            [expected_modern, expected_legacy],
        )

    def test_modern_sdk_manifest_resolution(self) -> None:
        modern_dir = os.path.join(self.td, "Windows Kits", "10", "bin")
        os.makedirs(modern_dir)

        expected_data = {
            "env": {
                "VSINSTALLDIR": [[".\\"]],
                "VCINSTALLDIR": [["VC\\"]],
                "VCToolsInstallDir": [["VC", "Tools", "MSVC", "14.42.34433\\"]],
                "INCLUDE": [
                    ["Windows Kits", "10", "Include", "10.0.22621.0", "um"],
                    ["VC", "Tools", "MSVC", "14.42.34433", "include"],
                ],
                "LIBPATH": [
                    [
                        "VC",
                        "Tools",
                        "MSVC",
                        "14.42.34433",
                        "lib",
                        "x86",
                        "store",
                        "references",
                    ],
                ],
                "PATH": [
                    ["Windows Kits", "10", "bin", "10.0.22621.0", "x64"],
                    [
                        "VC",
                        "Tools",
                        "MSVC",
                        "14.42.34433",
                        "bin",
                        "HostX64",
                        "x64",
                    ],
                ],
                "LIB": [
                    ["VC", "Tools", "MSVC", "14.42.34433", "lib", "x64"],
                ],
            }
        }
        manifest_path = os.path.join(modern_dir, "SetEnv.x64.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(expected_data, f)

        res = self._run_script(self.td, "x64", self.out_json)

        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertTrue(os.path.exists(self.out_json))
        with open(self.out_json, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), expected_data)

    def test_legacy_sdk_manifest_resolution(self) -> None:
        legacy_dir = os.path.join(self.td, "win_sdk", "bin")
        os.makedirs(legacy_dir)

        expected_data = {
            "env": {
                "PATH": [["..", "..", "win_sdk", "bin", "x64"]],
                "VSINSTALLDIR": [["..", "..\\"]],
                "INCLUDE": [
                    [
                        "..",
                        "..",
                        "win_sdk",
                        "Include",
                        "10.0.17134.0",
                        "um",
                    ],
                ],
            }
        }
        manifest_path = os.path.join(legacy_dir, "SetEnv.x64.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(expected_data, f)

        res = self._run_script(self.td, "x64", self.out_json)

        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertTrue(os.path.exists(self.out_json))
        with open(self.out_json, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), expected_data)

    def test_ambiguous_multiple_manifests_rejected(self) -> None:
        modern_dir = os.path.join(self.td, "Windows Kits", "10", "bin")
        legacy_dir = os.path.join(self.td, "win_sdk", "bin")
        os.makedirs(modern_dir)
        os.makedirs(legacy_dir)

        modern_data = {"env": {"PATH": [["Windows Kits", "10", "bin", "x64"]]}}
        legacy_data = {"env": {"PATH": [["..", "..", "win_sdk", "bin", "x64"]]}}

        with open(
            os.path.join(modern_dir, "SetEnv.x64.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(modern_data, f)
        with open(
            os.path.join(legacy_dir, "SetEnv.x64.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(legacy_data, f)

        res = self._run_script(self.td, "x64", self.out_json)

        self.assertNotEqual(res.returncode, 0)
        self.assertIn("multiple setenv files found", res.stderr.lower())
        self.assertFalse(os.path.exists(self.out_json))

    def test_cross_arch_split_manifests_rejected(self) -> None:
        modern_dir = os.path.join(self.td, "Windows Kits", "10", "bin")
        legacy_dir = os.path.join(self.td, "win_sdk", "bin")
        os.makedirs(modern_dir)
        os.makedirs(legacy_dir)

        modern_x64 = {"env": {"PATH": [["Windows Kits", "10", "bin", "x64"]]}}
        legacy_arm64 = {
            "env": {"PATH": [["..", "..", "win_sdk", "bin", "arm64"]]}
        }

        with open(
            os.path.join(modern_dir, "SetEnv.x64.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(modern_x64, f)
        with open(
            os.path.join(legacy_dir, "SetEnv.arm64.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(legacy_arm64, f)

        res = self._run_script(self.td, "arm64", self.out_json)

        self.assertNotEqual(res.returncode, 0)
        self.assertIn("multiple setenv files found", res.stderr.lower())
        self.assertFalse(os.path.exists(self.out_json))

    def test_supported_architectures(self) -> None:
        modern_dir = os.path.join(self.td, "Windows Kits", "10", "bin")
        os.makedirs(modern_dir)

        for arch in ("x86", "x64", "arm64"):
            arch_data = {"env": {"PATH": [["Windows Kits", "10", "bin", arch]]}}
            manifest_path = os.path.join(modern_dir, f"SetEnv.{arch}.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(arch_data, f)

            out_json = os.path.join(self.td, f"out_{arch}.json")
            res = self._run_script(self.td, arch, out_json)
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            with open(out_json, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), arch_data)

    def test_cipd_internal_symlink_allowed_and_escaping_symlink_rejected(
        self,
    ) -> None:
        sdk_root = os.path.join(self.td, "windows_sdk")
        cipd_pkg = os.path.join(
            sdk_root,
            ".cipd",
            "pkgs",
            "0",
            "instance",
            "Windows Kits",
            "10",
            "bin",
        )
        modern_dir = os.path.join(sdk_root, "Windows Kits", "10", "bin")
        os.makedirs(cipd_pkg)
        os.makedirs(modern_dir)

        expected_data = {
            "env": {"PATH": [["Windows Kits", "10", "bin", "x64"]]}
        }
        cipd_file = os.path.join(cipd_pkg, "SetEnv.x64.json")
        with open(cipd_file, "w", encoding="utf-8") as f:
            json.dump(expected_data, f)

        link_path = os.path.join(modern_dir, "SetEnv.x64.json")
        try:
            os.symlink(cipd_file, link_path)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        out_ok = os.path.join(self.td, "out_ok.json")
        res = self._run_script(sdk_root, "x64", out_ok)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertTrue(os.path.exists(out_ok))

        os.remove(link_path)
        outside_dir = os.path.join(self.td, "windows_sdk_outside")
        os.makedirs(outside_dir)
        outside_file = os.path.join(outside_dir, "SetEnv.x64.json")
        with open(outside_file, "w", encoding="utf-8") as f:
            json.dump(expected_data, f)
        os.symlink(outside_file, link_path)

        out_bad = os.path.join(self.td, "out_bad.json")
        res_bad = self._run_script(sdk_root, "x64", out_bad)
        self.assertNotEqual(res_bad.returncode, 0)
        self.assertIn("outside sdk_root", res_bad.stderr.lower())
        self.assertFalse(os.path.exists(out_bad))

    def test_resolve_within_root_handles_cross_drive_and_sibling_prefixes(
        self,
    ) -> None:
        root = os.path.abspath("/cache/windows_sdk")
        with unittest.mock.patch(
            "os.path.realpath",
            side_effect=lambda p: p,
        ):
            self.assertIsNone(
                self.module._resolve_within_root(
                    os.path.abspath("/cache/windows_sdk_extra/SetEnv.x64.json"),
                    root,
                )
            )
            self.assertIsNone(self.module._resolve_within_root(root, root))

        with unittest.mock.patch(
            "os.path.commonpath", side_effect=ValueError("different drives")
        ):
            self.assertIsNone(
                self.module._resolve_within_root("D:\\SetEnv.x64.json", root)
            )

    def test_directory_at_candidate_location_rejected(self) -> None:
        legacy_candidate = os.path.join(
            self.td, "win_sdk", "bin", "SetEnv.x64.json"
        )
        os.makedirs(legacy_candidate)

        res = self._run_script(self.td, "x64", self.out_json)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("not a regular file", res.stderr.lower())
        self.assertFalse(os.path.exists(self.out_json))

    def test_missing_manifest_rejected(self) -> None:
        res = self._run_script(self.td, "x64", self.out_json)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("unable to locate setenv file", res.stderr.lower())
        self.assertFalse(os.path.exists(self.out_json))

    def test_invalid_json_and_non_utf8_rejected(self) -> None:
        modern_dir = os.path.join(self.td, "Windows Kits", "10", "bin")
        os.makedirs(modern_dir)
        manifest_path = os.path.join(modern_dir, "SetEnv.x64.json")

        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true")
        res = self._run_script(self.td, "x64", self.out_json)
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(os.path.exists(self.out_json))

        with open(manifest_path, "wb") as f:
            f.write(b"\xff\xfe\x00\x00invalid_utf8")
        res = self._run_script(self.td, "x64", self.out_json)
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(os.path.exists(self.out_json))

    def test_invalid_setenv_schema_and_path_traversal_rejected(self) -> None:
        invalid_payloads: list[Any] = [
            ["not", "a", "dict"],
            {"other": {}},
            {"env": "not_a_dict"},
            {"env": {"": [["VC"]]}},
            {"env": {"PATH": "not_a_list"}},
            {"env": {"PATH": [[]]}},
            {"env": {"PATH": ["not_a_list_entry"]}},
            {"env": {"PATH": [[123]]}},
            {"env": {"PATH": [[".."]]}},
            {"env": {"PATH": [["..", "single_dotdot"]]}},
            {"env": {"PATH": [["..\\", "..\\", "outside"]]}},
            {"env": {"PATH": [["..", "..", "..", "outside"]]}},
            {"env": {"PATH": [["VC", "..", "..", "outside"]]}},
            {"env": {"PATH": [["VC\\..\\..\\outside"]]}},
            {"env": {"PATH": [["C:\\Windows\\System32"]]}},
            {"env": {"PATH": [["\\\\server\\share\\bin"]]}},
            {"env": {"PATH": [["/usr/local/bin"]]}},
            {"env": {"PATH": [["\\Windows\\System32"]]}},
        ]
        modern_dir = os.path.join(self.td, "Windows Kits", "10", "bin")
        os.makedirs(modern_dir)
        manifest_path = os.path.join(modern_dir, "SetEnv.x64.json")

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                res = self._run_script(self.td, "x64", self.out_json)
                self.assertNotEqual(res.returncode, 0)
                self.assertFalse(os.path.exists(self.out_json))

    def test_cli_argument_validation(self) -> None:
        res = self._run_script("relative/sdk_root", "x64", self.out_json)
        self.assertNotEqual(res.returncode, 0)

        res = self._run_script(self.td, "x64", "relative_out.json")
        self.assertNotEqual(res.returncode, 0)

        res = self._run_script(self.td, "mips64", self.out_json)
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(os.path.exists(self.out_json))


if __name__ == "__main__":
    unittest.main()
