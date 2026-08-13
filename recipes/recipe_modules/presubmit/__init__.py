# Copyright 2019 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import ConfigGroup, Single  # noqa: F401
from recipe_engine.recipe_api import Property  # noqa: F401

from PB.recipe_modules.depot_tools.presubmit import properties


DEPS = [
  "bot_update",
  "depot_tools",
  "gclient",
  "git",
  "recipe_engine/buildbucket",
  "recipe_engine/context",
  "recipe_engine/cv",
  "recipe_engine/findings",
  "recipe_engine/json",
  "recipe_engine/path",
  "recipe_engine/properties",
  "recipe_engine/raw_io",
  "recipe_engine/resultdb",
  "recipe_engine/step",
  "tryserver",
]


PROPERTIES = properties.InputProperties

from .api import PresubmitApi as API  # noqa: E402, F401
from .test_api import PresubmitTestApi as TEST_API  # noqa: E402, F401
