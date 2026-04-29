from pathlib import Path

from gdcruiser.parser.gdscript import GDScriptParser
from gdcruiser.parser.tres import TresParser
from gdcruiser.parser.tscn import TscnParser
from gdcruiser.symbols.table import SymbolTable
from gdcruiser.graph.node import DependencyType


FIXTURES = Path(__file__).parent / "fixtures"


class TestGDScriptParser:
    def setup_method(self):
        self.symbol_table = SymbolTable()
        self.parser = GDScriptParser(self.symbol_table)

    def test_parse_class_name(self):
        module = self.parser.parse(FIXTURES / "base_entity.gd", FIXTURES)
        assert module.class_name == "BaseEntity"
        assert self.symbol_table.has_class("BaseEntity")

    def test_parse_extends_class(self):
        # First parse base to register class
        self.parser.parse(FIXTURES / "base_entity.gd", FIXTURES)

        module = self.parser.parse(FIXTURES / "player.gd", FIXTURES)
        assert module.class_name == "Player"

        # Find extends dependency
        extends_deps = [
            d for d in module.dependencies if d.dep_type == DependencyType.EXTENDS_CLASS
        ]
        assert len(extends_deps) == 1
        assert extends_deps[0].target == "BaseEntity"

    def test_parse_extends_path(self):
        module = self.parser.parse(FIXTURES / "enemy.gd", FIXTURES)

        extends_deps = [
            d for d in module.dependencies if d.dep_type == DependencyType.EXTENDS_PATH
        ]
        assert len(extends_deps) == 1
        assert extends_deps[0].target == "res://base_entity.gd"

    def test_parse_preload(self):
        module = self.parser.parse(FIXTURES / "player.gd", FIXTURES)

        preload_deps = [
            d for d in module.dependencies if d.dep_type == DependencyType.PRELOAD
        ]
        assert len(preload_deps) == 1
        assert preload_deps[0].target == "res://inventory.gd"

    def test_parse_load(self):
        module = self.parser.parse(FIXTURES / "game_manager.gd", FIXTURES)

        load_deps = [
            d for d in module.dependencies if d.dep_type == DependencyType.LOAD
        ]
        assert len(load_deps) == 1
        assert load_deps[0].target == "res://config.gd"

    def test_resolve_class_dependencies(self):
        # Parse files to build symbol table
        self.parser.parse(FIXTURES / "base_entity.gd", FIXTURES)
        module = self.parser.parse(FIXTURES / "player.gd", FIXTURES)

        # Resolve class references
        self.parser.resolve_class_dependencies(module)

        extends_deps = [
            d for d in module.dependencies if d.dep_type == DependencyType.EXTENDS_CLASS
        ]
        assert len(extends_deps) == 1
        assert extends_deps[0].target == "res://base_entity.gd"
        assert extends_deps[0].resolved is True


class TestTscnParser:
    def setup_method(self):
        self.parser = TscnParser()

    def test_parse_scene_script(self):
        module = self.parser.parse(FIXTURES / "player.tscn", FIXTURES)

        assert module.path == "res://player.tscn"
        assert len(module.dependencies) == 1
        assert module.dependencies[0].target == "res://player.gd"
        assert module.dependencies[0].dep_type == DependencyType.SCENE_SCRIPT


class TestClassRefDetection:
    def setup_method(self):
        self.symbol_table = SymbolTable()
        self.parser = GDScriptParser(self.symbol_table)

    def _parse_all(self) -> None:
        # Populate the symbol table with everything in fixtures/.
        for gd_file in sorted(FIXTURES.glob("*.gd")):
            self.parser.parse(gd_file, FIXTURES)

    def test_typed_var_detected(self):
        self._parse_all()
        module = self.parser.parse(FIXTURES / "skill_system.gd", FIXTURES)
        # `var current_target: Player` — Player is a known class.
        targets = {d.target for d in module.dependencies}
        assert "Player" in targets

    def test_param_and_return_types_detected(self):
        self._parse_all()
        module = self.parser.parse(FIXTURES / "skill_system.gd", FIXTURES)
        targets = {d.target for d in module.dependencies}
        # Param `source: BaseEntity` and return-type `-> Inventory`.
        assert "BaseEntity" in targets
        assert "Inventory" in targets

    def test_is_as_detected(self):
        self._parse_all()
        module = self.parser.parse(FIXTURES / "skill_system.gd", FIXTURES)
        # `target is Player` and `source as Enemy`.
        targets = {d.target for d in module.dependencies}
        assert "Enemy" in targets

    def test_class_ref_resolves_to_path(self):
        self._parse_all()
        module = self.parser.parse(FIXTURES / "skill_system.gd", FIXTURES)
        self.parser.resolve_class_dependencies(module)

        class_refs = [
            d for d in module.dependencies if d.dep_type == DependencyType.CLASS_REF
        ]
        # All resolved CLASS_REFs point at known module paths.
        for dep in class_refs:
            assert dep.resolved is True
            assert dep.target.startswith("res://")

    def test_unresolved_class_refs_are_dropped(self):
        # No symbol table population: every class ref is unresolved → dropped.
        module = self.parser.parse(FIXTURES / "skill_system.gd", FIXTURES)
        self.parser.resolve_class_dependencies(module)

        class_refs = [
            d for d in module.dependencies if d.dep_type == DependencyType.CLASS_REF
        ]
        assert class_refs == []

    def test_builtin_classes_not_class_refs(self):
        self._parse_all()
        module = self.parser.parse(FIXTURES / "skill_system.gd", FIXTURES)
        targets = {d.target for d in module.dependencies}
        # Built-ins like Node, Array, Trigger (uppercase locals) shouldn't
        # appear once resolved.
        self.parser.resolve_class_dependencies(module)
        targets = {d.target for d in module.dependencies}
        assert not any(t == "Node" for t in targets)
        assert not any(t == "Array" for t in targets)

    def test_string_literal_class_name_ignored(self):
        # Class identifiers inside string literals must not be detected.
        symbol_table = SymbolTable()
        parser = GDScriptParser(symbol_table)
        symbol_table.register("Player", "res://player.gd")
        # Write a small fixture inline.
        tmp = FIXTURES / "_inline_string.gd"
        tmp.write_text(
            'extends Node\nvar greeting := "Hello Player"\nvar count: int = 0\n'
        )
        try:
            module = parser.parse(tmp, FIXTURES)
            targets = {d.target for d in module.dependencies}
            assert "Player" not in targets
        finally:
            tmp.unlink()

    def test_self_class_reference_dropped(self):
        # A file referencing its own class_name shouldn't self-loop.
        self._parse_all()
        module = self.parser.parse(FIXTURES / "skill_system.gd", FIXTURES)
        self.parser.resolve_class_dependencies(module)
        targets = {d.target for d in module.dependencies}
        assert module.path not in targets


class TestTresParser:
    def setup_method(self):
        self.symbol_table = SymbolTable()
        self.parser = TresParser(self.symbol_table)

    def test_parse_script_class_attribute(self):
        module = self.parser.parse(FIXTURES / "heal_skill.tres", FIXTURES)
        assert module.path == "res://heal_skill.tres"
        assert module.class_name == "HealSkill"
        assert self.symbol_table.has_class("HealSkill")

    def test_parse_ext_resource_script(self):
        module = self.parser.parse(FIXTURES / "heal_skill.tres", FIXTURES)
        targets = {d.target: d.dep_type for d in module.dependencies}
        assert targets["res://skill_system.gd"] == DependencyType.SCENE_SCRIPT

    def test_parse_ext_resource_other_resource(self):
        module = self.parser.parse(FIXTURES / "heal_skill.tres", FIXTURES)
        targets = {d.target: d.dep_type for d in module.dependencies}
        # Non-script resource ref classified as RESOURCE_REF.
        assert "res://config.gd" in targets

    def test_no_duplicate_targets(self):
        module = self.parser.parse(FIXTURES / "heal_skill.tres", FIXTURES)
        targets = [d.target for d in module.dependencies]
        assert len(targets) == len(set(targets))

    def test_works_without_symbol_table(self):
        # Parser is usable without a symbol table; just no registration.
        parser = TresParser()
        module = parser.parse(FIXTURES / "heal_skill.tres", FIXTURES)
        assert module.class_name == "HealSkill"
        assert len(module.dependencies) > 0
