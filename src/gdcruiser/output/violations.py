"""Violation output formatters."""

from ..config.models import Severity
from ..rules.models import RuleCheckResult


class ViolationTextFormatter:
    """Formats violations as human-readable text."""

    SEVERITY_ICONS = {
        Severity.ERROR: "ERROR",
        Severity.WARN: "WARN",
        Severity.INFO: "INFO",
        Severity.IGNORE: "IGNORE",
    }

    def format(self, result: RuleCheckResult) -> str:
        """Format violations as text."""
        if not result.violations:
            return ""

        lines: list[str] = []
        lines.append("-" * 40)
        lines.append(
            f"RULE VIOLATIONS ({result.error_count()} errors, "
            f"{result.warning_count()} warnings)"
        )
        lines.append("-" * 40)

        # Group violations by rule
        by_rule: dict[str, list] = {}
        for v in result.violations:
            rule_name = v.rule.name
            if rule_name not in by_rule:
                by_rule[rule_name] = []
            by_rule[rule_name].append(v)

        for rule_name, violations in by_rule.items():
            first = violations[0]
            severity_str = self.SEVERITY_ICONS.get(first.severity, "?")

            lines.append(f"\n[{severity_str}] {rule_name}")
            if first.rule.comment:
                lines.append(f"  {first.rule.comment}")

            for v in violations:
                if v.to_module:
                    lines.append(f"    {v.from_module} -> {v.to_module}")
                else:
                    lines.append(f"    {v.from_module}")

        return "\n".join(lines)


class ViolationJsonFormatter:
    """Formats violations as JSON-compatible dict."""

    def format(self, result: RuleCheckResult) -> dict:
        """Format violations as dictionary."""
        return result.to_dict()
