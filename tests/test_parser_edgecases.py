"""Regression tests for comment/string stripping and builtin handling."""

from pathlib import Path

from gdcruiser.parser.gdscript import GDScriptParser
from gdcruiser.graph.node import DependencyType
from gdcruiser.symbols.table import SymbolTable


def _parse(tmp_path: Path, source: str):
    parser = GDScriptParser(SymbolTable())
    f = tmp_path / "script.gd"
    f.write_text(source, encoding="utf-8")
    return parser.parse(f, tmp_path)


def _targets(module, dep_type):
    return [d.target for d in module.dependencies if d.dep_type == dep_type]


class TestCommentStripping:
    def test_preload_in_inline_comment_ignored(self, tmp_path):
        module = _parse(
            tmp_path,
            'extends Node\nvar x = 5  # preload("res://old.gd")\n',
        )
        assert _targets(module, DependencyType.PRELOAD) == []

    def test_load_in_inline_comment_ignored(self, tmp_path):
        module = _parse(
            tmp_path,
            'extends Node\nvar y = 1  # load("res://old.gd")\n',
        )
        assert _targets(module, DependencyType.LOAD) == []

    def test_real_preload_after_comment_kept(self, tmp_path):
        module = _parse(
            tmp_path,
            'var real = preload("res://real.gd")  # loads the thing\n',
        )
        assert _targets(module, DependencyType.PRELOAD) == ["res://real.gd"]

    def test_hash_inside_string_is_not_a_comment(self, tmp_path):
        module = _parse(
            tmp_path,
            'var real = preload("res://a.gd")\nvar s = "# not a comment"\n',
        )
        assert _targets(module, DependencyType.PRELOAD) == ["res://a.gd"]


class TestStringLiteralStripping:
    def test_preload_text_inside_string_ignored(self, tmp_path):
        module = _parse(
            tmp_path,
            'var doc = "call preload(\\"res://phantom.gd\\") somewhere"\n',
        )
        assert _targets(module, DependencyType.PRELOAD) == []


class TestMultilineStrings:
    def test_triple_quoted_block_ignored(self, tmp_path):
        source = (
            "extends Node\n"
            'var doc = """\n'
            'preload("res://in_triple.gd")\n'
            "extends InTripleClass\n"
            "ClassRef.method()\n"
            '"""\n'
            'var real = preload("res://real.gd")\n'
        )
        module = _parse(tmp_path, source)
        assert _targets(module, DependencyType.PRELOAD) == ["res://real.gd"]
        assert _targets(module, DependencyType.EXTENDS_CLASS) == []

    def test_single_quoted_triple_block_ignored(self, tmp_path):
        source = "var doc = '''\npreload(\"res://x.gd\")\n'''\n"
        module = _parse(tmp_path, source)
        assert _targets(module, DependencyType.PRELOAD) == []


class TestLineNumbersPreserved:
    def test_line_numbers_survive_preprocessing(self, tmp_path):
        source = (
            "extends Node\n"  # 1
            "# a comment line\n"  # 2
            'var doc = """\n'  # 3
            "hidden\n"  # 4
            '"""\n'  # 5
            'var real = preload("res://real.gd")\n'  # 6
        )
        module = _parse(tmp_path, source)
        preload = [
            d for d in module.dependencies if d.dep_type == DependencyType.PRELOAD
        ]
        assert len(preload) == 1
        assert preload[0].line == 6


class TestBuiltinExtends:
    def test_extends_known_builtin_not_a_dependency(self, tmp_path):
        module = _parse(tmp_path, "extends PhysicsBody2D\n")
        assert _targets(module, DependencyType.EXTENDS_CLASS) == []

    def test_extends_unknown_class_is_dependency(self, tmp_path):
        module = _parse(tmp_path, "extends SomeProjectClass\n")
        assert _targets(module, DependencyType.EXTENDS_CLASS) == ["SomeProjectClass"]
