"""Incremental parse cache.

Persists the *raw* parsed :class:`Module` for each source file keyed by the
file's modification time and size. On a subsequent run, unchanged files are
restored from the cache instead of being re-read and re-parsed.

Only per-file parsing is cached. Cross-file work (symbol resolution and cycle
detection) always runs fresh, because a change in one file can alter how an
unchanged file's class references resolve.
"""

import json
from pathlib import Path

from .graph.node import Module

# Bump when the cached representation or parsing semantics change, so stale
# caches from older versions are transparently ignored.
CACHE_VERSION = 1


class ParseCache:
    """A file-backed cache of parsed modules keyed by (mtime_ns, size)."""

    def __init__(self, cache_path: Path) -> None:
        self._path = cache_path
        self._old: dict[str, dict] = {}
        self._new: dict[str, dict] = {}
        self.hits = 0
        self.misses = 0

    def load(self) -> None:
        """Load an existing cache file, ignoring anything unreadable or stale."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict) and data.get("version") == CACHE_VERSION:
            entries = data.get("entries")
            if isinstance(entries, dict):
                self._old = entries

    @staticmethod
    def stat_key(file_path: Path) -> str:
        """Return a cache key capturing the file's current mtime and size."""
        stat = file_path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"

    def get(self, file_path: Path, key: str) -> Module | None:
        """Return the cached module for ``file_path`` if its key still matches."""
        path_key = str(file_path)
        entry = self._old.get(path_key)
        if entry is not None and entry.get("key") == key:
            self.hits += 1
            # Carry the still-valid entry forward so it survives the next save.
            self._new[path_key] = entry
            return Module.from_dict(entry["module"])
        self.misses += 1
        return None

    def put(self, file_path: Path, key: str, module: Module) -> None:
        """Store a freshly parsed module under its current key."""
        self._new[str(file_path)] = {"key": key, "module": module.to_dict()}

    def save(self) -> None:
        """Write the accumulated entries back to disk."""
        payload = {"version": CACHE_VERSION, "entries": self._new}
        try:
            self._path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass
