#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Configuration, settings, and low-level git primitives for git cl."""

import logging
import os
import sys
from typing import NoReturn

import gclient_utils
import scm
import subprocess2

DEPOT_TOOLS = os.path.dirname(os.path.abspath(__file__))
DESCRIPTION_BACKUP_FILE = ".git_cl_description_backup"

# Valid extensions for files we want to lint.
DEFAULT_LINT_REGEX = r"(.*\.cpp|.*\.cc|.*\.h)"
DEFAULT_LINT_IGNORE_REGEX = r"$^"


def DieWithError(message, change_desc=None) -> NoReturn:
    if change_desc:
        SaveDescriptionBackup(change_desc)
        print(
            "\n ** Content of CL description **\n"
            f"{'=' * 72}\n"
            f"{change_desc.description}\n"
            f"{'=' * 72}\n"
        )

    print(message, file=sys.stderr)
    sys.exit(1)


def SaveDescriptionBackup(change_desc):
    backup_path = os.path.join(DEPOT_TOOLS, DESCRIPTION_BACKUP_FILE)
    print(f"\nsaving CL description to {backup_path}\n")
    with open(backup_path, "wb") as backup_file:
        backup_file.write(change_desc.description.encode("utf-8"))


def GetNoGitPagerEnv():
    env = os.environ.copy()
    # 'cat' is a magical git string that disables pagers on all platforms.
    env["GIT_PAGER"] = "cat"
    return env


def RunCommand(args, error_ok=False, error_message=None, shell=False, **kwargs):
    try:
        stdout = subprocess2.check_output(args, shell=shell, **kwargs)
        return stdout.decode("utf-8", "replace")
    except subprocess2.CalledProcessError as e:
        logging.debug("Failed running %s", args)
        if not error_ok:
            message = error_message or e.stdout.decode("utf-8", "replace") or ""
            DieWithError('Command "%s" failed.\n%s' % (" ".join(args), message))
        out = e.stdout.decode("utf-8", "replace")
        if e.stderr:
            out += e.stderr.decode("utf-8", "replace")
        return out


def RunGit(args, **kwargs) -> str:
    """Returns stdout."""
    return RunCommand(["git"] + args, **kwargs)


def RunGitWithCode(args, suppress_stderr=False, cwd=None):
    """Returns return code and stdout."""
    if suppress_stderr:
        stderr = subprocess2.DEVNULL
    else:
        stderr = sys.stderr
    try:
        (out, _), code = subprocess2.communicate(
            ["git"] + args,
            env=GetNoGitPagerEnv(),
            stdout=subprocess2.PIPE,
            stderr=stderr,
            cwd=cwd,
        )
        return code, out.decode("utf-8", "replace")
    except subprocess2.CalledProcessError as e:
        logging.debug("Failed running %s", ["git"] + args)
        return e.returncode, e.stdout.decode("utf-8", "replace")


def RunGitSilent(args, cwd=None):
    """Returns stdout, suppresses stderr and ignores the return code."""
    return RunGitWithCode(args, suppress_stderr=True, cwd=cwd)[1]


def _SplitArgsByCmdLineLimit(args):
    """Splits a list of arguments into shorter lists that fit within the command
    line limit."""
    # The maximum command line length is 32768 characters on Windows and 2097152
    # characters on other platforms. Use a lower limit to be safe.
    command_line_limit = 30000 if sys.platform.startswith("win32") else 2000000

    batch_args = []
    batch_length = 0
    for arg in args:
        # Add 1 to account for the space between arguments.
        arg_length = len(arg) + 1
        # If adding the current argument would exceed the command line limit,
        # yield the current batch and start a new one.
        if batch_length + arg_length > command_line_limit and batch_args:
            yield batch_args
            batch_args = []
            batch_length = 0

        batch_args.append(arg)
        batch_length += arg_length

    if batch_args:
        yield batch_args


def RunGitDiffCmd(
    diff_type, upstream_commit, files, allow_prefix=False, **kwargs
):
    """Generates and runs diff command."""
    # Generate diff for the current branch's changes.
    diff_cmd = [
        "-c",
        "core.quotePath=false",
        "diff",
        "--no-ext-diff",
        "--no-renames",
    ]

    if allow_prefix:
        # explicitly setting --src-prefix and --dst-prefix is necessary in the
        # case that diff.noprefix is set in the user's git config.
        diff_cmd += ["--src-prefix=a/", "--dst-prefix=b/"]
    else:
        diff_cmd += ["--no-prefix"]

    diff_cmd += diff_type
    diff_cmd += [upstream_commit, "--"]

    if not files:
        return RunGit(diff_cmd, **kwargs)

    for file in files:
        if file != "-" and not os.path.isdir(file) and not os.path.isfile(file):
            DieWithError('Argument "%s" is not a file or a directory' % file)

    output = ""
    for files_batch in _SplitArgsByCmdLineLimit(files):
        output += RunGit(diff_cmd + files_batch, **kwargs)

    return output


def FindCodereviewSettingsFile(filename="codereview.settings", root=None):
    """Finds the given file starting in the cwd and going up.

    Only looks up to the top of the repository unless an
    'inherit-review-settings-ok' file exists in the root of the repository.
    """
    inherit_ok_file = "inherit-review-settings-ok"
    cwd = os.getcwd()
    if root is None:
        root = settings.GetRoot()
    if os.path.isfile(os.path.join(root, inherit_ok_file)):
        root = None
    while True:
        if os.path.isfile(os.path.join(cwd, filename)):
            return open(os.path.join(cwd, filename), encoding="utf-8")
        if cwd == root:
            break
        parent_dir = os.path.dirname(cwd)
        if parent_dir == cwd:
            # We hit the system root directory.
            break
        cwd = parent_dir
    return None


def LoadCodereviewSettingsFromFile(fileobj, root=None):
    """Parses a codereview.settings file and updates hooks."""
    keyvals = gclient_utils.ParseCodereviewSettingsContent(fileobj.read())
    if root is None:
        root = settings.GetRoot()

    def SetProperty(name, setting):
        fullname = f"rietveld.{name}"
        if setting in keyvals:
            scm.GIT.SetConfig(root, fullname, keyvals[setting])
        else:
            scm.GIT.SetConfig(root, fullname, None, modify_all=True)

    if not keyvals.get("GERRIT_HOST", False):
        SetProperty("server", "CODE_REVIEW_SERVER")
    # Only server setting is required. Other settings can be absent.
    # In that case, we ignore errors raised during option deletion attempt.
    SetProperty("cc", "CC_LIST")
    SetProperty("tree-status-url", "STATUS")
    SetProperty("viewvc-url", "VIEW_VC")
    SetProperty("bug-prefix", "BUG_PREFIX")
    SetProperty("cpplint-regex", "LINT_REGEX")
    SetProperty("cpplint-ignore-regex", "LINT_IGNORE_REGEX")
    SetProperty("run-post-upload-hook", "RUN_POST_UPLOAD_HOOK")
    SetProperty("format-full-by-default", "FORMAT_FULL_BY_DEFAULT")

    if "FORMAT_JS" in keyvals:
        scm.GIT.SetConfig(root, "cl.format-js", keyvals["FORMAT_JS"])

    if "GERRIT_HOST" in keyvals:
        scm.GIT.SetConfig(root, "gerrit.host", keyvals["GERRIT_HOST"])

    if "GERRIT_SQUASH_UPLOADS" in keyvals:
        scm.GIT.SetConfig(
            root, "gerrit.squash-uploads", keyvals["GERRIT_SQUASH_UPLOADS"]
        )

    if "GERRIT_SKIP_ENSURE_AUTHENTICATED" in keyvals:
        scm.GIT.SetConfig(
            root,
            "gerrit.skip-ensure-authenticated",
            keyvals["GERRIT_SKIP_ENSURE_AUTHENTICATED"],
        )

    if "PUSH_URL_CONFIG" in keyvals and "ORIGIN_URL_CONFIG" in keyvals:
        # should be of the form
        # PUSH_URL_CONFIG: url.ssh://gitrw.chromium.org.pushinsteadof
        # ORIGIN_URL_CONFIG: http://src.chromium.org/git
        scm.GIT.SetConfig(
            root,
            keyvals["PUSH_URL_CONFIG"],
            keyvals["ORIGIN_URL_CONFIG"],
        )


class Settings:
    """Manages and caches the repository settings and configurations."""

    def __init__(self):
        self.cc = None
        self.root = None
        self.git_dir = None
        self.tree_status_url = None
        self.viewvc_url = None
        self.updated = False
        self.is_gerrit = None
        self.squash_gerrit_uploads = None
        self.gerrit_skip_ensure_authenticated = None
        self.git_editor = None
        self.format_full_by_default = None
        self.is_status_commit_order_by_date = None
        self.format_js = None

    def _LazyUpdateIfNeeded(self):
        """Updates the settings from a codereview.settings file, if available."""
        if self.updated:
            return

        root = self.GetRoot()
        # The only value that actually changes the behavior is
        # autoupdate = "false". Everything else means "true".
        autoupdate = scm.GIT.GetConfig(root, "rietveld.autoupdate", "").lower()

        if autoupdate != "false":
            cr_settings_file = FindCodereviewSettingsFile(root=root)
            if cr_settings_file:
                with cr_settings_file:
                    LoadCodereviewSettingsFromFile(cr_settings_file, root=root)

        self.updated = True

    @staticmethod
    def GetRelativeRoot():
        return scm.GIT.GetCheckoutRoot(".")

    def GetRoot(self):
        if self.root is None:
            self.root = os.path.realpath(
                os.path.abspath(self.GetRelativeRoot())
            )
        return self.root

    def GetGitDir(self):
        if self.git_dir is None:
            self.git_dir = scm.GIT.GetCommonGitDir(".")
        return self.git_dir

    def GetTreeStatusUrl(self, error_ok=False):
        if not self.tree_status_url:
            self.tree_status_url = self._GetConfig("rietveld.tree-status-url")
            if self.tree_status_url is None and not error_ok:
                DieWithError(
                    "You must configure your tree status URL by running "
                    '"git cl config".'
                )
        return self.tree_status_url

    def GetViewVCUrl(self) -> str:
        if not self.viewvc_url:
            self.viewvc_url = self._GetConfig("rietveld.viewvc-url")
        return self.viewvc_url

    def GetBugPrefix(self):
        return self._GetConfig("rietveld.bug-prefix")

    def GetRunPostUploadHook(self):
        run_post_upload_hook = self._GetConfig("rietveld.run-post-upload-hook")
        return run_post_upload_hook == "True"

    def GetDefaultCCList(self):
        return self._GetConfig("rietveld.cc")

    def GetSquashGerritUploads(self):
        """Returns True if uploads to Gerrit should be squashed by default."""
        if self.squash_gerrit_uploads is None:
            self.squash_gerrit_uploads = self.GetSquashGerritUploadsOverride()
        if self.squash_gerrit_uploads is None:
            # Default is squash now (http://crbug.com/611892#c23).
            self.squash_gerrit_uploads = (
                self._GetConfig("gerrit.squash-uploads").lower() != "false"
            )
        return self.squash_gerrit_uploads

    def GetSquashGerritUploadsOverride(self):
        """Return True or False if codereview.settings should be overridden.

        Returns None if no override has been defined.
        """
        # See also http://crbug.com/611892#c23
        result = self._GetConfig("gerrit.override-squash-uploads").lower()
        if result == "true":
            return True
        if result == "false":
            return False
        return None

    def GetIsGerrit(self):
        """Return True if gerrit.host is set."""
        if self.is_gerrit is None:
            val = self._GetConfig("gerrit.host")
            self.is_gerrit = bool(val) and val.lower() != "false"
        return self.is_gerrit

    def GetGerritSkipEnsureAuthenticated(self):
        """Return True if EnsureAuthenticated should not be done for Gerrit
        uploads."""
        if self.gerrit_skip_ensure_authenticated is None:
            self.gerrit_skip_ensure_authenticated = (
                self._GetConfig("gerrit.skip-ensure-authenticated").lower()
                == "true"
            )
        return self.gerrit_skip_ensure_authenticated

    def GetGitEditor(self):
        """Returns the editor specified in the git config, or None if none is."""
        if self.git_editor is None:
            # Git requires single quotes for paths with spaces. We need to
            # replace them with double quotes for Windows to treat such paths as
            # a single path.
            self.git_editor = self._GetConfig("core.editor").replace("'", '"')
        return self.git_editor or None

    def GetLintRegex(self):
        return self._GetConfig("rietveld.cpplint-regex", DEFAULT_LINT_REGEX)

    def GetLintIgnoreRegex(self):
        return self._GetConfig(
            "rietveld.cpplint-ignore-regex", DEFAULT_LINT_IGNORE_REGEX
        )

    def GetFormatFullByDefault(self):
        if self.format_full_by_default is None:
            self.format_full_by_default = self._GetConfigBool(
                "rietveld.format-full-by-default"
            )
        return self.format_full_by_default

    def IsStatusCommitOrderByDate(self):
        if self.is_status_commit_order_by_date is None:
            self.is_status_commit_order_by_date = self._GetConfigBool(
                "cl.date-order"
            )
        return self.is_status_commit_order_by_date

    def GetFormatJs(self):
        if self.format_js is None:
            self.format_js = self._GetConfig("cl.format-js").lower() == "true"
        return self.format_js

    def _GetConfig(self, key, default=""):
        self._LazyUpdateIfNeeded()
        return scm.GIT.GetConfig(self.GetRoot(), key, default)

    def _GetConfigBool(self, key) -> bool:
        self._LazyUpdateIfNeeded()
        return scm.GIT.GetConfigBool(self.GetRoot(), key)


settings = Settings()
