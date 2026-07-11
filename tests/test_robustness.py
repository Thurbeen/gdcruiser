"""Tests for malformed-input handling, symbol collisions, and config semantics."""

from gdcruiser.analyzer import Analyzer
from gdcruiser.config.loader import ConfigLoader
from gdcruiser.symbols.table import SymbolTable


class TestSymbolCollisions:
    def test_duplicate_class_name_recorded(self):
        table = SymbolTable()
        table.register("Foo", "res://a.gd")
        table.register("Foo", "res://b.gd")
        collisions = table.collisions()
        assert collisions == [("Foo", "res://a.gd", "res://b.gd")]

    def test_same_path_not_a_collision(self):
        table = SymbolTable()
        table.register("Foo", "res://a.gd")
        table.register("Foo", "res://a.gd")
        assert table.collisions() == []

    def test_analyzer_surfaces_collision_warning(self, tmp_path):
        (tmp_path / "project.godot").write_text("[application]\n", encoding="utf-8")
        (tmp_path / "a.gd").write_text("class_name Dup\n", encoding="utf-8")
        (tmp_path / "b.gd").write_text("class_name Dup\n", encoding="utf-8")
        result = Analyzer(tmp_path).analyze()
        assert any("Duplicate symbol 'Dup'" in w for w in result.warnings)


class TestMalformedInput:
    def test_bad_utf8_gdscript_recorded_not_fatal(self, tmp_path):
        (tmp_path / "project.godot").write_text("[application]\n", encoding="utf-8")
        (tmp_path / "good.gd").write_text("class_name Good\n", encoding="utf-8")
        (tmp_path / "bad.gd").write_bytes(b"\xff\xfe invalid utf8 \x80\x81")

        result = Analyzer(tmp_path).analyze()
        # Good file still analyzed; bad one reported as an error.
        assert result.graph.has_module("res://good.gd")
        assert any("bad.gd" in e for e in result.errors)

    def test_malformed_project_godot_not_fatal(self, tmp_path):
        (tmp_path / "project.godot").write_bytes(b"\xff\xfe not utf8")
        (tmp_path / "good.gd").write_text("class_name Good\n", encoding="utf-8")

        result = Analyzer(tmp_path).analyze()
        assert result.graph.has_module("res://good.gd")
        assert any("project.godot" in e for e in result.errors)


class TestConfigSemantics:
    def test_unknown_top_level_key_warns(self, tmp_path):
        cfg = tmp_path / ".gdcruiser.json"
        cfg.write_text('{"forbiden": []}', encoding="utf-8")
        config = ConfigLoader(tmp_path).load(cfg)
        assert any("forbiden" in w for w in config.warnings)

    def test_bad_severity_warns_and_defaults_to_error(self, tmp_path):
        cfg = tmp_path / ".gdcruiser.json"
        cfg.write_text(
            '{"forbidden": [{"name": "r", "severity": "warning", '
            '"from": {"path": "a"}, "to": {"path": "b"}}]}',
            encoding="utf-8",
        )
        config = ConfigLoader(tmp_path).load(cfg)
        assert config.forbidden[0].severity.value == "error"
        assert any("severity" in w and "warning" in w for w in config.warnings)

    def test_unknown_rule_key_warns(self, tmp_path):
        cfg = tmp_path / ".gdcruiser.json"
        cfg.write_text(
            '{"forbidden": [{"name": "r", "frm": {"path": "a"}}]}',
            encoding="utf-8",
        )
        config = ConfigLoader(tmp_path).load(cfg)
        assert any("frm" in w for w in config.warnings)

    def test_valid_config_has_no_warnings(self, tmp_path):
        cfg = tmp_path / ".gdcruiser.json"
        cfg.write_text(
            '{"forbidden": [{"name": "r", "severity": "warn", '
            '"from": {"path": "a"}, "to": {"path": "b"}}], '
            '"options": {"exclude": ["addons"]}}',
            encoding="utf-8",
        )
        config = ConfigLoader(tmp_path).load(cfg)
        assert config.warnings == []
