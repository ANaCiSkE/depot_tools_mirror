#!/usr/bin/env vpython3
# Copyright 2020 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gerrit_util
import owners_client

alice = "alice@example.com"
bob = "bob@example.com"
chris = "chris@example.com"
dave = "dave@example.com"
emily = "emily@example.com"


class GerritClientTest(unittest.TestCase):
    def setUp(self):
        self.client = owners_client.GerritClient("host", "project", "branch")
        self.addCleanup(mock.patch.stopall)

    def testListOwners(self):
        mock.patch(
            "gerrit_util.GetOwnersForFile",
            return_value={
                "code_owners": [
                    {"account": {"email": "approver@example.com"}},
                    {
                        "account": {"email": "reviewer@example.com"},
                    },
                    {
                        "account": {"email": "missing@example.com"},
                    },
                    {
                        "account": {},
                    },
                ]
            },
        ).start()
        self.assertEqual(
            [
                "approver@example.com",
                "reviewer@example.com",
                "missing@example.com",
            ],
            self.client.ListOwners(os.path.join("bar", "everyone", "foo.txt")),
        )

        # Result should be cached.
        self.assertEqual(
            [
                "approver@example.com",
                "reviewer@example.com",
                "missing@example.com",
            ],
            self.client.ListOwners(os.path.join("bar", "everyone", "foo.txt")),
        )
        # Always use slashes as separators.
        gerrit_util.GetOwnersForFile.assert_called_once_with(
            "host",
            "project",
            "branch",
            "bar/everyone/foo.txt",
            resolve_all_users=False,
            highest_score_only=False,
            seed=mock.ANY,
        )

    def testListOwnersOwnedByAll(self):
        mock.patch(
            "gerrit_util.GetOwnersForFile",
            side_effect=[
                {
                    "code_owners": [
                        {
                            "account": {"email": "foo@example.com"},
                        },
                    ],
                    "owned_by_all_users": True,
                },
                {
                    "code_owners": [
                        {
                            "account": {"email": "bar@example.com"},
                        },
                    ],
                    "owned_by_all_users": False,
                },
            ],
        ).start()
        self.assertEqual(
            ["foo@example.com", self.client.EVERYONE],
            self.client.ListOwners("foo.txt"),
        )
        self.assertEqual(["bar@example.com"], self.client.ListOwners("bar.txt"))


class TestClient(owners_client.OwnersClient):
    def __init__(self, owners_by_path):
        super(TestClient, self).__init__()
        self.owners_by_path = owners_by_path

    def ListOwners(self, path):
        return self.owners_by_path[path]


class OwnersClientTest(unittest.TestCase):
    def setUp(self):
        self.owners = {}
        self.client = TestClient(self.owners)

    def testGetFilesApprovalStatus(self):
        self.client.owners_by_path = {
            "approved": ["approver@example.com"],
            "pending": ["reviewer@example.com"],
            "insufficient": ["insufficient@example.com"],
            "everyone": [owners_client.OwnersClient.EVERYONE],
        }
        self.assertEqual(
            self.client.GetFilesApprovalStatus(
                ["approved", "pending", "insufficient"],
                ["approver@example.com"],
                ["reviewer@example.com"],
            ),
            {
                "approved": owners_client.OwnersClient.APPROVED,
                "pending": owners_client.OwnersClient.PENDING,
                "insufficient": owners_client.OwnersClient.INSUFFICIENT_REVIEWERS,
            },
        )
        self.assertEqual(
            self.client.GetFilesApprovalStatus(
                ["everyone"], ["anyone@example.com"], []
            ),
            {"everyone": owners_client.OwnersClient.APPROVED},
        )
        self.assertEqual(
            self.client.GetFilesApprovalStatus(
                ["everyone"], [], ["anyone@example.com"]
            ),
            {"everyone": owners_client.OwnersClient.PENDING},
        )
        self.assertEqual(
            self.client.GetFilesApprovalStatus(["everyone"], [], []),
            {"everyone": owners_client.OwnersClient.INSUFFICIENT_REVIEWERS},
        )

    def testScoreOwners(self):
        self.client.owners_by_path = {"a": [alice, bob, chris]}
        self.assertEqual(
            self.client.ScoreOwners(self.client.owners_by_path.keys()),
            [alice, bob, chris],
        )

        self.client.owners_by_path = {
            "a": [alice, bob],
            "b": [bob],
            "c": [bob, chris],
        }
        self.assertEqual(
            self.client.ScoreOwners(self.client.owners_by_path.keys()),
            [alice, bob, chris],
        )

        self.client.owners_by_path = {
            "a": [alice, bob],
            "b": [bob],
            "c": [bob, chris],
        }
        self.assertEqual(
            self.client.ScoreOwners(
                self.client.owners_by_path.keys(), exclude=[chris]
            ),
            [alice, bob],
        )

        self.client.owners_by_path = {
            "a": [alice, bob, chris, dave],
            "b": [chris, bob, dave],
            "c": [chris, dave],
            "d": [alice, chris, dave],
        }
        self.assertEqual(
            self.client.ScoreOwners(self.client.owners_by_path.keys()),
            [alice, chris, bob, dave],
        )

    def assertSuggestsOwners(self, owners_by_path, exclude=None):
        self.client.owners_by_path = owners_by_path
        suggested = self.client.SuggestOwners(
            owners_by_path.keys(), exclude=exclude
        )

        # Owners should appear only once
        self.assertEqual(len(suggested), len(set(suggested)))

        # All paths should be covered.
        suggested = set(suggested)
        for owners in owners_by_path.values():
            self.assertTrue(suggested & set(owners))

        # No excluded owners should be present.
        if exclude:
            for owner in suggested:
                self.assertNotIn(owner, exclude)

    def testSuggestOwners(self):
        self.assertSuggestsOwners({})
        self.assertSuggestsOwners({"a": [alice]})
        self.assertSuggestsOwners({"abcd": [alice, bob, chris, dave]})
        self.assertSuggestsOwners(
            {"abcd": [alice, bob, chris, dave]}, exclude=[alice, bob]
        )
        self.assertSuggestsOwners(
            {
                "ae": [alice, emily],
                "be": [bob, emily],
                "ce": [chris, emily],
                "de": [dave, emily],
            }
        )
        self.assertSuggestsOwners(
            {
                "ad": [alice, dave],
                "cad": [chris, alice, dave],
                "ead": [emily, alice, dave],
                "bd": [bob, dave],
            }
        )
        self.assertSuggestsOwners(
            {"a": [alice], "b": [bob], "c": [chris], "ad": [alice, dave]}
        )
        self.assertSuggestsOwners(
            {
                "abc": [alice, bob, chris],
                "acb": [alice, chris, bob],
                "bac": [bob, alice, chris],
                "bca": [bob, chris, alice],
                "cab": [chris, alice, bob],
                "cba": [chris, bob, alice],
            }
        )

        # Check that we can handle a large amount of files with unrelated
        # owners.
        self.assertSuggestsOwners({str(x): [str(x)] for x in range(100)})

    def testBatchListOwners(self):
        self.client.owners_by_path = {
            "bar/everyone/foo.txt": [alice, bob],
            "bar/everyone/bar.txt": [bob],
            "bar/foo/": [bob, chris],
        }

        self.assertEqual(
            {
                "bar/everyone/foo.txt": [alice, bob],
                "bar/everyone/bar.txt": [bob],
                "bar/foo/": [bob, chris],
            },
            self.client.BatchListOwners(
                ["bar/everyone/foo.txt", "bar/everyone/bar.txt", "bar/foo/"]
            ),
        )

    def testSuggestMinimalOwners(self):
        self.client.owners_by_path = {
            "bar/everyone/foo.txt": [alice, bob, emily],
            "bar/everyone/bar.txt": [bob, emily],
            "bar/foo/": [bob, chris, emily],
            "baz/baz/baz": [chris, dave, emily],
        }

        self.assertEqual(
            [bob],
            self.client.SuggestMinimalOwners(
                ["bar/everyone/foo.txt", "bar/everyone/bar.txt", "bar/foo/"]
            ),
        )

        self.assertEqual(
            [chris],
            self.client.SuggestMinimalOwners(["bar/foo/", "baz/baz/baz"]),
        )

        self.assertEqual(
            [bob, chris],
            self.client.SuggestMinimalOwners(
                [
                    "bar/everyone/foo.txt",
                    "bar/everyone/bar.txt",
                    "bar/foo/",
                    "baz/baz/baz",
                ],
                exclude=[emily],
            ),
        )

        # A path whose every owner is excluded cannot be covered. Suggest the
        # owners that cover the rest.
        self.assertEqual(
            [bob],
            self.client.SuggestMinimalOwners(
                ["bar/everyone/foo.txt", "bar/everyone/bar.txt", "baz/baz/baz"],
                exclude=[emily, chris, dave],
            ),
        )

        # If no path can be covered at all, suggest nobody.
        self.assertEqual(
            [],
            self.client.SuggestMinimalOwners(
                ["baz/baz/baz"], exclude=[chris, dave, emily]
            ),
        )

        # An empty change needs no owners either.
        self.assertEqual([], self.client.SuggestMinimalOwners([]))

        # A path anybody can approve needs no reviewer of its own.
        self.client.owners_by_path["qux/qux"] = [
            owners_client.OwnersClient.EVERYONE
        ]
        self.assertEqual(
            [bob, chris],
            self.client.SuggestMinimalOwners(
                [
                    "bar/everyone/foo.txt",
                    "bar/everyone/bar.txt",
                    "bar/foo/",
                    "baz/baz/baz",
                    "qux/qux",
                ],
                exclude=[emily],
            ),
        )

    def testSuggestMinimalOwnersEveryoneCanApprove(self):
        client = TestClient(
            {
                "a": [alice, owners_client.OwnersClient.EVERYONE],
                "b": [bob, owners_client.OwnersClient.EVERYONE],
            }
        )
        # Any one of the owners can approve it all.
        suggested = client.SuggestMinimalOwners(["a", "b"])
        self.assertEqual(1, len(suggested))
        self.assertIn(suggested[0], [alice, bob])

        # With no owner left to name, anybody can still approve it.
        client = TestClient({"a": [alice, owners_client.OwnersClient.EVERYONE]})
        self.assertEqual(
            [owners_client.OwnersClient.EVERYONE],
            client.SuggestMinimalOwners(["a"], exclude=[alice]),
        )

        # Unless anybody is ruled out too.
        self.assertEqual(
            [],
            client.SuggestMinimalOwners(
                ["a"], exclude=[alice, owners_client.OwnersClient.EVERYONE]
            ),
        )

    def testSuggestMinimalOwnersIgnoresPathsAnybodyCanApprove(self):
        # Whoever reviews a.cc can approve BUILD.gn too, so bob is not needed.
        client = TestClient(
            {
                "a.cc": [alice],
                "BUILD.gn": [bob, owners_client.OwnersClient.EVERYONE],
            }
        )
        self.assertEqual(
            [alice], client.SuggestMinimalOwners(["a.cc", "BUILD.gn"])
        )

        # Owning q does not make bob a better choice than alice.
        client = TestClient(
            {
                "p1": [bob, alice],
                "p2": [alice],
                "q": [bob, owners_client.OwnersClient.EVERYONE],
            }
        )
        self.assertEqual(
            [alice], client.SuggestMinimalOwners(["p1", "p2", "q"])
        )


class GetCodeOwnersClientTest(unittest.TestCase):
    def setUp(self):
        mock.patch("gerrit_util.IsCodeOwnersEnabledOnHost").start()
        self.addCleanup(mock.patch.stopall)

    def testGetCodeOwnersClient_CodeOwnersEnabled(self):
        gerrit_util.IsCodeOwnersEnabledOnHost.return_value = True
        self.assertIsInstance(
            owners_client.GetCodeOwnersClient("host", "project", "branch"),
            owners_client.GerritClient,
        )

    def testGetCodeOwnersClient_CodeOwnersDisabled(self):
        gerrit_util.IsCodeOwnersEnabledOnHost.return_value = False
        with self.assertRaises(Exception):
            owners_client.GetCodeOwnersClient("", "", "")


if __name__ == "__main__":
    unittest.main()
