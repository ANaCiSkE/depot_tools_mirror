DEPS = [
  "depot_tools",
  "recipe_engine/buildbucket",
  "recipe_engine/context",
  "recipe_engine/runtime",
  "recipe_engine/path",
  "recipe_engine/platform",
  "recipe_engine/properties",
  "recipe_engine/raw_io",
  "recipe_engine/step",
]

from .api import GitApi as API  # noqa: E402, F401
from .test_api import GitTestApi as TEST_API  # noqa: E402, F401
