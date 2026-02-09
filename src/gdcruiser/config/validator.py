"""Configuration validation."""

import re
from dataclasses import dataclass, field

from .models import Config, PathMatcher, Rule


@dataclass
class ValidationError:
    """A configuration validation error."""

    path: str
    message: str


@dataclass
class ValidationResult:
    """Result of validating a configuration."""

    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Configuration is valid if no errors exist."""
        return len(self.errors) == 0

    def add_error(self, path: str, message: str) -> None:
        self.errors.append(ValidationError(path, message))

    def add_warning(self, path: str, message: str) -> None:
        self.warnings.append(ValidationError(path, message))


class ConfigValidator:
    """Validates gdcruiser configuration."""

    def validate(self, config: Config) -> ValidationResult:
        """Validate the configuration."""
        result = ValidationResult()

        for i, rule in enumerate(config.forbidden):
            self._validate_rule(rule, f"forbidden[{i}]", result)

        for i, rule in enumerate(config.allowed):
            self._validate_rule(rule, f"allowed[{i}]", result)

        for i, rule in enumerate(config.required):
            self._validate_rule(rule, f"required[{i}]", result)

        self._validate_options(config, result)

        return result

    def _validate_rule(self, rule: Rule, path: str, result: ValidationResult) -> None:
        """Validate a single rule."""
        if not rule.name:
            result.add_error(path, "Rule must have a name")

        if rule.from_:
            self._validate_path_matcher(rule.from_, f"{path}.from", result)

        if rule.to:
            self._validate_path_matcher(rule.to, f"{path}.to", result)

        # Check that rule has some matching criteria
        has_path_criteria = (
            rule.from_
            and (rule.from_.path or rule.from_.pathNot)
            or rule.to
            and (rule.to.path or rule.to.pathNot)
        )
        has_special_criteria = rule.circular or rule.orphan

        if not has_path_criteria and not has_special_criteria:
            result.add_warning(
                path, "Rule has no matching criteria and will match nothing"
            )

    def _validate_path_matcher(
        self, matcher: PathMatcher, path: str, result: ValidationResult
    ) -> None:
        """Validate a path matcher's regex patterns."""
        if matcher.path:
            self._validate_regex(matcher.path, f"{path}.path", result)

        if matcher.pathNot:
            self._validate_regex(matcher.pathNot, f"{path}.pathNot", result)

    def _validate_regex(
        self, pattern: str, path: str, result: ValidationResult
    ) -> None:
        """Validate a regex pattern."""
        try:
            re.compile(pattern)
        except re.error as e:
            result.add_error(path, f"Invalid regex pattern '{pattern}': {e}")

    def _validate_options(self, config: Config, result: ValidationResult) -> None:
        """Validate configuration options."""
        for i, pattern in enumerate(config.options.exclude):
            self._validate_regex(pattern, f"options.exclude[{i}]", result)
