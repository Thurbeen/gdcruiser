from gdcruiser.parser.patterns import Patterns


class TestExtendsPath:
    def test_matches_extends_path(self):
        line = 'extends "res://path/to/script.gd"'
        match = Patterns.EXTENDS_PATH.match(line)
        assert match is not None
        assert match.group(1) == "res://path/to/script.gd"

    def test_matches_with_leading_whitespace(self):
        line = '    extends "res://script.gd"'
        match = Patterns.EXTENDS_PATH.match(line)
        assert match is not None

    def test_no_match_for_class_extends(self):
        line = "extends Node2D"
        match = Patterns.EXTENDS_PATH.match(line)
        assert match is None


class TestExtendsClass:
    def test_matches_extends_class(self):
        line = "extends BaseEntity"
        match = Patterns.EXTENDS_CLASS.match(line)
        assert match is not None
        assert match.group(1) == "BaseEntity"

    def test_matches_with_comment(self):
        line = "extends Player # the main player"
        match = Patterns.EXTENDS_CLASS.match(line)
        assert match is not None
        assert match.group(1) == "Player"

    def test_no_match_for_path(self):
        line = 'extends "res://script.gd"'
        match = Patterns.EXTENDS_CLASS.match(line)
        assert match is None


class TestClassName:
    def test_matches_class_name(self):
        line = "class_name MyClass"
        match = Patterns.CLASS_NAME.match(line)
        assert match is not None
        assert match.group(1) == "MyClass"

    def test_matches_with_whitespace(self):
        line = "  class_name  Entity"
        match = Patterns.CLASS_NAME.match(line)
        assert match is not None


class TestPreload:
    def test_matches_preload(self):
        line = 'var thing = preload("res://thing.gd")'
        matches = Patterns.PRELOAD.findall(line)
        assert len(matches) == 1
        assert matches[0] == "res://thing.gd"

    def test_matches_multiple_preloads(self):
        line = 'var a = preload("res://a.gd"); var b = preload("res://b.gd")'
        matches = Patterns.PRELOAD.findall(line)
        assert len(matches) == 2


class TestLoad:
    def test_matches_load(self):
        line = 'var thing = load("res://thing.gd")'
        matches = Patterns.LOAD.findall(line)
        assert len(matches) == 1
        assert matches[0] == "res://thing.gd"

    def test_no_match_for_preload(self):
        line = 'var thing = preload("res://thing.gd")'
        matches = Patterns.LOAD.findall(line)
        assert len(matches) == 0


class TestTscnPatterns:
    def test_matches_ext_resource(self):
        line = '[ext_resource type="Script" path="res://player.gd" id="1"]'
        match = Patterns.TSCN_EXT_RESOURCE.search(line)
        assert match is not None
        assert match.group(1) == "res://player.gd"
