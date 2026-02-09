from gdcruiser.graph.node import Module, Dependency, DependencyType
from gdcruiser.graph.dependency import DependencyGraph
from gdcruiser.graph.cycles import CycleDetector


class TestDependencyGraph:
    def test_add_and_get_module(self):
        graph = DependencyGraph()
        module = Module(path="res://test.gd")
        graph.add_module(module)

        assert graph.has_module("res://test.gd")
        assert graph.get_module("res://test.gd") is module

    def test_module_count(self):
        graph = DependencyGraph()
        graph.add_module(Module(path="res://a.gd"))
        graph.add_module(Module(path="res://b.gd"))

        assert graph.module_count() == 2

    def test_dependency_count(self):
        graph = DependencyGraph()
        graph.add_module(
            Module(
                path="res://a.gd",
                dependencies=[
                    Dependency(target="res://b.gd", dep_type=DependencyType.PRELOAD),
                    Dependency(target="res://c.gd", dep_type=DependencyType.PRELOAD),
                ],
            )
        )
        graph.add_module(Module(path="res://b.gd"))

        assert graph.dependency_count() == 2

    def test_get_dependents(self):
        graph = DependencyGraph()
        graph.add_module(
            Module(
                path="res://a.gd",
                dependencies=[
                    Dependency(target="res://b.gd", dep_type=DependencyType.PRELOAD)
                ],
            )
        )
        graph.add_module(Module(path="res://b.gd"))

        dependents = graph.get_dependents("res://b.gd")
        assert len(dependents) == 1
        assert dependents[0][0] == "res://a.gd"


class TestCycleDetector:
    def test_no_cycles(self):
        graph = DependencyGraph()
        graph.add_module(
            Module(
                path="res://a.gd",
                dependencies=[
                    Dependency(target="res://b.gd", dep_type=DependencyType.PRELOAD)
                ],
            )
        )
        graph.add_module(Module(path="res://b.gd"))

        detector = CycleDetector(graph)
        cycles = detector.find_cycles()
        assert len(cycles) == 0

    def test_simple_cycle(self):
        graph = DependencyGraph()
        graph.add_module(
            Module(
                path="res://a.gd",
                dependencies=[
                    Dependency(target="res://b.gd", dep_type=DependencyType.PRELOAD)
                ],
            )
        )
        graph.add_module(
            Module(
                path="res://b.gd",
                dependencies=[
                    Dependency(target="res://a.gd", dep_type=DependencyType.PRELOAD)
                ],
            )
        )

        detector = CycleDetector(graph)
        cycles = detector.find_cycles()
        assert len(cycles) == 1
        assert set(cycles[0]) == {"res://a.gd", "res://b.gd"}

    def test_three_node_cycle(self):
        graph = DependencyGraph()
        graph.add_module(
            Module(
                path="res://a.gd",
                dependencies=[
                    Dependency(target="res://b.gd", dep_type=DependencyType.PRELOAD)
                ],
            )
        )
        graph.add_module(
            Module(
                path="res://b.gd",
                dependencies=[
                    Dependency(target="res://c.gd", dep_type=DependencyType.PRELOAD)
                ],
            )
        )
        graph.add_module(
            Module(
                path="res://c.gd",
                dependencies=[
                    Dependency(target="res://a.gd", dep_type=DependencyType.PRELOAD)
                ],
            )
        )

        detector = CycleDetector(graph)
        cycles = detector.find_cycles()
        assert len(cycles) == 1
        assert set(cycles[0]) == {"res://a.gd", "res://b.gd", "res://c.gd"}
