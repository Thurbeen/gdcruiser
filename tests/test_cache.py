"""Tests for the incremental parse cache."""

from gdcruiser.analyzer import Analyzer
from gdcruiser.cache import ParseCache


def _make_project(root):
    (root / "project.godot").write_text("[application]\n", encoding="utf-8")
    (root / "a.gd").write_text(
        'class_name A\nvar b = preload("res://b.gd")\n', encoding="utf-8"
    )
    (root / "b.gd").write_text("class_name B\n", encoding="utf-8")


def test_cold_run_all_misses(tmp_path):
    _make_project(tmp_path)
    cache = ParseCache(tmp_path / "cache.json")
    cache.load()
    Analyzer(tmp_path, cache=cache).analyze()
    assert cache.hits == 0
    assert cache.misses == 2


def test_warm_run_all_hits(tmp_path):
    _make_project(tmp_path)
    cache_path = tmp_path / "cache.json"

    cold = ParseCache(cache_path)
    cold.load()
    Analyzer(tmp_path, cache=cold).analyze()

    warm = ParseCache(cache_path)
    warm.load()
    Analyzer(tmp_path, cache=warm).analyze()
    assert warm.hits == 2
    assert warm.misses == 0


def test_changed_file_invalidated(tmp_path):
    _make_project(tmp_path)
    cache_path = tmp_path / "cache.json"

    cold = ParseCache(cache_path)
    cold.load()
    Analyzer(tmp_path, cache=cold).analyze()

    # Rewrite one file with a newer mtime/size.
    (tmp_path / "a.gd").write_text(
        'class_name A\nvar b = preload("res://b.gd")\n# changed\n', encoding="utf-8"
    )

    warm = ParseCache(cache_path)
    warm.load()
    Analyzer(tmp_path, cache=warm).analyze()
    assert warm.hits == 1
    assert warm.misses == 1


def test_cache_produces_identical_graph(tmp_path):
    _make_project(tmp_path)
    cache_path = tmp_path / "cache.json"

    no_cache = Analyzer(tmp_path).analyze().to_dict()["graph"]

    cold = ParseCache(cache_path)
    cold.load()
    Analyzer(tmp_path, cache=cold).analyze()
    warm = ParseCache(cache_path)
    warm.load()
    cached = Analyzer(tmp_path, cache=warm).analyze().to_dict()["graph"]

    assert cached == no_cache


def test_stale_version_ignored(tmp_path):
    _make_project(tmp_path)
    cache_path = tmp_path / "cache.json"
    cache_path.write_text('{"version": 0, "entries": {}}', encoding="utf-8")

    cache = ParseCache(cache_path)
    cache.load()
    Analyzer(tmp_path, cache=cache).analyze()
    # Old version dropped -> everything reparsed.
    assert cache.misses == 2


def test_corrupt_cache_ignored(tmp_path):
    _make_project(tmp_path)
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("not json{{{", encoding="utf-8")

    cache = ParseCache(cache_path)
    cache.load()  # must not raise
    Analyzer(tmp_path, cache=cache).analyze()
    assert cache.misses == 2
