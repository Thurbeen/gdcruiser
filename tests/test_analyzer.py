from pathlib import Path

from gdcruiser.analyzer import Analyzer
from gdcruiser.graph.node import DependencyType


FIXTURES = Path(__file__).parent / "fixtures"


class TestAnalyzer:
    def test_analyze_finds_modules(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        # Should find all .gd and .tscn files
        assert result.graph.module_count() >= 8  # 8 .gd files + 1 .tscn

    def test_analyze_builds_symbol_table(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        # Should have class names registered
        assert result.symbol_table.has_class("BaseEntity")
        assert result.symbol_table.has_class("Player")
        assert result.symbol_table.has_class("Enemy")
        assert result.symbol_table.has_class("Inventory")

    def test_analyze_detects_cycles(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        # Should detect the CycleA <-> CycleB cycle
        assert len(result.cycles) >= 1

        # Find the cycle containing CycleA and CycleB
        cycle_paths = set()
        for cycle in result.cycles:
            cycle_paths.update(cycle)

        assert "res://cycle_a.gd" in cycle_paths
        assert "res://cycle_b.gd" in cycle_paths

    def test_analyze_no_cycles_option(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze(detect_cycles=False)

        assert result.cycles == []

    def test_analyze_resolves_class_references(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        # Check that Player's extends BaseEntity is resolved
        player_module = result.graph.get_module("res://player.gd")
        assert player_module is not None

        extends_deps = [
            d for d in player_module.dependencies if "extends" in d.dep_type.value
        ]
        resolved_count = sum(1 for d in extends_deps if d.resolved)
        assert resolved_count > 0

    def test_exclude_removes_matching_files(self):
        analyzer = Analyzer(FIXTURES, exclude=["cycle_"])
        result = analyzer.analyze()

        module_paths = [m.path for m in result.graph.all_modules()]
        assert "res://cycle_a.gd" not in module_paths
        assert "res://cycle_b.gd" not in module_paths
        # Other modules should still be present
        assert "res://player.gd" in module_paths

    def test_exclude_nonmatching_pattern_keeps_all(self):
        baseline = Analyzer(FIXTURES)
        baseline_result = baseline.analyze()

        analyzer = Analyzer(FIXTURES, exclude=["zzz_no_match"])
        result = analyzer.analyze()

        assert result.graph.module_count() == baseline_result.graph.module_count()

    def test_analyze_resolves_class_refs_to_paths(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        skill = result.graph.get_module("res://skill_system.gd")
        assert skill is not None

        class_refs = [
            d for d in skill.dependencies if d.dep_type == DependencyType.CLASS_REF
        ]
        # Every CLASS_REF that survives resolution points at a real path.
        assert len(class_refs) > 0
        for dep in class_refs:
            assert dep.resolved is True
            assert result.graph.has_module(dep.target)

    def test_analyze_includes_tres_files(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        tres = result.graph.get_module("res://heal_skill.tres")
        assert tres is not None
        assert tres.class_name == "HealSkill"
        # script_class registers in the symbol table for cross-module resolution.
        assert result.symbol_table.has_class("HealSkill")

        targets = {d.target for d in tres.dependencies}
        assert "res://skill_system.gd" in targets
        assert "res://config.gd" in targets

    def test_typed_var_in_existing_fixture_resolves(self):
        # `enemy.gd` has `var target: Player` — this is the canonical class-ref
        # case the new parser must catch. Ensure it now resolves to player.gd.
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        enemy = result.graph.get_module("res://enemy.gd")
        assert enemy is not None
        targets = {d.target for d in enemy.dependencies}
        assert "res://player.gd" in targets
