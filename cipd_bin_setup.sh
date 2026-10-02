# Copyright 2017 The Chromium Authors
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

    local CACHE_DIR="$ROOT/.cipd/tmp"
    local CACHED_ENSURE="$CACHE_DIR/.cipd_manifest.txt"
    local CACHED_VERSIONS="$CACHE_DIR/.cipd_manifest.versions"
    local CACHED_CLIENT="$CACHE_DIR/.cipd_client_version"

    # CIPD ensure is slow (hundreds of milliseconds). We cache the result by
    # storing copies of the input files and comparing them on subsequent runs.
    # We use `cmp` (content-based) instead of `mtime` comparison to avoid
    # false-positive cache misses on CI bots where git checkouts reset mtimes.
    # Cache files live in `.cipd/tmp`, which `cipd ensure` automatically removes
    # whenever it modifies packages (even if invoked by an older checkout's
    # `cipd_bin_setup.sh` that predates this cache).
    if [ ! -f "$CACHED_ENSURE" ] || \
       ! cmp -s "$ENSURE" "$CACHED_ENSURE" || \
       ! cmp -s "$MYPATH/cipd_manifest.versions" "$CACHED_VERSIONS" || \
       ! cmp -s "$MYPATH/cipd_client_version" "$CACHED_CLIENT"; then

        rm -rf "$CACHE_DIR"
        rm -f "$ROOT/.cipd_manifest.txt" "$ROOT/.cipd_manifest.versions" "$ROOT/.cipd_client_version"

        (
        source "$MYPATH/cipd" ensure \
            -log-level warning \
            -ensure-file "$ENSURE" \
            -root "$ROOT"
        )
        if [ $? -eq 0 ]; then
            mkdir -p "$CACHE_DIR" && \
            cp "$ENSURE" "$CACHED_ENSURE" && \
            cp "$MYPATH/cipd_manifest.versions" "$CACHED_VERSIONS" && \
            cp "$MYPATH/cipd_client_version" "$CACHED_CLIENT"
        fi
    fi

    echo $ROOT
}
