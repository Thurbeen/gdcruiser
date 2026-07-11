from gdcruiser.parser import patterns as Patterns


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


class TestTypedRef:
    def test_var_typed(self):
        match = Patterns.TYPED_REF.search("var x: Player")
        assert match is not None
        assert match.group(1) == "Player"

    def test_param_typed(self):
        matches = Patterns.TYPED_REF.findall("func foo(a: Foo, b: Bar) -> void:")
        assert "Foo" in matches
        assert "Bar" in matches

    def test_no_match_for_lowercase(self):
        assert Patterns.TYPED_REF.search("var x: int = 0") is None or (
            Patterns.TYPED_REF.search("var x: int = 0").group(1)[0].isupper()
        )


class TestReturnType:
    def test_matches_return_type(self):
        match = Patterns.RETURN_TYPE.search("func f() -> Player:")
        assert match is not None
        assert match.group(1) == "Player"


class TestIsAsRef:
    def test_matches_is(self):
        match = Patterns.IS_AS_REF.search("if obj is Player:")
        assert match is not None
        assert match.group(1) == "Player"

    def test_matches_as(self):
        match = Patterns.IS_AS_REF.search("var p = obj as Player")
        assert match is not None
        assert match.group(1) == "Player"


class TestMemberAccess:
    def test_static_call(self):
        matches = Patterns.MEMBER_ACCESS.findall("var x = SkillSystem.dispatch()")
        assert "SkillSystem" in matches

    def test_constant_access(self):
        matches = Patterns.MEMBER_ACCESS.findall("var t = MiracleSystem.Trigger")
        assert "MiracleSystem" in matches

    def test_no_match_for_property_access(self):
        # `obj.Foo.bar` — Foo here is a property of obj, not a class.
        matches = Patterns.MEMBER_ACCESS.findall("obj.Foo.bar")
        assert "Foo" not in matches


class TestResourcePath:
    def test_matches_gd(self):
        match = Patterns.RESOURCE_PATH.search('path="res://player.gd"')
        assert match is not None
        assert match.group(1) == "res://player.gd"

    def test_matches_tres(self):
        match = Patterns.RESOURCE_PATH.search('path="res://data/foo.tres"')
        assert match is not None
        assert match.group(1) == "res://data/foo.tres"


class TestResourceScriptClass:
    def test_extracts_script_class(self):
        line = '[gd_resource type="Resource" script_class="HealSkill" load_steps=2]'
        match = Patterns.RESOURCE_SCRIPT_CLASS.search(line)
        assert match is not None
        assert match.group(1) == "HealSkill"
