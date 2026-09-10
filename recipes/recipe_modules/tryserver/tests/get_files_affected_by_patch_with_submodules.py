# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  "tryserver",
  "recipe_engine/assertions",
  "recipe_engine/path",
  "recipe_engine/platform",
  "recipe_engine/properties",
  "recipe_engine/raw_io",
]


def RunSteps(api):
  result = api.tryserver.get_files_affected_by_patch_with_submodules(
    api.properties["patch_root"],
    report_files_via_property=api.properties.get("report_files_via_property"),
  )

  # Assert on the affected files
  api.assertions.assertCountEqual(
    result.affected_files, api.properties["expected_files"]
  )

  # Assert on the other fields of the SubmodulePathsResult if specified in properties
  if "expected_unchecked_out_submodules" in api.properties:
    api.assertions.assertCountEqual(
      result.unchecked_out_submodules,
      api.properties["expected_unchecked_out_submodules"],
    )
  if "expected_deleted_submodules" in api.properties:
    api.assertions.assertCountEqual(
      result.deleted_submodules,
      api.properties["expected_deleted_submodules"],
    )
  if "expected_new_submodules" in api.properties:
    api.assertions.assertCountEqual(
      result.new_submodules, api.properties["expected_new_submodules"]
    )
  if "expected_nested_submodules" in api.properties:
    api.assertions.assertCountEqual(
      result.nested_submodules, api.properties["expected_nested_submodules"]
    )


def GenTests(api):

  def has_nested_submodules_log(check, steps, step_name):
    check("nested_submodules" in steps[step_name].logs)

  def has_unchecked_out_submodules_log(check, steps, step_name):
    check("unchecked_out_submodules" in steps[step_name].logs)

  def has_deleted_submodules_log(check, steps, step_name):
    check("deleted_submodules" in steps[step_name].logs)

  def has_new_submodules_log(check, steps, step_name):
    check("new_submodules" in steps[step_name].logs)

  yield api.test(
    "submodule",
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(
        "\n:100644 100644 1234567 89abcdef M\tsub_foo.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub", "sub/sub_foo.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-added",
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(":000000 160000 0000000 89abcdef A\tsub"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(":000000 100644 0000000 89abcdef A\tsub_foo.cc"),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub", "sub/sub_foo.cc"],
      expected_new_submodules=["sub"],
    ),
    api.post_check(
      has_new_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-deleted",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(":160000 160000 1234567 0000000 D\tsub"),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub"],
      expected_deleted_submodules=["sub"],
    ),
    api.post_check(
      has_deleted_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-none",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(":100644 100644 1234567 89abcdef M\tfoo.cc"),
    ),
    api.properties(
      patch_root="",
      expected_files=["foo.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-win",
    api.platform("win", 32),
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(
        "\n:100644 100644 1234567 89abcdef M\tsub_foo.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub", "sub/sub_foo.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-nested",
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(
        "\n:100644 160000 1234567 89abcdef M\tnested_sub\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub"],
      expected_nested_submodules=["sub/nested_sub"],
    ),
    api.post_check(
      has_nested_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-unchecked-out",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub"],
      expected_unchecked_out_submodules=["sub"],
    ),
    api.post_check(
      has_unchecked_out_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-unchecked-out-win",
    api.platform("win", 32),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub"],
      expected_unchecked_out_submodules=["sub"],
    ),
    api.post_check(
      has_unchecked_out_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-expansion-failed",
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.step_data("[Experimental] git diff submodules.sub", retcode=1),
    api.properties(
      patch_root="",
      expected_files=[],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-deleted-win",
    api.platform("win", 32),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(":160000 160000 1234567 0000000 D\tsub"),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub"],
      expected_deleted_submodules=["sub"],
    ),
    api.post_check(
      has_deleted_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-added-win",
    api.platform("win", 32),
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(":000000 160000 0000000 89abcdef A\tsub"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(":000000 100644 0000000 89abcdef A\tsub_foo.cc"),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub", "sub/sub_foo.cc"],
      expected_new_submodules=["sub"],
    ),
    api.post_check(
      has_new_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-nested-win",
    api.platform("win", 32),
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(
        "\n:100644 160000 1234567 89abcdef M\tnested_sub\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub"],
      expected_nested_submodules=["sub/nested_sub"],
    ),
    api.post_check(
      has_nested_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-none-win",
    api.platform("win", 32),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(
        ":100644 100644 1234567 89abcdef M\tfoo\\bar.cc"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["foo/bar.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-report-property",
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(
        "\n:100644 100644 1234567 89abcdef M\tsub_foo.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      report_files_via_property="affected-files",
      expected_files=["sub", "sub/sub_foo.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-report-property-win",
    api.platform("win", 32),
    api.path.files_exist(api.path.start_dir / "sub" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output("\n:100644 160000 1234567 89abcdef M\tsub\n"),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub",
      api.raw_io.stream_output(
        "\n:100644 100644 1234567 89abcdef M\tsub_foo.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      report_files_via_property="affected-files",
      expected_files=["sub", "sub/sub_foo.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-none-report-property",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(":100644 100644 1234567 89abcdef M\tfoo.cc"),
    ),
    api.properties(
      patch_root="",
      report_files_via_property="affected-files",
      expected_files=["foo.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "submodule-renamed",
    api.path.files_exist(api.path.start_dir / "sub_dst" / ".git"),
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(
        "\n:160000 160000 1234567 89abcdef R100\tsub_src\tsub_dst\n"
      ),
    ),
    api.step_data(
      "[Experimental] git diff submodules.sub_dst",
      api.raw_io.stream_output(
        "\n:100644 100644 1234567 89abcdef M\tsub_foo.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["sub_src", "sub_dst", "sub_dst/sub_foo.cc"],
      expected_deleted_submodules=["sub_src"],
      expected_new_submodules=["sub_dst"],
    ),
    api.post_check(
      has_deleted_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(
      has_new_submodules_log, "[Experimental] git diff submodules"
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "file-renamed",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(
        "\n:100644 100644 1234567 89abcdef R100\tfoo_src.cc\tfoo_dst.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["foo_src.cc", "foo_dst.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "file-copied",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      api.raw_io.stream_output(
        "\n:100644 100644 1234567 89abcdef C090\tfoo_src.cc\tfoo_dst.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=["foo_dst.cc"],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "malformed-diff-parts",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      # missing new_sha and status
      api.raw_io.stream_output(":100644 100644 1234567\tfoo.cc\n"),
    ),
    api.properties(
      patch_root="",
      expected_files=[],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )

  yield api.test(
    "malformed-diff-rename",
    api.step_data(
      "[Experimental] git diff --raw to analyze patch",
      # missing dst_path
      api.raw_io.stream_output(
        ":100644 100644 1234567 89abcdef R100\tfoo.cc\n"
      ),
    ),
    api.properties(
      patch_root="",
      expected_files=[],
    ),
    api.post_check(post_process.StatusSuccess),
    api.post_process(post_process.DropExpectation),
  )
