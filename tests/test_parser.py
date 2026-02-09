from pathlib import Path

from gdcruiser.parser.gdscript import GDScriptParser
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
