"""Tests for configuration loading and validation."""

import json
import tempfile
from pathlib import Path

import pytest

from gdcruiser.config import (
    Config,
    ConfigError,
    ConfigLoader,
    ConfigValidator,
    PathMatcher,
    Rule,
    Severity,
)


class TestConfigModels:
    def test_severity_values(self):
        assert Severity.ERROR.value == "error"
        assert Severity.WARN.value == "warn"
        assert Severity.INFO.value == "info"
        assert Severity.IGNORE.value == "ignore"

    def test_path_matcher_defaults(self):
        matcher = PathMatcher()
        assert matcher.path is None
        assert matcher.pathNot is None

    def test_path_matcher_with_values(self):
        matcher = PathMatcher(path="^res://ui/", pathNot="^res://ui/test")
        assert matcher.path == "^res://ui/"
        assert matcher.pathNot == "^res://ui/test"

    def test_rule_defaults(self):
        rule = Rule(name="test")
        assert rule.name == "test"
        assert rule.severity == Severity.ERROR
        assert rule.comment is None
        assert rule.from_ is not None
        assert rule.to is not None
        assert rule.circular is False
        assert rule.orphan is False

    def test_config_has_rules(self):
        config = Config()
        assert config.has_rules() is False

        config.forbidden.append(Rule(name="test"))
        assert config.has_rules() is True

    def test_config_all_rules(self):
        config = Config(
            forbidden=[Rule(name="f1")],
            allowed=[Rule(name="a1")],
            required=[Rule(name="r1")],
        )
        rules = config.all_rules()
        assert len(rules) == 3
        assert ("forbidden", config.forbidden[0]) in rules
        assert ("allowed", config.allowed[0]) in rules
        assert ("required", config.required[0]) in rules


class TestConfigLoader:
    def test_discover_no_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))
            assert loader.discover() is None

    def test_discover_gdcruiser_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gdcruiser.json"
            config_path.write_text("{}")

            loader = ConfigLoader(Path(tmpdir))
            assert loader.discover() == config_path

    def test_discover_pyproject_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "pyproject.toml"
            config_path.write_text("[tool.gdcruiser]\n")

            loader = ConfigLoader(Path(tmpdir))
            assert loader.discover() == config_path

    def test_load_empty_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))
            config = loader.load()
            assert config.has_rules() is False

    def test_load_json_forbidden_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gdcruiser.json"
            config_path.write_text(
                json.dumps(
                    {
                        "forbidden": [
                            {
                                "name": "no-ui-to-core",
                                "comment": "UI should not depend on core",
                                "severity": "error",
                                "from": {"path": "^res://ui/"},
                                "to": {"path": "^res://core/"},
                            }
                        ]
                    }
                )
            )

            loader = ConfigLoader(Path(tmpdir))
            config = loader.load()

            assert len(config.forbidden) == 1
            rule = config.forbidden[0]
            assert rule.name == "no-ui-to-core"
            assert rule.comment == "UI should not depend on core"
            assert rule.severity == Severity.ERROR
            assert rule.from_.path == "^res://ui/"
            assert rule.to.path == "^res://core/"

    def test_load_json_allowed_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gdcruiser.json"
            config_path.write_text(
                json.dumps(
                    {
                        "allowed": [
                            {
                                "name": "only-utils",
                                "from": {"path": "^res://scripts/"},
                                "to": {"path": "^res://utils/"},
                            }
                        ]
                    }
                )
            )

            loader = ConfigLoader(Path(tmpdir))
            config = loader.load()

            assert len(config.allowed) == 1
            assert config.allowed[0].name == "only-utils"

    def test_load_json_circular_rule(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gdcruiser.json"
            config_path.write_text(
                json.dumps(
                    {
                        "forbidden": [
                            {
                                "name": "no-cycles",
                                "from": {"path": "^res://core/"},
                                "circular": True,
                            }
                        ]
                    }
                )
            )

            loader = ConfigLoader(Path(tmpdir))
            config = loader.load()

            assert config.forbidden[0].circular is True

    def test_load_json_with_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gdcruiser.json"
            config_path.write_text(
                json.dumps({"options": {"exclude": ["^res://addons/"]}})
            )

            loader = ConfigLoader(Path(tmpdir))
            config = loader.load()

            assert config.options.exclude == ["^res://addons/"]

    def test_load_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gdcruiser.json"
            config_path.write_text("{ invalid json }")

            loader = ConfigLoader(Path(tmpdir))
            with pytest.raises(ConfigError, match="Invalid JSON"):
                loader.load()

    def test_load_nonexistent_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))
            with pytest.raises(ConfigError, match="not found"):
                loader.load(Path(tmpdir) / "missing.json")

    def test_load_pyproject_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "pyproject.toml"
            config_path.write_text(
                """
[tool.gdcruiser]

[[tool.gdcruiser.forbidden]]
name = "no-ui-to-core"
severity = "warn"

[tool.gdcruiser.forbidden.from]
path = "^res://ui/"

[tool.gdcruiser.forbidden.to]
path = "^res://core/"
"""
            )

            loader = ConfigLoader(Path(tmpdir))
            config = loader.load()

            assert len(config.forbidden) == 1
            rule = config.forbidden[0]
            assert rule.name == "no-ui-to-core"
            assert rule.severity == Severity.WARN


class TestConfigValidator:
    def test_validate_empty_config(self):
        config = Config()
        validator = ConfigValidator()
        result = validator.validate(config)
        assert result.is_valid()

    def test_validate_valid_rule(self):
        config = Config(
            forbidden=[
                Rule(
                    name="test",
                    from_=PathMatcher(path="^res://ui/"),
                    to=PathMatcher(path="^res://core/"),
                )
            ]
        )
        validator = ConfigValidator()
        result = validator.validate(config)
        assert result.is_valid()

    def test_validate_invalid_regex(self):
        config = Config(
            forbidden=[
                Rule(
                    name="test",
                    from_=PathMatcher(path="[invalid"),
                )
            ]
        )
        validator = ConfigValidator()
        result = validator.validate(config)
        assert not result.is_valid()
        assert any("Invalid regex" in e.message for e in result.errors)

    def test_validate_rule_without_criteria_warns(self):
        config = Config(forbidden=[Rule(name="empty")])
        validator = ConfigValidator()
        result = validator.validate(config)
        assert result.is_valid()  # warnings don't fail
        assert len(result.warnings) > 0

    def test_validate_circular_rule_has_criteria(self):
        config = Config(forbidden=[Rule(name="cycles", circular=True)])
        validator = ConfigValidator()
        result = validator.validate(config)
        assert result.is_valid()
        assert len(result.warnings) == 0

    def test_validate_options_exclude(self):
        config = Config()
        config.options.exclude = ["[invalid"]
        validator = ConfigValidator()
        result = validator.validate(config)
        assert not result.is_valid()
