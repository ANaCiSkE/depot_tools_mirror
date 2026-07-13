#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import from_third_party


class FromThirdPartyTest(unittest.TestCase):

    def test_module_and_submodule_caching(self):
        """Verifies that modules and submodules are cached across imports and attached to parent modules."""
        repo1 = from_third_party.import_module('repo')
        repo2 = from_third_party.import_module('repo')
        self.assertIs(repo1, repo2)

        progress = from_third_party.import_module('repo.progress')
        self.assertIs(progress, repo1.progress)
        self.assertIn('_depot_tools_third_party_repo', sys.modules)
        self.assertIn('_depot_tools_third_party_repo.progress', sys.modules)

    def test_namespace_isolation(self):
        """Verifies that imports are isolated without contaminating top-level `schema` or `third_party` in sys.modules."""
        had_schema = 'schema' in sys.modules
        old_schema = sys.modules.get('schema')
        had_third_party = 'third_party' in sys.modules
        old_third_party = sys.modules.get('third_party')

        schema_mod = from_third_party.import_module('schema')
        self.assertIn('_depot_tools_third_party_schema', sys.modules)
        self.assertIs(sys.modules['_depot_tools_third_party_schema'],
                      schema_mod)

        if not had_schema:
            self.assertNotIn('schema', sys.modules)
        else:
            self.assertIs(sys.modules['schema'], old_schema)

        if not had_third_party:
            self.assertNotIn('third_party', sys.modules)
        else:
            self.assertIs(sys.modules['third_party'], old_third_party)

    def test_error_handling_missing(self):
        """Verifies that importing a non-existent module raises an ImportError referencing the missing target."""
        with self.assertRaises(ImportError) as cm:
            from_third_party.import_module('nonexistent_package.sub')
        self.assertIn('Cannot find third_party module nonexistent_package.sub',
                      str(cm.exception))

    def test_cleanup_on_execution_failure(self):
        """Verifies that sys.modules and parent attributes are cleaned up if a module raises an error on initialization."""
        tmp_dir = tempfile.mkdtemp()
        try:
            badpkg_dir = os.path.join(tmp_dir, 'badpkg')
            os.makedirs(badpkg_dir)
            with open(os.path.join(badpkg_dir, '__init__.py'), 'w') as f:
                f.write("raise RuntimeError('init failed')\n")

            goodpkg_dir = os.path.join(tmp_dir, 'goodpkg')
            os.makedirs(goodpkg_dir)
            with open(os.path.join(goodpkg_dir, '__init__.py'), 'w') as f:
                f.write("# empty\n")
            with open(os.path.join(goodpkg_dir, 'broken_sub.py'), 'w') as f:
                f.write("raise RuntimeError('sub init failed')\n")

            with mock.patch.object(from_third_party, '_THIRD_PARTY_ROOT',
                                   tmp_dir):
                with self.assertRaises(RuntimeError):
                    from_third_party.import_module('badpkg')
                self.assertNotIn('_depot_tools_third_party_badpkg', sys.modules)

                goodpkg = from_third_party.import_module('goodpkg')
                self.assertIn('_depot_tools_third_party_goodpkg', sys.modules)
                with self.assertRaises(RuntimeError):
                    from_third_party.import_module('goodpkg.broken_sub')
                self.assertNotIn('_depot_tools_third_party_goodpkg.broken_sub',
                                 sys.modules)
                self.assertFalse(hasattr(goodpkg, 'broken_sub'))
        finally:
            shutil.rmtree(tmp_dir)

    def test_get_module(self):
        """Verifies that get() returns loaded modules or None when not loaded without raising ImportError."""
        self.assertIsNone(from_third_party.get('nonexistent_package.sub'))
        schema_mod = from_third_party.import_module('schema')
        self.assertIs(from_third_party.get('schema'), schema_mod)


if __name__ == '__main__':
    unittest.main()
