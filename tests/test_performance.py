"""Tests for the reverse-dependents index, deep-graph cycles, and scanner."""

from gdcruiser.graph.cycles import CycleDetector
from gdcruiser.graph.dependency import DependencyGraph
from gdcruiser.graph.node import Dependency, DependencyType, Module
from gdcruiser.scanner import Scanner


def _dep(target):
    return Dependency(target=target, dep_type=DependencyType.PRELOAD)


class TestDependentsIndex:
    def test_dependents_found(self):
        g = DependencyGraph()
        g.add_module(Module(path="a", dependencies=[_dep("c")]))
        g.add_module(Module(path="b", dependencies=[_dep("c")]))
        g.add_module(Module(path="c"))
        sources = sorted(p for p, _ in g.get_dependents("c"))
        assert sources == ["a", "b"]

    def test_no_dependents(self):
        g = DependencyGraph()
        g.add_module(Module(path="a"))
        assert g.get_dependents("a") == []

    def test_index_invalidated_on_add(self):
        g = DependencyGraph()
        g.add_module(Module(path="a", dependencies=[_dep("c")]))
        assert len(g.get_dependents("c")) == 1  # builds index
        g.add_module(Module(path="b", dependencies=[_dep("c")]))
        assert len(g.get_dependents("c")) == 2  # index rebuilt


class TestDeepCycles:
    def test_deep_chain_no_recursion_error(self):
        g = DependencyGraph()
        n = 3000
        for i in range(n):
            deps = [_dep(f"m{i + 1}")] if i < n - 1 else []
            g.add_module(Module(path=f"m{i}", dependencies=deps))
        # A linear chain has no cycles and must not raise RecursionError.
        assert CycleDetector(g).find_cycles() == []

    def test_deep_chain_with_cycle(self):
        g = DependencyGraph()
        n = 2000
        for i in range(n):
            target = f"m{(i + 1) % n}"  # wrap-around -> one big cycle
            g.add_module(Module(path=f"m{i}", dependencies=[_dep(target)]))
        cycles = CycleDetector(g).find_cycles()
        assert len(cycles) == 1
        assert len(cycles[0]) == n


class TestScannerSinglePass:
    def test_buckets_by_suffix(self, tmp_path):
        (tmp_path / "a.gd").write_text("", encoding="utf-8")
        (tmp_path / "s.tscn").write_text("", encoding="utf-8")
        (tmp_path / "r.tres").write_text("", encoding="utf-8")
        (tmp_path / "ignore.txt").write_text("", encoding="utf-8")
        sub = tmp_path / "nested"
        sub.mkdir()
        (sub / "b.gd").write_text("", encoding="utf-8")

        gd, tscn, tres = Scanner(tmp_path).find_all_files()
        assert [p.name for p in gd] == ["a.gd", "b.gd"]
        assert [p.name for p in tscn] == ["s.tscn"]
        assert [p.name for p in tres] == ["r.tres"]

    def test_exclude_pattern(self, tmp_path):
        (tmp_path / "keep.gd").write_text("", encoding="utf-8")
        addons = tmp_path / "addons"
        addons.mkdir()
        (addons / "plugin.gd").write_text("", encoding="utf-8")

        gd = Scanner(tmp_path, exclude=["addons"]).find_gdscript_files()
        assert [p.name for p in gd] == ["keep.gd"]
