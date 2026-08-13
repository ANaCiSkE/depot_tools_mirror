# Copyright 2018 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  "recipe_engine/cipd",
  "recipe_engine/context",
  "recipe_engine/json",
  "recipe_engine/path",
  "recipe_engine/platform",
  "recipe_engine/properties",
  "recipe_engine/raw_io",
  "recipe_engine/step",
  "recipe_engine/version",
]

from recipe_engine.recipe_api import Property  # noqa: E402
from recipe_engine.config import ConfigGroup, Single  # noqa: E402

PROPERTIES = {
  "$depot_tools/osx_sdk": Property(
    help="Properties specifically for the infra osx_sdk module.",
    param_name="sdk_properties",
    kind=ConfigGroup(
      # XCode build version number. Internally maps to an XCode build id like
      # '9c40b'. See
      #
      #   https://chrome-infra-packages.appspot.com/p/infra_internal/ios/xcode/mac/+/
      #
      # For an up to date list of the latest SDK builds.
      sdk_version=Single(str),
      # The CIPD toolchain tool package and version
      toolchain_pkg=Single(str),
      toolchain_ver=Single(str),
    ),
    default={},
  )
}

from .api import OSXSDKApi as API  # noqa: E402, F401
from .test_api import OSXSDKTestApi as TEST_API  # noqa: E402, F401
