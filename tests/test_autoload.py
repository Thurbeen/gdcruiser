from pathlib import Path

from gdcruiser.analyzer import Analyzer
from gdcruiser.graph.node import DependencyType
from gdcruiser.parser.gdscript import GDScriptParser
from gdcruiser.parser.project_godot import parse_autoloads
from gdcruiser.symbols.table import SymbolTable


FIXTURES = Path(__file__).parent / "fixtures"
AUTOLOAD_PROJECT = FIXTURES / "autoload_project"


class TestParseAutoloads:
    def test_parses_starred_entries(self):
        autoloads = parse_autoloads(AUTOLOAD_PROJECT)
        assert autoloads["TurnManager"] == "res://scripts/autoload/turn_manager.gd"
        assert autoloads["EventBus"] == "res://scripts/autoload/event_bus.gd"

    def test_parses_unstarred_entries(self):
        # An [autoload] entry without the `*` enabled marker still maps an
        # identifier to a file; gdcruiser shouldn't drop it on the floor.
        autoloads = parse_autoloads(AUTOLOAD_PROJECT)
        assert autoloads["DisabledSingleton"] == "res://scripts/autoload/disabled.gd"

    def test_no_project_file_returns_empty(self):
        # Pointing at a directory with no project.godot returns {}.
        autoloads = parse_autoloads(FIXTURES.parent)
        assert autoloads == {}

    def test_no_autoload_section_returns_empty(self):
        # The shared fixtures project.godot has no [autoload] section.
        autoloads = parse_autoloads(FIXTURES)
        assert autoloads == {}

    def test_only_autoload_section_is_read(self, tmp_path):
        # Lines that look like autoload entries but live under a different
        # section must not be parsed as autoloads.
        project = tmp_path / "project.godot"
        project.write_text(
            "[application]\n"
            'Trap="*res://scripts/trap.gd"\n'
            "[autoload]\n"
            'Real="*res://scripts/real.gd"\n'
        )
        autoloads = parse_autoloads(tmp_path)
        assert autoloads == {"Real": "res://scripts/real.gd"}


class TestAutoloadResolution:
    def test_member_access_resolves_to_autoload_target(self):
        analyzer = Analyzer(AUTOLOAD_PROJECT)
        result = analyzer.analyze()

        # heal_skill.gd uses TurnManager.advance() and EventBus.something_happened.
        skill = result.graph.get_module("res://scripts/heal_skill.gd")
        assert skill is not None

        targets = {d.target for d in skill.dependencies}
        assert "res://scripts/autoload/turn_manager.gd" in targets
        assert "res://scripts/autoload/event_bus.gd" in targets

        autoload_refs = [
            d
            for d in skill.dependencies
            if d.dep_type == DependencyType.CLASS_REF
            and d.target.startswith("res://scripts/autoload/")
        ]
        for dep in autoload_refs:
            assert dep.resolved is True

    def test_string_literal_autoload_ignored(self, tmp_path):
        # "TurnManager.advance" inside a string must not produce a class_ref.
        project = tmp_path / "project.godot"
        project.write_text('[autoload]\nTurnManager="*res://turn_manager.gd"\n')
        (tmp_path / "turn_manager.gd").write_text("extends Node\n")
        (tmp_path / "user.gd").write_text(
            'extends Node\nvar note := "TurnManager.advance"\n'
        )

        analyzer = Analyzer(tmp_path)
        result = analyzer.analyze()

        user = result.graph.get_module("res://user.gd")
        assert user is not None
        targets = {d.target for d in user.dependencies}
        assert "res://turn_manager.gd" not in targets

    def test_comment_autoload_ignored(self, tmp_path):
        project = tmp_path / "project.godot"
        project.write_text('[autoload]\nTurnManager="*res://turn_manager.gd"\n')
        (tmp_path / "turn_manager.gd").write_text("extends Node\n")
        (tmp_path / "user.gd").write_text(
            "extends Node\n"
            "# Sometime later we should call TurnManager.advance\n"
            "func noop() -> void:\n"
            "    pass\n"
        )

        analyzer = Analyzer(tmp_path)
        result = analyzer.analyze()

        user = result.graph.get_module("res://user.gd")
        assert user is not None
        targets = {d.target for d in user.dependencies}
        assert "res://turn_manager.gd" not in targets

    def test_class_name_can_shadow_autoload(self):
        # If a script declares `class_name TurnManager`, gdcruiser must
        # still resolve a member-access reference somewhere — to one of
        # the two definitions. We assert the symbol is registered, not
        # which one wins, since either is a valid project setup.
        analyzer = Analyzer(AUTOLOAD_PROJECT)
        result = analyzer.analyze()
        assert result.symbol_table.has_class("TurnManager")
        assert result.symbol_table.has_class("EventBus")


class TestStringLiteralImmunityForClassRefs:
    """Regression coverage for v1.6.0+ class-ref detection."""

    def setup_method(self):
        self.symbol_table = SymbolTable()
        self.parser = GDScriptParser(self.symbol_table)

    def test_class_member_inside_string_is_ignored(self, tmp_path):
        self.symbol_table.register("TurnManager", "res://turn_manager.gd")
        f = tmp_path / "user.gd"
        f.write_text(
            "extends Node\n"
            'var s := "TurnManager.advance is just a label"\n'
            "func _ready() -> void:\n"
            "    print(s)\n"
        )
        module = self.parser.parse(f, tmp_path)
        self.parser.resolve_class_dependencies(module)
        targets = {d.target for d in module.dependencies}
        assert "res://turn_manager.gd" not in targets

    def test_class_member_inside_comment_is_ignored(self, tmp_path):
        self.symbol_table.register("TurnManager", "res://turn_manager.gd")
        f = tmp_path / "user.gd"
        f.write_text(
            "extends Node\n"
            "# Could call TurnManager.advance here later.\n"
            "func _ready() -> void:\n"
            "    pass\n"
        )
        module = self.parser.parse(f, tmp_path)
        self.parser.resolve_class_dependencies(module)
        targets = {d.target for d in module.dependencies}
        assert "res://turn_manager.gd" not in targets
