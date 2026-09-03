# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Lightweight Chrome Trace Event format tracer for depot_tools.

Produces JSON trace files compatible with Perfetto UI (https://ui.perfetto.dev)
and chrome://tracing with zero external dependencies.
"""

from collections.abc import Iterator
import contextlib
import functools
import json
import os
import sys
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional

_ENV_TRACE_VAR = "GCLIENT_TRACE"
_DEFAULT_TRACE_FILE = os.path.join(tempfile.gettempdir(), "gclient_trace.json")


class TraceCollector:
    """Collects trace events and writes them to a JSON file."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: List[Dict[str, Any]] = []
        self._threads: Dict[int, str] = {}
        self._enabled = False
        self._filepath: Optional[str] = None
        self._pid = os.getpid()

        # Check environment variable on startup.
        env_val = os.environ.get(_ENV_TRACE_VAR)
        if env_val:
            val_lower = env_val.strip().lower()
            if not val_lower or val_lower in ("0", "false", "no", "off"):
                pass
            elif val_lower in ("1", "true", "yes", "on"):
                self.start(_DEFAULT_TRACE_FILE)
            else:
                self.start(env_val)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def filepath(self) -> Optional[str]:
        return self._filepath

    def start(self, filepath: Optional[str] = None) -> None:
        """Starts trace collection to the given file path."""
        with self._lock:
            if self._enabled:
                # Tracing is already enabled (e.g. initialized early via environment
                # variable and called again during CLI argument parsing).
                # Do not wipe already collected events; update filepath if specified.
                if filepath:
                    self._filepath = filepath

                return

            self._enabled = True
            self._filepath = filepath or _DEFAULT_TRACE_FILE
            self._events = []
            self._threads = {}
            # Record main process/thread metadata.
            self._set_process_name_locked("gclient")
            self._set_thread_name_locked(threading.get_ident(), "MainThread")

    def set_thread_name(self, name: str, tid: Optional[int] = None) -> None:
        """Sets the display name for a thread."""
        if not self._enabled:
            return

        if tid is None:
            tid = threading.get_ident()

        with self._lock:
            self._set_thread_name_locked(tid, name)

    def _set_process_name_locked(self, name: str) -> None:
        self._events.append(
            {
                "name": "process_name",
                "ph": "M",
                "pid": self._pid,
                "tid": threading.get_ident(),
                "args": {"name": name},
            }
        )

    def _set_thread_name_locked(self, tid: int, name: str) -> None:
        self._threads[tid] = name
        self._events.append(
            {
                "name": "thread_name",
                "ph": "M",
                "pid": self._pid,
                "tid": tid,
                "args": {"name": name},
            }
        )

    def add_complete_event(
        self,
        name: str,
        cat: Optional[str],
        start_us: int,
        dur_us: int,
        tid: Optional[int] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Adds a Complete ('X') trace event."""
        if not self._enabled:
            return

        if tid is None:
            tid = threading.get_ident()

        event: Dict[str, Any] = {
            "name": name,
            "cat": cat or "gclient",
            "ph": "X",
            "ts": start_us,
            "dur": dur_us,
            "pid": self._pid,
            "tid": tid,
        }
        if args:
            # Ensure args values are JSON serializable.
            clean_args: Dict[str, Any] = {}
            for k, v in args.items():
                if (
                    isinstance(v, (str, int, float, bool, list, dict))
                    or v is None
                ):
                    clean_args[k] = v
                else:
                    clean_args[k] = str(v)
            event["args"] = clean_args

        with self._lock:
            self._events.append(event)

    def close(self) -> None:
        """Flushes collected trace events to the JSON file and disables tracing."""
        if not self._enabled:
            return

        with self._lock:
            self._enabled = False
            events_to_write = list(self._events)
            filepath = self._filepath

        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"traceEvents": events_to_write}, f, indent=2)
            print(
                f"Trace written to {os.path.abspath(filepath)} (open in https://ui.perfetto.dev)",
                file=sys.stderr,
            )
        except IOError as e:
            print(
                f"Failed to write trace file {filepath}: {e}", file=sys.stderr
            )


collector = TraceCollector()


@contextlib.contextmanager
def trace(
    name: str,
    cat: str = "gclient",
    args: Optional[Dict[str, Any]] = None,
) -> Iterator[None]:
    """Context manager to trace execution time of a block."""
    if not collector.enabled:
        yield
        return

    tid = threading.get_ident()
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        start_us = int(start_time * 1_000_000)
        dur_us = int((end_time - start_time) * 1_000_000)
        collector.add_complete_event(
            name, cat, start_us, dur_us, tid=tid, args=args
        )


def trace_function(
    name: Optional[str] = None,
    cat: str = "gclient",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to trace a function call."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        event_name = name or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not collector.enabled:
                return fn(*args, **kwargs)

            with trace(event_name, cat=cat):
                return fn(*args, **kwargs)

        return wrapper

    return decorator
