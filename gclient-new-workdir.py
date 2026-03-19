#!/usr/bin/env python3
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Usage:
#    gclient-new-workdir.py [options] <repository> <new_workdir>
#

import argparse
import os
import random
import shutil
import subprocess
import sys
import textwrap

import gclient_utils
import git_common


def parse_options():
    if sys.platform == 'win32':
        print(
            'ERROR: This script cannot run on Windows because it uses symlinks.'
        )
        sys.exit(1)
    if gclient_utils.IsEnvCog():
        print('ERROR: This script cannot run in non-git environment.')
        sys.exit(1)

    parser = argparse.ArgumentParser(description='''Clone an existing '''
    '''gclient workspace, taking care of all sub-repositories.''')
    parser.add_argument('repository',
                        type=os.path.abspath,
                        help='should contain a .gclient file')
    parser.add_argument('new_workdir', help='must not exist')
    parser.add_argument(
        '--use-git-worktree',
        action='store_true',
        default=False,
        help='''Use git worktree instead of using symlinks for .git folders.''',
    )
    parser.add_argument(
        '--use-git-symlinks',
        action='store_false',
        dest='use_git_worktree',
        help='''Use symlinks for .git folders instead of using git worktree.''',
    )
    parser.add_argument(
        '--reflink',
        action='store_true',
        default=None,
        help='''Force use of a copy-on-write flag when copying for better '''
        '''performance and disk utilization. This is the default behavior on '''
        '''supported copy-on-write FS like btrfs, ZFS, or APFS.''')
    parser.add_argument(
        '--no-reflink',
        action='store_false',
        dest='reflink',
        help='''Force not to use a copy-on-write flag when copying even on a '''
        '''supported copy-on-write FS like btrfs, ZFS, or APFS.''')
    parser.add_argument(
        '--link-root-git-repo-only',
        action='store_true',
        default=None,
        help='''Force linking only root repository's .git e.g. chromium/src '''
        '''for better performance. This is the default behavior on supported '''
        '''copy-on-write FS like btrfs, ZFS, or APFS.''')
    parser.add_argument('--link-all-git-sub-repos',
                        action='store_false',
                        dest='link_root_git_repo_only',
                        help='''Force linking .git for all sub-repositories.''')
    args = parser.parse_args()

    if not os.path.exists(args.repository):
        parser.error('Repository "%s" does not exist.' % args.repository)

    gclient = os.path.join(args.repository, '.gclient')
    if not os.path.exists(gclient):
        parser.error('No .gclient file at "%s".' % gclient)

    if os.path.exists(args.new_workdir):
        parser.error('New workdir "%s" already exists.' % args.new_workdir)

    return args


def cp_copy_on_write_flag():
    return '-c' if sys.platform == 'darwin' else '--reflink'


def support_copy_on_write(src, dest):
    # Use of a copy-on-write flag always succeeds when 'src' is a symlink or a directory
    assert os.path.isfile(src) and not os.path.islink(src)
    try:
        subprocess.check_output(
            ['cp', '-a', cp_copy_on_write_flag(), src, dest],
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return False
    finally:
        if os.path.isfile(dest):
            os.remove(dest)
    return True


def try_btrfs_subvol_snapshot(src, dest):
    try:
        subprocess.check_call(['btrfs', 'subvol', 'snapshot', src, dest],
                              stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, OSError):
        return False
    assert os.path.exists(dest)
    return True


def real_git_dir(repo_path):
    relative_git_dir = (
        subprocess.check_output(
            ['git', 'rev-parse', '--git-dir'], cwd=repo_path
        )
        .decode()
        .strip()
    )
    return os.path.realpath(os.path.join(repo_path, relative_git_dir))


def link_git_repo(src, dest, reflink):
    print('Linking: %s/.git' % src)
    src_git_dir = real_git_dir(src)
    dest_git_dir = os.path.join(dest, '.git')
    git_common.make_workdir(src_git_dir, dest_git_dir)
    if reflink:
        subprocess.check_call(
            [
                'cp',
                '-a',
                cp_copy_on_write_flag(),
                os.path.join(src_git_dir, 'index'),
                os.path.join(dest_git_dir, 'index'),
            ]
        )
        # Detach the HEAD ref without checking out files or updating the index.
        subprocess.check_call(
            ['git', 'update-ref', '--no-deref', 'HEAD', 'HEAD'], cwd=dest
        )
    else:
        print('Running: git checkout --detach -f %s' % dest)
        subprocess.check_call(['git', 'checkout', '--detach', '-f'], cwd=dest)


def adopt_git_worktree(src, dest):
    assert os.path.exists(dest)
    # Rename the existing directory since `git worktree add` won't work if the
    # worktree directory already exists even with the `--force` flag.
    tmp_dest = os.path.join(
        os.path.dirname(dest),
        'tmp-' + os.path.basename(dest) + '-' + '%08x' % random.getrandbits(32),
    )
    os.rename(dest, tmp_dest)
    # Run `git worktree add --no-checkout` to create the worktree without
    # touching any files in the worktree.
    print('Running: git worktree add %s --no-checkout -d -f' % dest)
    subprocess.check_call(
        ['git', 'worktree', 'add', dest, '--no-checkout', '-d', '-f'], cwd=src
    )
    # Move the .git file from the worktree to the temporary directory and move
    # the temporary directory back to the worktree directory. Note that the .git
    # file is different from the worktree's real .git directory used below.
    shutil.move(os.path.join(dest, '.git'), tmp_dest)
    shutil.rmtree(dest)
    os.rename(tmp_dest, dest)
    # Copy the index so that the worktree is aware of files in the repository.
    subprocess.check_call(
        [
            'cp',
            '-a',
            cp_copy_on_write_flag(),
            os.path.join(real_git_dir(src), 'index'),
            os.path.join(real_git_dir(dest), 'index'),
        ]
    )


def create_git_worktree(src, workdir):
    print('Running: git worktree add %s -d -f' % workdir)
    subprocess.check_call(
        ['git', 'worktree', 'add', workdir, '-d', '-f'], cwd=src
    )


def main():
    args = parse_options()

    used_btrfs_subvol_snapshot = False
    if try_btrfs_subvol_snapshot(args.repository, args.new_workdir):
        # If btrfs is being used, reflink support is always present, and there's
        # no benefit to not using it.
        args.reflink = True
        used_btrfs_subvol_snapshot = True
    else:
        os.makedirs(args.new_workdir)

    # If any of the operations below fail, we want to clean up the new workdir.
    try:
        gclient = os.path.realpath(os.path.join(args.repository, '.gclient'))
        new_gclient = os.path.join(args.new_workdir, '.gclient')

        if args.reflink is None:
            args.reflink = support_copy_on_write(gclient, new_gclient)
            if args.reflink:
                print('Copy-on-write support is detected.')

        if not os.path.exists(new_gclient):
            os.symlink(gclient, new_gclient)

        if args.reflink and args.link_root_git_repo_only is None:
            # Since we're doing a btrfs subvolume snapshot or reflink copy, the
            # sub-repositories will already be present in the copy, and we only
            # need to link the .git directory for the root repository.
            args.link_root_git_repo_only = True

        for root, dirs, _ in os.walk(args.repository):
            if '.git' in dirs:
                workdir = root.replace(args.repository, args.new_workdir, 1)

                if args.reflink:
                    if not os.path.exists(workdir):
                        print('Copying: %s' % workdir)
                        subprocess.check_call(
                            ['cp', '-a', cp_copy_on_write_flag(), root, workdir]
                        )
                    shutil.rmtree(os.path.join(workdir, '.git'))

                if args.use_git_worktree:
                    if args.reflink:
                        adopt_git_worktree(root, workdir)
                    else:
                        create_git_worktree(root, workdir)
                else:
                    link_git_repo(root, workdir, reflink=args.reflink)

                # Break out of the for loop if we're only linking the root git
                # repository's .git folder and using copy-on-write since all the
                # sub-repositories will already be copied and we are done here.
                # Otherwise, we can't avoid visiting all sub-repositories for
                # checking out the files with git.
                if args.reflink and args.link_root_git_repo_only:
                    break

        if args.reflink:
            print(
                textwrap.dedent(
                    '''\
        The repo was copied using copy-on-write, and the artifacts were retained.
        More details on http://crbug.com/721585.

        Depending on your usage pattern, you might want to do "gn gen"
        on the output directories. More details: http://crbug.com/723856.'''
                )
            )
    except Exception as e:
        print(f'Error: {e}')
        print(f'Cleaning up {args.new_workdir}')
        if used_btrfs_subvol_snapshot:
            subprocess.check_call(
                ['btrfs', 'subvol', 'delete', args.new_workdir]
            )
        else:
            shutil.rmtree(args.new_workdir, ignore_errors=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
