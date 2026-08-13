# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys

import config_util


class Libyuv(config_util.Config):
    """Basic Config class for libyuv."""

    @staticmethod
    def fetch_spec(props):
        url = "https://chromium.googlesource.com/libyuv/libyuv.git"
        solution = {
            "name": "src",
            "url": url,
            "deps_file": "DEPS",
            "custom_deps": {},
        }
        spec = {
            "solutions": [solution],
        }
        return {
            "type": "gclient_git",
            "gclient_git_spec": spec,
        }

    @staticmethod
    def expected_root(_props):
        return "src"


def main(argv=None):
    return Libyuv().handle_args(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
