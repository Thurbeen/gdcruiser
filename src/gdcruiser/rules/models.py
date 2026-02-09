"""Rule evaluation models."""

from dataclasses import dataclass, field

from ..config.models import Rule, Severity


@dataclass
class Violation:
    """A rule violation."""

    rule: Rule
    rule_type: str  # "forbidden", "allowed", "required"
    from_module: str
    to_module: str | None = None
    message: str | None = None

    @property
    def severity(self) -> Severity:
        return self.rule.severity

    def to_dict(self) -> dict:
        return {
            "rule": self.rule.name,
            "rule_type": self.rule_type,
            "severity": self.severity.value,
            "from": self.from_module,
            "to": self.to_module,
            "message": self.message or self._default_message(),
        }

    def _default_message(self) -> str:
        if self.rule_type == "forbidden":
            if self.to_module:
                return f"Forbidden dependency: {self.from_module} -> {self.to_module}"
            elif self.rule.circular:
                return f"Circular dependency involving: {self.from_module}"
            elif self.rule.orphan:
                return f"Orphan module: {self.from_module}"
            return f"Forbidden pattern in: {self.from_module}"
        elif self.rule_type == "allowed":
            return f"Dependency not in allowed list: {self.from_module} -> {self.to_module}"
        elif self.rule_type == "required":
            return (
                f"Missing required dependency: {self.from_module} -> {self.to_module}"
            )
        return f"Rule violation: {self.rule.name}"


@dataclass
class RuleCheckResult:
    """Result of checking all rules against the dependency graph."""

    violations: list[Violation] = field(default_factory=list)

    def has_errors(self) -> bool:
        """Check if any error-severity violations exist."""
        return any(v.severity == Severity.ERROR for v in self.violations)

    def has_warnings(self) -> bool:
        """Check if any warning-severity violations exist."""
        return any(v.severity == Severity.WARN for v in self.violations)

    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.ERROR)

    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARN)

    def info_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.INFO)

    def to_dict(self) -> dict:
        return {
            "violations": [v.to_dict() for v in self.violations],
            "summary": {
                "errors": self.error_count(),
                "warnings": self.warning_count(),
                "info": self.info_count(),
            },
        }
