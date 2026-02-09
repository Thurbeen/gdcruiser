from pathlib import Path

from gdcruiser.analyzer import Analyzer


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
