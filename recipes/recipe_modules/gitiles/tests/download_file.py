# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import DropExpectation, StatusSuccess


DEPS = [
  "gitiles",
  "recipe_engine/properties",
  "recipe_engine/step",
  "recipe_engine/assertions",
]


def RunSteps(api):
  url = "https://chromium.googlesource.com/chromium/src"

  invalid_paths = [
    "../secret",
    "../../other_repo/+/main/file",
    "foo/../../bar",
    "..",
    "/absolute/path",
    "/",
  ]
  for invalid_path in invalid_paths:
    with api.assertions.assertRaisesRegexp(
      ValueError, "must be a relative path"
    ):
      api.gitiles.download_file(url, invalid_path)

  valid_paths = [
    ".gitignore",
    "foo/../bar.txt",
  ]
  for valid_path in valid_paths:
    data = api.gitiles.download_file(url, valid_path)
    api.assertions.assertEqual("data", data)


def GenTests(api):
  yield (
    api.test("basic")
    + api.step_data(
      "fetch main:.gitignore",
      api.gitiles.make_encoded_file("data"),
    )
    + api.step_data(
      "fetch main:bar.txt",
      api.gitiles.make_encoded_file("data"),
    )
    + api.post_process(StatusSuccess)
    + api.post_process(DropExpectation)
  )
