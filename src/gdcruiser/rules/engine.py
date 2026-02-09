"""Rule evaluation engine."""

import re

from ..config.models import Config, Rule, Severity
from ..graph.dependency import DependencyGraph
from .matcher import PathMatcherCompiled
from .models import RuleCheckResult, Violation


class RuleEngine:
    """Evaluates rules against a dependency graph."""

    def __init__(self, config: Config, graph: DependencyGraph) -> None:
        self._config = config
        self._graph = graph
        self._exclude_patterns = [re.compile(p) for p in config.options.exclude]

    def check_all(self, cycles: list[list[str]] | None = None) -> RuleCheckResult:
        """Check all rules and return violations."""
        result = RuleCheckResult()

        for rule in self._config.forbidden:
            self._check_forbidden(rule, result, cycles)

        for rule in self._config.allowed:
            self._check_allowed(rule, result)

        for rule in self._config.required:
            self._check_required(rule, result)

        return result

    def _is_excluded(self, path: str) -> bool:
        """Check if a path is excluded from rule checking."""
        return any(p.search(path) for p in self._exclude_patterns)

    def _check_forbidden(
        self,
        rule: Rule,
        result: RuleCheckResult,
        cycles: list[list[str]] | None,
    ) -> None:
        """Check a forbidden rule."""
        if rule.severity == Severity.IGNORE:
            return

        from_matcher = PathMatcherCompiled(rule.from_)
        to_matcher = PathMatcherCompiled(rule.to)

        # Handle circular dependency rules
        if rule.circular and cycles:
            self._check_circular_forbidden(rule, from_matcher, cycles, result)
            return

        # Handle orphan rules
        if rule.orphan:
            self._check_orphan_forbidden(rule, from_matcher, result)
            return

        # Regular dependency rules
        for module in self._graph.all_modules():
            if self._is_excluded(module.path):
                continue

            if not from_matcher.matches(module.path):
                continue

            for dep in module.dependencies:
                if self._is_excluded(dep.target):
                    continue

                if to_matcher.matches(dep.target):
                    result.violations.append(
                        Violation(
                            rule=rule,
                            rule_type="forbidden",
                            from_module=module.path,
                            to_module=dep.target,
                        )
                    )

    def _check_circular_forbidden(
        self,
        rule: Rule,
        from_matcher: PathMatcherCompiled,
        cycles: list[list[str]],
        result: RuleCheckResult,
    ) -> None:
        """Check for forbidden circular dependencies."""
        reported_cycles: set[tuple[str, ...]] = set()

        for cycle in cycles:
            # Check if any module in the cycle matches the from pattern
            matching_modules = [
                path
                for path in cycle
                if from_matcher.matches(path) and not self._is_excluded(path)
            ]

            if matching_modules:
                # Create a normalized cycle key to avoid duplicates
                cycle_key = tuple(sorted(cycle))
                if cycle_key not in reported_cycles:
                    reported_cycles.add(cycle_key)
                    result.violations.append(
                        Violation(
                            rule=rule,
                            rule_type="forbidden",
                            from_module=" -> ".join(cycle),
                            message=f"Circular dependency: {' -> '.join(cycle)} -> {cycle[0]}",
                        )
                    )

    def _check_orphan_forbidden(
        self,
        rule: Rule,
        from_matcher: PathMatcherCompiled,
        result: RuleCheckResult,
    ) -> None:
        """Check for forbidden orphan modules (no dependencies)."""
        for module in self._graph.all_modules():
            if self._is_excluded(module.path):
                continue

            if not from_matcher.matches(module.path):
                continue

            # Check if module has no dependencies and no dependents
            has_deps = len(module.dependencies) > 0
            has_dependents = len(self._graph.get_dependents(module.path)) > 0

            if not has_deps and not has_dependents:
                result.violations.append(
                    Violation(
                        rule=rule,
                        rule_type="forbidden",
                        from_module=module.path,
                    )
                )

    def _check_allowed(self, rule: Rule, result: RuleCheckResult) -> None:
        """Check an allowed rule (dependencies must match pattern)."""
        if rule.severity == Severity.IGNORE:
            return

        from_matcher = PathMatcherCompiled(rule.from_)
        to_matcher = PathMatcherCompiled(rule.to)

        for module in self._graph.all_modules():
            if self._is_excluded(module.path):
                continue

            if not from_matcher.matches(module.path):
                continue

            for dep in module.dependencies:
                if self._is_excluded(dep.target):
                    continue

                # In allowed rules, violations are dependencies that DON'T match
                if not to_matcher.matches(dep.target):
                    result.violations.append(
                        Violation(
                            rule=rule,
                            rule_type="allowed",
                            from_module=module.path,
                            to_module=dep.target,
                        )
                    )

    def _check_required(self, rule: Rule, result: RuleCheckResult) -> None:
        """Check a required rule (matching modules must have dependency)."""
        if rule.severity == Severity.IGNORE:
            return

        from_matcher = PathMatcherCompiled(rule.from_)
        to_matcher = PathMatcherCompiled(rule.to)

        # Required rules only make sense with specific 'to' patterns
        if to_matcher.matches_any():
            return

        for module in self._graph.all_modules():
            if self._is_excluded(module.path):
                continue

            if not from_matcher.matches(module.path):
                continue

            # Check if module has at least one dependency matching 'to' pattern
            has_required_dep = any(
                to_matcher.matches(dep.target)
                for dep in module.dependencies
                if not self._is_excluded(dep.target)
            )

            if not has_required_dep:
                result.violations.append(
                    Violation(
                        rule=rule,
                        rule_type="required",
                        from_module=module.path,
                        to_module=rule.to.path if rule.to else None,
                        message=f"Missing required dependency matching '{rule.to.path}'",
                    )
                )
