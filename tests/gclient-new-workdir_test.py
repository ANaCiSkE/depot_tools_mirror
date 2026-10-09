import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Load the script with hyphens in name as a module
test_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.abspath(
    os.path.join(test_dir, "..", "gclient-new-workdir.py")
)

# Ensure depot_tools root is in sys.path so gclient_utils can be imported
depot_tools_dir = os.path.dirname(script_path)
if depot_tools_dir not in sys.path:
    sys.path.insert(0, depot_tools_dir)

loader = importlib.machinery.SourceFileLoader(
    "gclient_new_workdir",
    script_path,
)
spec = importlib.util.spec_from_loader(loader.name, loader)
gclient_new_workdir = importlib.util.module_from_spec(spec)
loader.exec_module(gclient_new_workdir)


@unittest.skipIf(
    sys.platform == "win32", "gclient-new-workdir not supported on Windows"
)
class TestGclientNewWorkdir(unittest.TestCase):
    @patch("subprocess.check_output")
    @patch("os.stat")
    @patch("os.access")
    @patch("subprocess.check_call")
    @patch("os.makedirs")
    @patch("sys.exit")
    def test_abort_on_btrfs_fail(
        self,
        mock_exit,
        mock_makedirs,
        mock_check_call,
        mock_os_access,
        mock_os_stat,
        mock_check_output,
    ):
        # Setup mocks
        mock_check_output.return_value = b"btrfs"
        mock_stat_res = MagicMock()
        mock_stat_res.st_ino = 256
        mock_os_stat.return_value = mock_stat_res

        def mock_cc(args, **kwargs):
            _ = kwargs
            if len(args) > 2 and args[2] == "snapshot":
                raise OSError("Failed")

        mock_check_call.side_effect = mock_cc

        # Make mock_exit raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit(1)

        # Mock os.access to return True for diagnostics
        mock_os_access.return_value = True

        # Mock parse_options
        mock_args = MagicMock()
        mock_args.repository = "repo"
        mock_args.new_workdir = "dest"

        with patch.object(
            gclient_new_workdir, "parse_options", return_value=mock_args
        ):
            try:
                gclient_new_workdir.main()
            except SystemExit:
                pass  # Expected

        # Assertions
        mock_exit.assert_called_with(1)
        mock_makedirs.assert_not_called()

    @patch("subprocess.check_output")
    @patch("os.stat")
    @patch("os.access")
    @patch("os.makedirs")
    @patch("sys.exit")
    @patch.object(gclient_new_workdir, "support_copy_on_write")
    def test_fallback_on_non_subvolume(
        self,
        mock_support_cow,
        mock_exit,
        mock_makedirs,
        mock_os_access,
        mock_os_stat,
        mock_check_output,
    ):
        # Setup mocks
        mock_check_output.return_value = b"btrfs"
        mock_stat_res = MagicMock()
        mock_stat_res.st_ino = 123  # Not subvolume!
        mock_os_stat.return_value = mock_stat_res

        # Mock os.access to return True for diagnostics
        mock_os_access.return_value = True

        # Mock support_copy_on_write to stop execution after os.makedirs
        mock_support_cow.side_effect = SystemExit(0)

        # Mock parse_options
        mock_args = MagicMock()
        mock_args.repository = "repo"
        mock_args.new_workdir = "dest"

        with patch.object(
            gclient_new_workdir, "parse_options", return_value=mock_args
        ):
            try:
                gclient_new_workdir.main()
            except SystemExit:
                pass

        # Assertions
        mock_exit.assert_not_called()
        # It should proceed to os.makedirs with resolved path
        mock_makedirs.assert_called_with(os.path.realpath("dest"))

    @patch("subprocess.check_output")
    @patch("os.stat")
    @patch("os.access")
    @patch("subprocess.check_call")
    @patch("os.makedirs")
    @patch("sys.exit")
    @patch.object(gclient_new_workdir, "support_copy_on_write")
    def test_btrfs_snapshot_success(
        self,
        mock_support_cow,
        mock_exit,
        mock_makedirs,
        mock_check_call,
        mock_os_access,
        mock_os_stat,
        mock_check_output,
    ):
        # Setup mocks
        mock_check_output.return_value = b"btrfs"
        mock_stat_res = MagicMock()
        mock_stat_res.st_ino = 256
        mock_os_stat.return_value = mock_stat_res

        with patch.object(
            gclient_new_workdir, "btrfs_subvol_snapshot", return_value=True
        ):
            mock_support_cow.side_effect = SystemExit(0)

            mock_args = MagicMock()
            mock_args.repository = "repo"
            mock_args.new_workdir = "dest"

            with patch.object(
                gclient_new_workdir, "parse_options", return_value=mock_args
            ):
                try:
                    gclient_new_workdir.main()
                except SystemExit:
                    pass

        mock_makedirs.assert_not_called()

    @patch("subprocess.check_output")
    @patch("os.stat")
    @patch("os.access")
    @patch("subprocess.check_call")
    @patch("os.makedirs")
    @patch("sys.exit")
    def test_diagnostics_repo_not_readable(
        self,
        mock_exit,
        mock_makedirs,
        mock_check_call,
        mock_os_access,
        mock_os_stat,
        mock_check_output,
    ):
        # Setup mocks
        mock_check_output.return_value = b"btrfs"
        mock_stat_res = MagicMock()
        mock_stat_res.st_ino = 256
        mock_os_stat.return_value = mock_stat_res

        def mock_cc(args, **kwargs):
            _ = kwargs
            if args[2] == "snapshot":
                raise OSError("Failed")

        mock_check_call.side_effect = mock_cc

        # Make mock_exit raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit(1)

        # Mock os.access: False for repo (not readable)
        def side_effect(path, mode):
            if path == "repo" and mode == os.R_OK:
                return False
            return True

        mock_os_access.side_effect = side_effect

        # Mock parse_options
        mock_args = MagicMock()
        mock_args.repository = "repo"
        mock_args.new_workdir = "dest"

        with patch.object(
            gclient_new_workdir, "parse_options", return_value=mock_args
        ):
            try:
                gclient_new_workdir.main()
            except SystemExit:
                pass

        # Assertions
        mock_exit.assert_called_with(1)
        mock_makedirs.assert_not_called()

    @patch("subprocess.check_output")
    @patch("os.stat")
    @patch("os.access")
    @patch("subprocess.check_call")
    @patch("os.makedirs")
    @patch("sys.exit")
    def test_diagnostics_dest_not_writable(
        self,
        mock_exit,
        mock_makedirs,
        mock_check_call,
        mock_os_access,
        mock_os_stat,
        mock_check_output,
    ):
        # Setup mocks
        mock_check_output.return_value = b"btrfs"
        mock_stat_res = MagicMock()
        mock_stat_res.st_ino = 256
        mock_os_stat.return_value = mock_stat_res

        def mock_cc(args, **kwargs):
            _ = kwargs
            if args[2] == "snapshot":
                raise OSError("Failed")

        mock_check_call.side_effect = mock_cc

        # Make mock_exit raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit(1)

        # Mock os.access: False for dest parent (not writable)
        def side_effect(path, mode):
            if path == "dir" and mode == os.W_OK:
                return False
            return True

        mock_os_access.side_effect = side_effect

        # Mock parse_options
        mock_args = MagicMock()
        mock_args.repository = "repo"
        mock_args.new_workdir = "dir/dest"

        with patch.object(
            gclient_new_workdir, "parse_options", return_value=mock_args
        ):
            try:
                gclient_new_workdir.main()
            except SystemExit:
                pass

        # Assertions
        mock_exit.assert_called_with(1)
        mock_makedirs.assert_not_called()

    @patch("os.walk")
    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("os.symlink")
    @patch.object(gclient_new_workdir, "copy_on_write")
    @patch.object(gclient_new_workdir, "adopt_git_worktree")
    def test_main_detects_git_file(
        self,
        mock_adopt,
        mock_cow,
        mock_symlink,
        mock_makedirs,
        mock_exists,
        mock_walk,
    ):
        # Mock parse_options
        mock_args = MagicMock()
        mock_args.repository = "/fake/repo"
        mock_args.new_workdir = "/fake/dest"
        mock_args.copy_on_write = True
        mock_args.use_git_worktree = True
        mock_args.max_depth = None

        with patch.object(
            gclient_new_workdir, "parse_options", return_value=mock_args
        ):
            # Mock os.walk to return a directory
            mock_walk.return_value = [("/fake/repo", ["dir1"], [])]

            # Mock os.path.exists
            def exists_side_effect(path):
                if path == "/fake/repo/.gclient":
                    return True
                if path == "/fake/dest/.gclient":
                    return False
                if path == "/fake/repo/.git":
                    return True
                return False

            mock_exists.side_effect = exists_side_effect

            # Mock is_btrfs_subvolume to return False
            with patch.object(
                gclient_new_workdir, "is_btrfs_subvolume", return_value=False
            ):
                gclient_new_workdir.main()

            # Verify that adopt_git_worktree was called!
            mock_adopt.assert_called_once_with("/fake/repo", "/fake/dest")

    @patch("subprocess.call")
    def test_refresh_index_stat_cache(self, mock_call):
        gclient_new_workdir._refresh_index_stat_cache("/fake/dest")
        mock_call.assert_called_once_with(
            [
                "git",
                "-c",
                "core.checkStat=minimal",
                "update-index",
                "-q",
                "--refresh",
            ],
            cwd="/fake/dest",
        )


@unittest.skipIf(
    sys.platform == "win32", "gclient-new-workdir not supported on Windows"
)
class TestCopyGnArgs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = os.path.join(self._tmp.name, "repo")
        self.dest = os.path.join(self._tmp.name, "dest")
        os.makedirs(os.path.join(self.dest, "src"))

    def _write(self, path, contents):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(contents)

    def _read(self, path):
        with open(path) as f:
            return f.read()

    def test_copies_each_build_dir(self):
        default_args = os.path.join(
            self.repo, "src", "out", "Default", "args.gn"
        )
        android_args = os.path.join(
            self.repo, "src", "out", "Android", "args.gn"
        )
        self._write(default_args, "is_debug = true\n")
        self._write(android_args, 'target_os = "android"\n')
        # Build dirs without an args.gn are ignored.
        os.makedirs(os.path.join(self.repo, "src", "out", "NoArgs"))

        gclient_new_workdir.copy_gn_args(self.repo, self.dest)

        for src_args in (default_args, android_args):
            dest_args = os.path.join(
                self.dest, os.path.relpath(src_args, self.repo)
            )
            self.assertFalse(os.path.islink(dest_args))
            self.assertEqual(self._read(dest_args), self._read(src_args))
        self.assertFalse(
            os.path.exists(os.path.join(self.dest, "src", "out", "NoArgs"))
        )
        # The repository is left untouched.
        self.assertEqual(self._read(default_args), "is_debug = true\n")

    def test_keeps_existing_args(self):
        src_args = os.path.join(self.repo, "src", "out", "Default", "args.gn")
        dest_args = os.path.join(self.dest, "src", "out", "Default", "args.gn")
        self._write(src_args, "is_debug = true\n")
        self._write(dest_args, "is_debug = false\n")

        gclient_new_workdir.copy_gn_args(self.repo, self.dest)

        self.assertEqual(self._read(dest_args), "is_debug = false\n")

    def test_keeps_existing_symlink(self):
        src_args = os.path.join(self.repo, "src", "out", "Default", "args.gn")
        dest_args = os.path.join(self.dest, "src", "out", "Default", "args.gn")
        other = os.path.join(self._tmp.name, "other_args.gn")
        self._write(src_args, "is_debug = true\n")
        self._write(other, "is_debug = false\n")
        os.makedirs(os.path.dirname(dest_args))
        os.symlink(other, dest_args)

        gclient_new_workdir.copy_gn_args(self.repo, self.dest)

        self.assertEqual(os.readlink(dest_args), other)
        self.assertEqual(self._read(other), "is_debug = false\n")

    def test_skips_build_dir_shared_through_symlink(self):
        src_args = os.path.join(self.repo, "src", "out", "Default", "args.gn")
        self._write(src_args, "is_debug = true\n")
        # A symlinked out/ copied as-is points at the repository's out/.
        os.symlink(
            os.path.join(self.repo, "src", "out"),
            os.path.join(self.dest, "src", "out"),
        )

        gclient_new_workdir.copy_gn_args(self.repo, self.dest)

        self.assertEqual(self._read(src_args), "is_debug = true\n")

    @patch("os.walk")
    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("os.symlink")
    @patch.object(gclient_new_workdir, "copy_gn_args")
    def _run_main(
        self,
        copy_gn_args_flag,
        mock_copy,
        mock_symlink,
        mock_makedirs,
        mock_exists,
        mock_walk,
    ):
        mock_args = MagicMock()
        mock_args.repository = "/fake/repo"
        mock_args.new_workdir = "/fake/dest"
        mock_args.copy_on_write = False
        mock_args.max_depth = None
        mock_args.copy_gn_args = copy_gn_args_flag
        mock_walk.return_value = []
        mock_exists.side_effect = lambda path: path == "/fake/repo/.gclient"
        with (
            patch.object(
                gclient_new_workdir, "parse_options", return_value=mock_args
            ),
            patch.object(
                gclient_new_workdir, "is_btrfs_subvolume", return_value=False
            ),
        ):
            self.assertEqual(gclient_new_workdir.main(), 0)
        return mock_copy

    def test_main_copies_gn_args_when_requested(self):
        self._run_main(True).assert_called_once_with("/fake/repo", "/fake/dest")

    def test_main_does_not_copy_gn_args_by_default(self):
        self._run_main(False).assert_not_called()


if __name__ == "__main__":
    unittest.main()
