# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import hashlib

from recipe_engine import recipe_api


from dataclasses import dataclass, field

class Constants:
  def __init__(self):
    self.NONTRIVIAL_ROLL_FOOTER = 'Recipe-Nontrivial-Roll'
    self.MANUAL_CHANGE_FOOTER = 'Recipe-Manual-Change'
    self.BYPASS_FOOTER = 'Recipe-Tryjob-Bypass-Reason'
    self.SKIP_RETRY_FOOTER = 'Disable-Retries'
    self.CQ_DEPEND_FOOTER = 'Cq-Depend'
    self.ALL_VALID_FOOTERS = set([
        self.NONTRIVIAL_ROLL_FOOTER, self.MANUAL_CHANGE_FOOTER,
        self.BYPASS_FOOTER, self.SKIP_RETRY_FOOTER, self.CQ_DEPEND_FOOTER
    ])


constants = Constants()


@dataclass(frozen=True)
class SubmodulePathsResult:
  """Holds the results of submodule diff expansion."""
  # List of all affected files (including both main repository files
  # and the expanded files inside any checked-out submodules).
  affected_files: list[str] = field(default_factory=list)

  # Submodules that were not checked out by the builder's gclient config.
  unchecked_out_submodules: list[str] = field(default_factory=list)

  # Submodules that were deleted by the patch.
  deleted_submodules: list[str] = field(default_factory=list)

  # Submodules that were newly added by the patch.
  new_submodules: list[str] = field(default_factory=list)

  # Nested submodules that were detected (and thus skipped from recursion).
  nested_submodules: list[str] = field(default_factory=list)


class TryserverApi(recipe_api.RecipeApi):
  def __init__(self, *args, **kwargs):
    super(TryserverApi, self).__init__(*args, **kwargs)
    self._gerrit_change = None  # self.m.buildbucket.common_pb2.GerritChange
    self._gerrit_change_repo_url = None
    self._gerrit_change_repo_host = None
    self._gerrit_change_repo_project = None

    self._gerrit_info_initialized = False
    self._gerrit_change_target_ref = None
    self._gerrit_change_fetch_ref = None
    self._gerrit_change_owner = None
    self._change_footers = None
    self._gerrit_commit_message = None

  def initialize(self):
    changes = self.m.buildbucket.build.input.gerrit_changes
    if len(changes) == 1:
      self.set_change(changes[0])

  @property
  def valid_footers(self):  #pragma: nocover
    return constants.ALL_VALID_FOOTERS

  @property
  def constants(self):  #pragma: nocover
    # Nocover to be removed when callers (not within depot_tools) exercise this
    return constants

  @property
  def gerrit_change(self):
    """Returns current gerrit change, if there is exactly one.

    Returns a self.m.buildbucket.common_pb2.GerritChange or None.
    """
    return self._gerrit_change

  @property
  def gerrit_change_repo_url(self):
    """Returns canonical URL of the gitiles repo of the current Gerrit CL.

    Populated iff gerrit_change is populated.
    """
    return self._gerrit_change_repo_url

  @property
  def gerrit_change_repo_host(self):
    """Returns the host of the gitiles repo of the current Gerrit CL.

    Populated iff gerrit_change is populated.
    """
    return self._gerrit_change_repo_host

  @property
  def gerrit_change_repo_project(self):
    """Returns the project of the gitiles repo of the current Gerrit CL.

    Populated iff gerrit_change is populated.
    """
    return self._gerrit_change_repo_project

  @property
  def gerrit_change_owner(self):
    """Returns owner of the current Gerrit CL.

    Populated iff gerrit_change is populated.
    Is a dictionary with keys like "name".
    """
    self._ensure_gerrit_change_info()
    return self._gerrit_change_owner

  @property
  def gerrit_change_review_url(self):
    """Returns the review URL for the active patchset."""
    # Gerrit redirects to insert the project into the URL.
    gerrit_change = self._gerrit_change
    return 'https://%s/c/%s/%s' % (
          gerrit_change.host, gerrit_change.change, gerrit_change.patchset)

  def _ensure_gerrit_change_info(self):
    """Initializes extra info about gerrit_change, fetched from Gerrit server.

    Initializes _gerrit_change_target_ref and _gerrit_change_fetch_ref.

    May emit a step when called for the first time.
    """
    cl = self.gerrit_change
    if not cl:  # pragma: no cover
      return

    if self._gerrit_info_initialized:
      return

    td = self._test_data if self._test_data.enabled else {}
    mock_res = [{
      'branch': td.get('gerrit_change_target_ref', 'main'),
      'revisions': {
        '184ebe53805e102605d11f6b143486d15c23a09c': {
          '_number': str(cl.patchset),
          'ref': 'refs/changes/%02d/%d/%d' % (
              cl.change % 100, cl.change, cl.patchset),
        },
      },
      'owner': {
          'name': 'John Doe',
      },
    }]
    res = self.m.gerrit.get_changes(
        host='https://' + cl.host,
        query_params=[('change', cl.change)],
        # This list must remain static/hardcoded.
        # If you need extra info, either change it here (hardcoded) or
        # fetch separately.
        o_params=['ALL_REVISIONS', 'DOWNLOAD_COMMANDS'],
        limit=1,
        name='fetch current CL info',
        timeout=480,
        step_test_data=lambda: self.m.json.test_api.output(mock_res))[0]

    self._gerrit_change_target_ref = res['branch']
    if not self._gerrit_change_target_ref.startswith('refs/'):
      self._gerrit_change_target_ref = (
          'refs/heads/' + self._gerrit_change_target_ref)

    for rev in res['revisions'].values():
      if int(rev['_number']) == self.gerrit_change.patchset:
        self._gerrit_change_fetch_ref = rev['ref']
        break
    self._gerrit_change_owner = dict(res['owner'])
    self._gerrit_info_initialized = True

  @property
  def gerrit_change_fetch_ref(self):
    """Returns gerrit patch ref, e.g. "refs/heads/45/12345/6, or None.

    Populated iff gerrit_change is populated.
    """
    self._ensure_gerrit_change_info()
    return self._gerrit_change_fetch_ref

  @property
  def gerrit_change_target_ref(self):
    """Returns gerrit change destination ref, e.g. "refs/heads/main".

    Populated iff gerrit_change is populated.
    """
    self._ensure_gerrit_change_info()
    return self._gerrit_change_target_ref

  @property
  def gerrit_change_number(self):
    """Returns gerrit change patchset, e.g. 12345 for a patch ref of
    "refs/heads/45/12345/6".

    Populated iff gerrit_change is populated. Returns None if not populated.
    """
    self._ensure_gerrit_change_info()
    if not self._gerrit_change:  #pragma: nocover
      return None
    return int(self._gerrit_change.change)

  @property
  def gerrit_patchset_number(self):
    """Returns gerrit change patchset, e.g. 6 for a patch ref of
    "refs/heads/45/12345/6".

    Populated iff gerrit_change is populated Returns None if not populated..
    """
    self._ensure_gerrit_change_info()
    if not self._gerrit_change:  #pragma: nocover
      return None
    return int(self._gerrit_change.patchset)

  @property
  def is_tryserver(self):
    """Returns true iff we have a change to check out."""
    return (self.is_patch_in_git or self.is_gerrit_issue)

  @property
  def is_gerrit_issue(self):
    """Returns true iff the properties exist to match a Gerrit issue."""
    if self.gerrit_change:
      return True
    # TODO(tandrii): remove this, once nobody is using buildbot Gerrit Poller.
    return ('event.patchSet.ref' in self.m.properties and
            'event.change.url' in self.m.properties and
            'event.change.id' in self.m.properties)

  @property
  def is_patch_in_git(self):
    return (self.m.properties.get('patch_storage') == 'git' and
            self.m.properties.get('patch_repo_url') and
            self.m.properties.get('patch_ref'))

  def require_is_tryserver(self):
    if self.m.tryserver.is_tryserver:
      return

    status = self.m.step.EXCEPTION
    step_text = 'This recipe requires a gerrit CL for the source under test'
    if self.m.led.launched_by_led:
      status = self.m.step.FAILURE
      step_text += (
          "\n run 'led edit-cr-cl <source CL URL>' to attach a CL to test"
      )
    self.m.step.empty('not a tryjob', status=status, step_text=step_text)

  def get_files_affected_by_patch(self,
                                  patch_root,
                                  report_files_via_property=None,
                                  **kwargs):
    """Returns list of paths to files affected by the patch.

    Args:
      * patch_root: path relative to api.path['root'], usually obtained from
        api.gclient.get_gerrit_patch_root().
      * report_files_via_property: name of the output property to report the
        list of the files. If None (default), do not report.

    Returned paths will be relative to to api.path['root'].
    """
    cwd = self.m.context.cwd or self.m.path.start_dir / patch_root
    with self.m.context(cwd=cwd):
      step_result = self.m.git(
          '-c', 'core.quotePath=false', 'diff', '--cached', '--name-only',
          name='git diff to analyze patch',
          stdout=self.m.raw_io.output(),
          step_test_data=lambda:
            self.m.raw_io.test_api.stream_output('foo.cc'),
          **kwargs)
    paths = [self.m.path.join(patch_root, p.decode('utf-8')) for p in
             step_result.stdout.splitlines()]
    paths.sort()
    if self.m.platform.is_win:
      # Looks like "analyze" wants POSIX slashes even on Windows (since git
      # uses that format even on Windows).
      paths = [path.replace('\\', '/') for path in paths]
    step_result.presentation.logs['files'] = paths
    if report_files_via_property:
      step_result.presentation.properties[report_files_via_property] = {
        'total_count': len(paths),
        # Do not report too many because it might violate build size limits,
        # and isn't very useful anyway.
        'first_100': paths[:100],
      }

    return paths

  def get_files_affected_by_patch_with_submodules(
      self,
      patch_root,
      report_files_via_property=None,
      **kwargs) -> SubmodulePathsResult:
    """Returns a SubmodulePathsResult containing affected files and submodule metadata.

    This is an extended version of get_files_affected_by_patch that also detects
    and expands submodule diffs.
    """
    try:
      return self._get_files_affected_by_patch_with_submodules(
          patch_root,
          report_files_via_property=report_files_via_property,
          **kwargs)
    except Exception as ex:
      # Temporarily prevent any submodule expansion errors from failing the
      # build while this function is run as an experiment and is only
      # logging its results.
      self.m.step.empty('[Experimental] submodule expansion failed (ignored)',
                        status=self.m.step.WARNING,
                        step_text=str(ex),
                        raise_on_failure=False)
      return SubmodulePathsResult(affected_files=[],
                                  unchecked_out_submodules=[],
                                  deleted_submodules=[],
                                  new_submodules=[],
                                  nested_submodules=[])

  def _get_files_affected_by_patch_with_submodules(
      self,
      patch_root,
      report_files_via_property=None,
      **kwargs) -> SubmodulePathsResult:
    """Internal implementation of get_files_affected_by_patch_with_submodules.

    Args:
      * patch_root: path relative to api.path['root'], usually obtained from
        api.gclient.get_gerrit_patch_root().
      * report_files_via_property: name of the output property to report the
        list of the files. If None (default), do not report.
    """
    affected_files = []
    unchecked_out_submodules = []
    deleted_submodules = []
    new_submodules = []
    nested_submodules = []
    submodule_files = []
    submodules_to_process = []

    def parse_raw_diff(step_result):
      """Parses 'git diff --raw' output into (mode, old_sha, new_sha, path)."""
      NULL_SHA = '0' * 40
      for raw_line in step_result.stdout.splitlines():
        line = raw_line.decode('utf-8')
        # each line of a --raw diff is expected to begin with ':' and to have
        # a tab separating the metadata from the path to the modified file(s)
        # example: ":100644 100644 bcd1234 0123456 M file0"
        if line.startswith(':') and '\t' in line:
          # remove leading ':' and split metadata from path(s)
          meta, path = line[1:].split('\t', 1)
          meta_parts = meta.split()
          if len(meta_parts) != 5:
            raise ValueError(
                f"Unexpected git diff --raw metadata (expected 5 fields, got "
                f"{len(meta_parts)}): {meta!r}")
          old_mode, new_mode, old_sha, new_sha, status = meta_parts
          if status[0] in ('R', 'C'):
            # In Rename or Copy operation the path contains src_path\tdst_path
            # example: ":100644 100644 abcd123 1234567 R86 file1 file3"
            if '\t' not in path:
              raise ValueError(
                  f"Unexpected git diff --raw path for {status[0]} operation "
                  f"(expected tab-separated src and dst paths): {path!r}")
            src_path, dst_path = path.split('\t', 1)
            if status[0] == 'R':
              # Yield src_path as deleted for renames only (using its old_mode)
              yield old_mode, old_sha, NULL_SHA, src_path
            # Yield dst_path as added for both renames and copies
            yield new_mode, NULL_SHA, new_sha, dst_path
          else:
            # Statuses: A, D, M, T (change in type) and U (file is unmerged)
            yield new_mode, old_sha, new_sha, path

    def attach_submodule_log(presentation, files, log_name='submodule_files'):
      if files:
        files.sort()
        if self.m.platform.is_win:
          files = [path.replace('\\', '/') for path in files]
        presentation.logs[log_name] = files

    def finalize_and_log(presentation, files):
      files.sort()
      if self.m.platform.is_win:
        files = [path.replace('\\', '/') for path in files]

      if report_files_via_property:

        def format_prop_list(lst):
          sorted_lst = sorted(lst)
          if self.m.platform.is_win:
            sorted_lst = [p.replace('\\', '/') for p in sorted_lst]
          return {
              'total_count': len(sorted_lst),
              'first_100': sorted_lst[:100],
          }

        prop_dict = format_prop_list(files)
        prop_dict.update({
            'submodule_files':
            format_prop_list(submodule_files),
            'unchecked_out_submodules':
            format_prop_list(unchecked_out_submodules),
            'deleted_submodules':
            format_prop_list(deleted_submodules),
            'new_submodules':
            format_prop_list(new_submodules),
            'nested_submodules':
            format_prop_list(nested_submodules),
        })
        presentation.properties[report_files_via_property] = prop_dict
      presentation.logs['files'] = files
      return files

    cwd = self.m.context.cwd or self.m.path.start_dir / patch_root
    with self.m.context(cwd=cwd):
      step_result = self.m.git(
          '-c',
          'core.quotePath=false',
          'diff',
          '--cached',
          '--raw',
          name='[Experimental] git diff --raw to analyze patch',
          stdout=self.m.raw_io.output(add_output_log=True),
          step_test_data=lambda: self.m.raw_io.test_api.stream_output(''),
          **kwargs)

    # 1. Collect all affected paths (including submodule gitlinks) and identify submodules
    for mode, old_sha, new_sha, rel_path in parse_raw_diff(step_result):
      affected_files.append(self.m.path.join(patch_root, rel_path))
      if mode == '160000':
        submodules_to_process.append((old_sha, new_sha, rel_path))

    # 2. Process submodules if there are any
    if submodules_to_process:
      with self.m.context(cwd=cwd):
        with self.m.step.nest(
            '[Experimental] git diff submodules') as presentation:
          for old_sha, new_sha, rel_path in submodules_to_process:
            if new_sha.startswith('0' * 7):
              # If a submodule is deleted (new_commit starts with 0s), we skip
              # expanding its files.
              deleted_submodules.append(rel_path)
              continue

            submodule_dir = cwd / rel_path
            # If the submodule directory does not contain a .git file/directory,
            # it means the submodule was not checked out by this builder's
            # gclient/checkout configuration (e.g. platform-specific or
            # internal-only deps).
            if not self.m.path.exists(submodule_dir / '.git'):
              unchecked_out_submodules.append(rel_path)
              continue

            if old_sha.startswith('0' * 7):
              new_submodules.append(rel_path)
              # 4b825dc642cb6eb9a060e54bf8d69288fbee4904 is Git's empty tree hash.
              # Used to diff newly added submodules (which have a null old SHA).
              old_sha = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
            # this call to git diff is what actually expands the submodule
            sub_result = self.m.git(
                '-C',
                rel_path,
                'diff',
                '--raw',
                old_sha,
                new_sha,
                name=rel_path,
                stdout=self.m.raw_io.output(add_output_log=True),
                step_test_data=lambda: self.m.raw_io.test_api.stream_output(
                    ':100644 100644 1234567 89abcdef M\tsub_foo.cc'),
            )
            step_files = []
            for sub_mode, _, _, sub_path in parse_raw_diff(sub_result):
              # Do not recursively expand nested submodules because tryjob checkouts
              # often perform shallow syncs or only check out the tip commit, meaning older
              # revisions are missing locally.
              if sub_mode == '160000':
                nested_submodules.append('%s/%s' % (rel_path, sub_path))
              else:
                sub_file = self.m.path.join(patch_root, rel_path, sub_path)
                step_files.append(sub_file)
                submodule_files.append(sub_file)
                affected_files.append(sub_file)

            attach_submodule_log(sub_result.presentation, step_files)

          attach_submodule_log(presentation, unchecked_out_submodules,
                               'unchecked_out_submodules')
          attach_submodule_log(presentation, deleted_submodules,
                               'deleted_submodules')
          attach_submodule_log(presentation, new_submodules, 'new_submodules')
          attach_submodule_log(presentation, nested_submodules,
                               'nested_submodules')

          affected_files = finalize_and_log(presentation, affected_files)
    else:
      affected_files = finalize_and_log(step_result.presentation,
                                        affected_files)

    return SubmodulePathsResult(
        affected_files=affected_files,
        unchecked_out_submodules=unchecked_out_submodules,
        deleted_submodules=deleted_submodules,
        new_submodules=new_submodules,
        nested_submodules=nested_submodules,
    )

  def set_subproject_tag(self, subproject_tag):
    """Adds a subproject tag to the build.

    This can be used to distinguish between builds that execute different steps
    depending on what was patched, e.g. blink vs. pure chromium patches.
    """
    assert self.is_tryserver

    step_result = self.m.step('TRYJOB SET SUBPROJECT_TAG', cmd=None)
    step_result.presentation.properties['subproject_tag'] = subproject_tag
    step_result.presentation.step_text = subproject_tag

  def _set_failure_type(self, failure_type):
    if not self.is_tryserver:
      return

    # TODO(iannucci): add API to set properties regardless of the current step.
    step_result = self.m.step('TRYJOB FAILURE', cmd=None)
    step_result.presentation.properties['failure_type'] = failure_type
    step_result.presentation.step_text = failure_type
    step_result.presentation.status = 'FAILURE'

  def set_patch_failure_tryjob_result(self):
    """Mark the tryjob result as failure to apply the patch."""
    self._set_failure_type('PATCH_FAILURE')

  def set_compile_failure_tryjob_result(self):
    """Mark the tryjob result as a compile failure."""
    self._set_failure_type('COMPILE_FAILURE')

  def set_test_failure_tryjob_result(self):
    """Mark the tryjob result as a test failure.

    This means we started running actual tests (not prerequisite steps
    like checkout or compile), and some of these tests have failed.
    """
    self._set_failure_type('TEST_FAILURE')

  def set_invalid_test_results_tryjob_result(self):
    """Mark the tryjob result as having invalid test results.

    This means we run some tests, but the results were not valid
    (e.g. no list of specific test cases that failed, or too many
    tests failing, etc).
    """
    self._set_failure_type('INVALID_TEST_RESULTS')

  def set_test_timeout_tryjob_result(self):
    """Mark the tryjob result as a test timeout.

    This means tests were scheduled but didn't finish executing within the
    timeout.
    """
    self._set_failure_type('TEST_TIMEOUT')

  def set_test_expired_tryjob_result(self):
    """Mark the tryjob result as a test expiration.

    This means a test task expired and was never scheduled, most likely due to
    lack of capacity.
    """
    self._set_failure_type('TEST_EXPIRED')

  def get_footers(self, patch_text=None):
    """Retrieves footers from the patch description.

    footers are machine readable tags embedded in commit messages. See
    git-footers documentation for more information.
    """
    return self._get_footers(patch_text)

  def _ensure_gerrit_commit_message(self):
    """Fetch full commit message for Gerrit change."""
    if self._gerrit_commit_message:
      return

    self._ensure_gerrit_change_info()
    self._gerrit_commit_message = self.m.gerrit.get_change_description(
        'https://%s' % self.gerrit_change.host,
        self.gerrit_change_number,
        self.gerrit_patchset_number,
        timeout=480)

  def _get_footers(self, patch_text=None):
    if patch_text is not None:
      return self._get_footer_step(patch_text)
    if self._change_footers is not None:
      return self._change_footers
    if self.gerrit_change:
      self._ensure_gerrit_commit_message()
      self._change_footers = self._get_footer_step(self._gerrit_commit_message)
      return self._change_footers
    raise Exception(
        'No patch text or associated changelist, cannot get footers')  #pragma: nocover

  def _get_footer_step(self, patch_text):
    result = self.m.step(
        'parse description',
        [
            'python3',
            self.repo_resource('git_footers.py'),
            '--json',
            self.m.json.output(),
        ],
        stdin=self.m.raw_io.input(data=patch_text),
        step_test_data=lambda: self.m.json.test_api.output({}),
    )
    return result.json.output

  def get_footer(self, tag, patch_text=None):
    """Gets a specific tag from a CL description"""
    footers = self._get_footers(patch_text)
    return footers.get(tag, [])

  def normalize_footer_name(self, footer):
    return '-'.join([ word.title() for word in footer.strip().split('-') ])

  def get_change_description(self):
    """Gets the CL description."""
    self._ensure_gerrit_commit_message()
    return self._gerrit_commit_message

  def set_change(self, change):
    """Set the gerrit change for this module.

    Args:
      * change: a self.m.buildbucket.common_pb2.GerritChange.
    """
    self._gerrit_info_initialized = False
    self._gerrit_change = change
    gs_suffix = '-review.googlesource.com'
    host = change.host
    if host.endswith(gs_suffix):
      host = '%s.googlesource.com' % host[:-len(gs_suffix)]
    self._gerrit_change_repo_url = 'https://%s/%s' % (host, change.project)
    self._gerrit_change_repo_host = host
    self._gerrit_change_repo_project = change.project
