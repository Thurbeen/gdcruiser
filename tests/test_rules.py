"""Tests for rule evaluation."""

from gdcruiser.config import Config, ConfigOptions, PathMatcher, Rule, Severity
from gdcruiser.graph.dependency import DependencyGraph
from gdcruiser.graph.node import Dependency, DependencyType, Module
from gdcruiser.rules import PathMatcherCompiled, RuleEngine, Violation
from gdcruiser.rules.models import RuleCheckResult


class TestPathMatcherCompiled:
    def test_empty_matcher_matches_all(self):
        matcher = PathMatcherCompiled(PathMatcher())
        assert matcher.matches("res://anything.gd")
        assert matcher.matches("res://ui/button.gd")
        assert matcher.matches_any()

    def test_path_pattern_matches(self):
        matcher = PathMatcherCompiled(PathMatcher(path="^res://ui/"))
        assert matcher.matches("res://ui/button.gd")
        assert matcher.matches("res://ui/menu/main.gd")
        assert not matcher.matches("res://core/player.gd")
        assert not matcher.matches_any()

    def test_path_not_pattern(self):
        matcher = PathMatcherCompiled(PathMatcher(pathNot="^res://test/"))
        assert matcher.matches("res://ui/button.gd")
        assert not matcher.matches("res://test/mock.gd")

    def test_combined_patterns(self):
        matcher = PathMatcherCompiled(PathMatcher(path="^res://ui/", pathNot="test"))
        assert matcher.matches("res://ui/button.gd")
        assert not matcher.matches("res://ui/test_button.gd")
        assert not matcher.matches("res://core/player.gd")


class TestRuleCheckResult:
    def test_empty_result(self):
        result = RuleCheckResult()
        assert not result.has_errors()
        assert not result.has_warnings()
        assert result.error_count() == 0

    def test_with_violations(self):
        rule_error = Rule(name="err", severity=Severity.ERROR)
        rule_warn = Rule(name="warn", severity=Severity.WARN)
        rule_info = Rule(name="info", severity=Severity.INFO)

        result = RuleCheckResult(
            violations=[
                Violation(rule=rule_error, rule_type="forbidden", from_module="a"),
                Violation(rule=rule_warn, rule_type="forbidden", from_module="b"),
                Violation(rule=rule_info, rule_type="forbidden", from_module="c"),
            ]
        )

        assert result.has_errors()
        assert result.has_warnings()
        assert result.error_count() == 1
        assert result.warning_count() == 1
        assert result.info_count() == 1

    def test_to_dict(self):
        rule = Rule(name="test", severity=Severity.ERROR)
        result = RuleCheckResult(
            violations=[
                Violation(
                    rule=rule,
                    rule_type="forbidden",
                    from_module="res://a.gd",
                    to_module="res://b.gd",
                )
            ]
        )

        data = result.to_dict()
        assert "violations" in data
        assert "summary" in data
        assert data["summary"]["errors"] == 1


class TestViolation:
    def test_violation_to_dict(self):
        rule = Rule(name="test-rule", severity=Severity.ERROR)
        violation = Violation(
            rule=rule,
            rule_type="forbidden",
            from_module="res://ui/button.gd",
            to_module="res://core/engine.gd",
        )

        data = violation.to_dict()
        assert data["rule"] == "test-rule"
        assert data["rule_type"] == "forbidden"
        assert data["severity"] == "error"
        assert data["from"] == "res://ui/button.gd"
        assert data["to"] == "res://core/engine.gd"

    def test_default_message_forbidden(self):
        rule = Rule(name="test")
        v = Violation(
            rule=rule,
            rule_type="forbidden",
            from_module="a.gd",
            to_module="b.gd",
        )
        assert "Forbidden dependency" in v._default_message()

    def test_default_message_allowed(self):
        rule = Rule(name="test")
        v = Violation(
            rule=rule, rule_type="allowed", from_module="a.gd", to_module="b.gd"
        )
        assert "not in allowed list" in v._default_message()


class TestRuleEngine:
    def _make_graph(self, modules: list[Module]) -> DependencyGraph:
        graph = DependencyGraph()
        for m in modules:
            graph.add_module(m)
        return graph

    def test_no_rules_no_violations(self):
        config = Config()
        graph = self._make_graph([Module(path="res://test.gd")])
        engine = RuleEngine(config, graph)
        result = engine.check_all()
        assert len(result.violations) == 0

    def test_forbidden_rule_matches(self):
        config = Config(
            forbidden=[
                Rule(
                    name="no-ui-to-core",
                    from_=PathMatcher(path="^res://ui/"),
                    to=PathMatcher(path="^res://core/"),
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(
                    path="res://ui/button.gd",
                    dependencies=[
                        Dependency(
                            target="res://core/engine.gd",
                            dep_type=DependencyType.PRELOAD,
                        )
                    ],
                ),
                Module(path="res://core/engine.gd"),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()

        assert len(result.violations) == 1
        v = result.violations[0]
        assert v.rule.name == "no-ui-to-core"
        assert v.from_module == "res://ui/button.gd"
        assert v.to_module == "res://core/engine.gd"

    def test_forbidden_rule_no_match(self):
        config = Config(
            forbidden=[
                Rule(
                    name="no-ui-to-core",
                    from_=PathMatcher(path="^res://ui/"),
                    to=PathMatcher(path="^res://core/"),
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(
                    path="res://ui/button.gd",
                    dependencies=[
                        Dependency(
                            target="res://ui/utils.gd", dep_type=DependencyType.PRELOAD
                        )
                    ],
                ),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()
        assert len(result.violations) == 0

    def test_allowed_rule_violation(self):
        config = Config(
            allowed=[
                Rule(
                    name="only-ui-deps",
                    from_=PathMatcher(path="^res://ui/"),
                    to=PathMatcher(path="^res://ui/"),
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(
                    path="res://ui/button.gd",
                    dependencies=[
                        Dependency(
                            target="res://core/engine.gd",
                            dep_type=DependencyType.PRELOAD,
                        )
                    ],
                ),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()

        assert len(result.violations) == 1
        assert result.violations[0].rule_type == "allowed"

    def test_allowed_rule_no_violation(self):
        config = Config(
            allowed=[
                Rule(
                    name="only-ui-deps",
                    from_=PathMatcher(path="^res://ui/"),
                    to=PathMatcher(path="^res://ui/"),
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(
                    path="res://ui/button.gd",
                    dependencies=[
                        Dependency(
                            target="res://ui/utils.gd", dep_type=DependencyType.PRELOAD
                        )
                    ],
                ),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()
        assert len(result.violations) == 0

    def test_required_rule_missing_dep(self):
        config = Config(
            required=[
                Rule(
                    name="must-use-logger",
                    from_=PathMatcher(path="^res://core/"),
                    to=PathMatcher(path="res://utils/logger.gd"),
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(path="res://core/engine.gd", dependencies=[]),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()

        assert len(result.violations) == 1
        assert result.violations[0].rule_type == "required"

    def test_required_rule_has_dep(self):
        config = Config(
            required=[
                Rule(
                    name="must-use-logger",
                    from_=PathMatcher(path="^res://core/"),
                    to=PathMatcher(path="res://utils/logger.gd"),
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(
                    path="res://core/engine.gd",
                    dependencies=[
                        Dependency(
                            target="res://utils/logger.gd",
                            dep_type=DependencyType.PRELOAD,
                        )
                    ],
                ),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()
        assert len(result.violations) == 0

    def test_circular_rule(self):
        config = Config(
            forbidden=[
                Rule(
                    name="no-cycles-in-core",
                    from_=PathMatcher(path="^res://core/"),
                    circular=True,
                )
            ]
        )

        graph = self._make_graph([Module(path="res://core/a.gd")])
        cycles = [["res://core/a.gd", "res://core/b.gd"]]

        engine = RuleEngine(config, graph)
        result = engine.check_all(cycles=cycles)

        assert len(result.violations) == 1
        assert "Circular dependency" in result.violations[0].message

    def test_orphan_rule(self):
        config = Config(
            forbidden=[
                Rule(
                    name="no-orphans",
                    from_=PathMatcher(path="^res://"),
                    orphan=True,
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(path="res://orphan.gd", dependencies=[]),
                Module(
                    path="res://connected.gd",
                    dependencies=[
                        Dependency(
                            target="res://utils.gd", dep_type=DependencyType.PRELOAD
                        )
                    ],
                ),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()

        # orphan.gd has no deps and no dependents
        assert len(result.violations) == 1
        assert result.violations[0].from_module == "res://orphan.gd"

    def test_exclude_option(self):
        config = Config(
            forbidden=[
                Rule(
                    name="no-deps",
                    from_=PathMatcher(path="^res://"),
                    to=PathMatcher(path="^res://"),
                )
            ],
            options=ConfigOptions(exclude=["^res://addons/"]),
        )

        graph = self._make_graph(
            [
                Module(
                    path="res://addons/plugin.gd",
                    dependencies=[
                        Dependency(
                            target="res://core/engine.gd",
                            dep_type=DependencyType.PRELOAD,
                        )
                    ],
                ),
                Module(
                    path="res://game.gd",
                    dependencies=[
                        Dependency(
                            target="res://core/engine.gd",
                            dep_type=DependencyType.PRELOAD,
                        )
                    ],
                ),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()

        # Only game.gd should be flagged, addons/ is excluded
        assert len(result.violations) == 1
        assert result.violations[0].from_module == "res://game.gd"

    def test_ignore_severity_skipped(self):
        config = Config(
            forbidden=[
                Rule(
                    name="ignored-rule",
                    severity=Severity.IGNORE,
                    from_=PathMatcher(path="^res://"),
                    to=PathMatcher(path="^res://"),
                )
            ]
        )

        graph = self._make_graph(
            [
                Module(
                    path="res://a.gd",
                    dependencies=[
                        Dependency(target="res://b.gd", dep_type=DependencyType.PRELOAD)
                    ],
                ),
            ]
        )

        engine = RuleEngine(config, graph)
        result = engine.check_all()
        assert len(result.violations) == 0
