# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

function cipd_bin_setup {
    local MYPATH="${DEPOT_TOOLS_DIR:-$(dirname "${BASH_SOURCE[0]}")}"
    local ENSURE="$MYPATH/cipd_manifest.txt"
    local ROOT="$MYPATH/.cipd_bin"

    UNAME="${DEPOT_TOOLS_UNAME_S:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
    case $UNAME in
      cygwin*)
        ENSURE="$(cygpath -w $ENSURE)"
        ROOT="$(cygpath -w $ROOT)"
        ;;
    esac

    # value in .cipd_client_root file overrides the default root.
    CIPD_ROOT_OVERRIDE_FILE="${MYPATH}/.cipd_client_root"
    if [ -f "${CIPD_ROOT_OVERRIDE_FILE}" ]; then
        ROOT=$(<"${CIPD_ROOT_OVERRIDE_FILE}")
    fi

    local CACHED_ENSURE="$ROOT/.cipd_manifest.txt"
    local CACHED_VERSIONS="$ROOT/.cipd_manifest.versions"
    local CACHED_CLIENT="$ROOT/.cipd_client_version"

    # CIPD ensure is slow (hundreds of milliseconds). We cache the result by
    # storing copies of the input files and comparing them on subsequent runs.
    # We use `cmp` (content-based) instead of `mtime` comparison to avoid
    # false-positive cache misses on CI bots where git checkouts reset mtimes.
    if [ ! -f "$CACHED_ENSURE" ] || \
       ! cmp -s "$ENSURE" "$CACHED_ENSURE" || \
       ! cmp -s "$MYPATH/cipd_manifest.versions" "$CACHED_VERSIONS" || \
       ! cmp -s "$MYPATH/cipd_client_version" "$CACHED_CLIENT"; then

        rm -f "$CACHED_ENSURE"

        (
        source "$MYPATH/cipd" ensure \
            -log-level warning \
            -ensure-file "$ENSURE" \
            -root "$ROOT"
        )
        if [ $? -eq 0 ]; then
            cp "$ENSURE" "$CACHED_ENSURE" && \
            cp "$MYPATH/cipd_manifest.versions" "$CACHED_VERSIONS" && \
            cp "$MYPATH/cipd_client_version" "$CACHED_CLIENT"
        fi
    fi

    echo $ROOT
}
