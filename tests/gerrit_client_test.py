#!/usr/bin/env vpython3
# coding=utf-8
# Copyright 2020 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for gerrit_client.py."""

import contextlib
import io
import logging
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gerrit_client


class TestGerritClient(unittest.TestCase):
    @mock.patch("gerrit_util.GetGerritBranch", return_value="")
    def test_branch_info(self, util_mock):
        gerrit_client.main(
            [
                "branchinfo",
                "--host",
                "https://example.org/foo",
                "--project",
                "projectname",
                "--branch",
                "branchname",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org", "projectname", "branchname"
        )

    @mock.patch("gerrit_util.CreateGerritBranch", return_value="")
    @mock.patch("gerrit_util.GetGerritBranch", return_value="")
    def test_branch(self, _, CreateGerritBranch_mock):
        gerrit_client.main(
            [
                "branch",
                "--host",
                "https://example.org/foo",
                "--project",
                "projectname",
                "--branch",
                "branchname",
                "--commit",
                "commitname",
            ]
        )
        CreateGerritBranch_mock.assert_called_once_with(
            "example.org", "projectname", "branchname", "commitname"
        )

    @mock.patch("gerrit_util.QueryChanges", return_value="")
    def test_changes(self, util_mock):
        gerrit_client.main(
            [
                "changes",
                "--host",
                "https://example.org/foo",
                "-p",
                "foo=bar",
                "-p",
                "baz=qux",
                "--limit",
                "10",
                "--start",
                "20",
                "-o",
                "op1",
                "-o",
                "op2",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            [("foo", "bar"), ("baz", "qux")],
            first_param=None,
            limit=10,
            start=20,
            o_params=["op1", "op2"],
        )

    @mock.patch("gerrit_util.QueryChanges", return_value="")
    def test_changes_query(self, util_mock):
        gerrit_client.main(
            [
                "changes",
                "--host",
                "https://example.org/foo",
                "--query",
                "is:owner is:open",
                "--limit",
                "10",
                "--start",
                "20",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            [],
            first_param="is:owner is:open",
            limit=10,
            start=20,
            o_params=None,
        )

    @mock.patch("gerrit_util.QueryChanges", return_value="")
    def test_changes_params_query(self, util_mock):
        gerrit_client.main(
            [
                "changes",
                "--host",
                "https://example.org/foo",
                "--query",
                "is:owner is:open",
                "-p",
                "foo=bar",
                "--limit",
                "10",
                "--start",
                "20",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            [("foo", "bar")],
            first_param="is:owner is:open",
            limit=10,
            start=20,
            o_params=None,
        )

    @mock.patch("gerrit_client.write_result")
    @mock.patch("gerrit_util.GetChangeChecks")
    def test_checks_revision_json(self, util_mock, write_result_mock):
        checks = [
            {"check_name": "ClangTidy", "results": [{"message": "finding"}]}
        ]
        util_mock.return_value = checks

        gerrit_client.main(
            [
                "checks",
                "--host",
                "https://example.org/foo",
                "--change",
                "8265612",
                "--revision",
                "1",
                "--json_file",
                "checks.json",
            ]
        )

        util_mock.assert_called_once_with(
            "example.org", "8265612", revision="1"
        )
        write_result_mock.assert_called_once()
        result, opt = write_result_mock.call_args.args
        self.assertIs(checks, result)
        self.assertEqual("checks.json", opt.json_file)

    @mock.patch("gerrit_util.GetChangeChecks", return_value=[])
    def test_checks_defaults(self, util_mock):
        gerrit_client.main(
            [
                "checks",
                "--host",
                "https://example.org/foo",
                "--change",
                "project~branch~Ichange",
            ]
        )

        util_mock.assert_called_once_with(
            "example.org",
            "project~branch~Ichange",
            revision="current",
        )

    @mock.patch("gerrit_util.GetChangeChecks")
    def test_checks_requires_change(self, util_mock):
        stderr = io.StringIO()
        with (
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as error,
        ):
            gerrit_client.main(["checks", "--host", "https://example.org"])

        self.assertEqual(2, error.exception.code)
        self.assertIn("--change is required", stderr.getvalue())
        util_mock.assert_not_called()

    @mock.patch("gerrit_client.write_result")
    @mock.patch("gerrit_util.GetChangeComments")
    def test_comments(self, util_mock, write_result_mock):
        comments = {"file.py": [{"message": "published comment"}]}
        util_mock.return_value = comments

        gerrit_client.main(
            [
                "comments",
                "--host",
                "https://example.org/foo",
                "--change",
                "project~branch~Ichange",
                "--json_file",
                "comments.json",
            ]
        )

        util_mock.assert_called_once_with(
            "example.org", "project~branch~Ichange"
        )
        write_result_mock.assert_called_once()
        result, opt = write_result_mock.call_args.args
        self.assertIs(comments, result)
        self.assertEqual("comments.json", opt.json_file)

    @mock.patch("gerrit_util.GetRelatedChanges", return_value="")
    def test_relatedchanges(self, util_mock):
        gerrit_client.main(
            [
                "relatedchanges",
                "--host",
                "https://example.org/foo",
                "--change",
                "foo-change-id",
                "--revision",
                "foo-revision-id",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org", change="foo-change-id", revision="foo-revision-id"
        )

    @mock.patch("gerrit_util.CreateChange", return_value={})
    def test_createchange(self, util_mock):
        gerrit_client.main(
            [
                "createchange",
                "--host",
                "https://example.org/foo",
                "--project",
                "project",
                "--branch",
                "main",
                "--subject",
                "subject",
                "-p",
                "work_in_progress=true",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            "project",
            branch="main",
            subject="subject",
            params=[("work_in_progress", "true")],
        )

    @mock.patch("builtins.open", mock.mock_open())
    @mock.patch("gerrit_util.ChangeEdit", return_value="")
    def test_changeedit(self, util_mock):
        open().read.return_value = "test_data"
        gerrit_client.main(
            [
                "changeedit",
                "--host",
                "https://example.org/foo",
                "--change",
                "1",
                "--path",
                "path/to/file",
                "--file",
                "/my/foo",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org", 1, "path/to/file", "test_data"
        )

    @mock.patch("gerrit_util.PublishChangeEdit", return_value="")
    def test_publishchangeedit(self, util_mock):
        gerrit_client.main(
            [
                "publishchangeedit",
                "--host",
                "https://example.org/foo",
                "--change",
                "1",
                "--notify",
                "yes",
            ]
        )
        util_mock.assert_called_once_with("example.org", 1, "yes")

    @mock.patch("gerrit_util.AbandonChange", return_value="")
    def test_abandon(self, util_mock):
        gerrit_client.main(
            [
                "abandon",
                "--host",
                "https://example.org/foo",
                "-c",
                "1",
                "-m",
                "bar",
            ]
        )
        util_mock.assert_called_once_with("example.org", 1, "bar")

    @mock.patch("gerrit_util.SetReview", return_value="")
    def test_setlabel(self, util_mock):
        gerrit_client.main(
            [
                "setlabel",
                "--host",
                "https://example.org/foo",
                "-c",
                "1",
                "-l",
                "some-label",
                "-2",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org", 1, labels={"some-label": "-2"}
        )

    @mock.patch("gerrit_util.SetReview", return_value="")
    def test_addmessage(self, util_mock):
        gerrit_client.main(
            [
                "addmessage",
                "--host",
                "https://example.org/foo",
                "-c",
                "1",
                "-r",
                "2",
                "-m",
                "This is a message",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            1,
            revision="2",
            msg="This is a message",
            automatic_attention_set_update=None,
        )

    @mock.patch("gerrit_util.CreateDraft", return_value={})
    def test_adddraftcomment_defaults(self, util_mock):
        gerrit_client.main(
            [
                "adddraftcomment",
                "--host",
                "https://example.org/foo",
                "-c",
                "123",
                "-m",
                "Draft comment",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            "123",
            revision="current",
            body={"path": "/PATCHSET_LEVEL", "message": "Draft comment"},
        )

    @mock.patch("gerrit_client.write_result")
    @mock.patch("gerrit_util.CreateDraft")
    def test_adddraftcomment_options(self, util_mock, write_result_mock):
        draft = {"id": "draft-1", "message": "Inline reply"}
        util_mock.return_value = draft
        gerrit_client.main(
            [
                "adddraftcomment",
                "--host",
                "https://example.org/foo",
                "-c",
                "123",
                "-r",
                "2",
                "--path",
                "src/foo.cc",
                "--line",
                "42",
                "--side",
                "REVISION",
                "--in-reply-to",
                "comment-uuid",
                "--unresolved",
                "-m",
                "Inline reply",
                "--json_file",
                "draft.json",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            "123",
            revision="2",
            body={
                "path": "src/foo.cc",
                "line": 42,
                "side": "REVISION",
                "in_reply_to": "comment-uuid",
                "unresolved": True,
                "message": "Inline reply",
            },
        )
        write_result_mock.assert_called_once()
        result, opt = write_result_mock.call_args.args
        self.assertIs(draft, result)
        self.assertEqual("draft.json", opt.json_file)

    @mock.patch("gerrit_util.CreateDraft", return_value={})
    def test_adddraftcomment_body_and_override(self, util_mock):
        gerrit_client.main(
            [
                "adddraftcomment",
                "--host",
                "https://example.org/foo",
                "-c",
                "123",
                "--body",
                '{"path": "src/foo.cc", "line": 10, "message": "From body"}',
                "--resolved",
            ]
        )
        util_mock.assert_called_once_with(
            "example.org",
            "123",
            revision="current",
            body={
                "path": "src/foo.cc",
                "line": 10,
                "message": "From body",
                "unresolved": False,
            },
        )

    @mock.patch("gerrit_util.CreateDraft", return_value={})
    @mock.patch("gerrit_util.GetChangeComments")
    def test_adddraftcomment_in_reply_to_resolves_parent(
        self, get_comments_mock, create_draft_mock
    ):
        get_comments_mock.return_value = {
            "/PATCHSET_LEVEL": [{"id": "ps-uuid", "patch_set": 1}],
            "src/foo.cc": [
                {
                    "id": "comment-uuid",
                    "patch_set": 2,
                    "line": 42,
                    "side": "PARENT",
                    "range": {
                        "start_line": 42,
                        "start_character": 0,
                        "end_line": 42,
                        "end_character": 10,
                    },
                }
            ],
        }
        gerrit_client.main(
            [
                "adddraftcomment",
                "--host",
                "https://example.org/foo",
                "-c",
                "123",
                "--in-reply-to",
                "comment-uuid",
                "--resolved",
                "-m",
                "Done.",
            ]
        )
        get_comments_mock.assert_called_once_with("example.org", "123")
        create_draft_mock.assert_called_once_with(
            "example.org",
            "123",
            revision="2",
            body={
                "path": "src/foo.cc",
                "line": 42,
                "side": "PARENT",
                "range": {
                    "start_line": 42,
                    "start_character": 0,
                    "end_line": 42,
                    "end_character": 10,
                },
                "in_reply_to": "comment-uuid",
                "unresolved": False,
                "message": "Done.",
            },
        )

    @mock.patch("gerrit_util.GetChangeComments", return_value={})
    @mock.patch("gerrit_util.CreateDraft")
    def test_adddraftcomment_validation(self, util_mock, get_comments_mock):
        for args, expected_err in [
            (
                [
                    "adddraftcomment",
                    "--host",
                    "https://example.org",
                    "-m",
                    "hi",
                ],
                "--change is required",
            ),
            (
                [
                    "adddraftcomment",
                    "--host",
                    "https://example.org",
                    "-c",
                    "123",
                ],
                "--message is required",
            ),
            (
                [
                    "adddraftcomment",
                    "--host",
                    "https://example.org",
                    "-c",
                    "123",
                    "--body",
                    "{bad",
                ],
                "Invalid --body JSON",
            ),
            (
                [
                    "adddraftcomment",
                    "--host",
                    "https://example.org",
                    "-c",
                    "123",
                    "--body",
                    "[]",
                ],
                "--body must be a JSON object",
            ),
            (
                [
                    "adddraftcomment",
                    "--host",
                    "https://example.org",
                    "-c",
                    "123",
                    "--line",
                    "42",
                    "-m",
                    "hi",
                ],
                "--path is required when --line is specified",
            ),
            (
                [
                    "adddraftcomment",
                    "--host",
                    "https://example.org",
                    "-c",
                    "123",
                    "--in-reply-to",
                    "missing-uuid",
                    "-m",
                    "hi",
                ],
                "Could not find comment with UUID missing-uuid to reply to",
            ),
        ]:
            stderr = io.StringIO()
            with (
                contextlib.redirect_stderr(stderr),
                self.assertRaises(SystemExit) as error,
            ):
                gerrit_client.main(args)
            self.assertEqual(2, error.exception.code)
            self.assertIn(expected_err, stderr.getvalue())
        util_mock.assert_not_called()
        get_comments_mock.assert_called_once_with("example.org", "123")

    @mock.patch("gerrit_util.GetPatch", return_value=b"formatted patch\n")
    def test_patch_defaults(self, util_mock):
        with mock.patch("gerrit_client.sys.stdout") as stdout_mock:
            gerrit_client.main(
                [
                    "patch",
                    "--host",
                    "https://example.org/foo",
                    "--change",
                    "Ichange",
                ]
            )

        util_mock.assert_called_once_with(
            "example.org",
            "Ichange",
            revision="current",
            path=None,
            parent=None,
            context=None,
        )
        stdout_mock.buffer.write.assert_called_once_with(b"formatted patch\n")

    @mock.patch("gerrit_client.write_result")
    @mock.patch("gerrit_util.GetPatch", return_value=b"file patch\n")
    def test_patch_options(self, util_mock, write_result_mock):
        with mock.patch("gerrit_client.sys.stdout") as stdout_mock:
            gerrit_client.main(
                [
                    "patch",
                    "--host",
                    "https://example.org/foo",
                    "--change",
                    "123",
                    "--revision",
                    "7",
                    "--path",
                    "src/file name.cc",
                    "--parent",
                    "2",
                    "--context",
                    "0",
                    "--json_file",
                    "ignored.json",
                ]
            )

        util_mock.assert_called_once_with(
            "example.org",
            "123",
            revision="7",
            path="src/file name.cc",
            parent=2,
            context=0,
        )
        stdout_mock.buffer.write.assert_called_once_with(b"file patch\n")
        write_result_mock.assert_not_called()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG if "-v" in sys.argv else logging.ERROR
    )
    unittest.main()
