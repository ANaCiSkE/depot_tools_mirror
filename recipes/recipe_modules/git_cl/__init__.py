DEPS = [
  "recipe_engine/context",
  "recipe_engine/raw_io",
  "recipe_engine/step",
]

from .api import GitClApi as API  # noqa: E402, F401
