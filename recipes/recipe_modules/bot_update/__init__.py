DEPS = [
  "depot_tools",
  "gclient",
  "gerrit",
  "gitiles",
  "gsutil",
  "recipe_engine/archive",
  "recipe_engine/buildbucket",
  "recipe_engine/context",
  "recipe_engine/commit_position",
  "recipe_engine/cv",
  "recipe_engine/json",
  "recipe_engine/led",
  "recipe_engine/milo",
  "recipe_engine/path",
  "recipe_engine/platform",
  "recipe_engine/properties",
  "recipe_engine/raw_io",
  "recipe_engine/runtime",
  "recipe_engine/step",
  "recipe_engine/warning",
  "tryserver",
]

from recipe_engine.recipe_api import Property  # noqa: E402
from recipe_engine.config import ConfigGroup, Single  # noqa: E402

PROPERTIES = {
  # Gerrit patches will have all properties about them prefixed with patch_.
  "deps_revision_overrides": Property(default={}),
  "$depot_tools/bot_update": Property(
    help="Properties specific to bot_update module.",
    param_name="properties",
    kind=ConfigGroup(stale_process_duration_override=Single(int)),
    default={},
  ),
}

# Forward these types so that they can be used without importing api
from .api import RelativeRoot, Result  # noqa: E402, F401

from .api import BotUpdateApi as API  # noqa: E402, F401
from .test_api import BotUpdateTestApi as TEST_API  # noqa: E402, F401
