DEPS = [
  "recipe_engine/buildbucket",
  "recipe_engine/context",
  "recipe_engine/file",
  "recipe_engine/json",
  "recipe_engine/path",
  "recipe_engine/raw_io",
  "recipe_engine/step",
  "recipe_engine/time",
]

from .api import GerritApi as API  # noqa: E402, F401
from .test_api import GerritTestApi as TEST_API  # noqa: E402, F401
