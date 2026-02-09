from ..analyzer import AnalysisResult
from ..rules.models import RuleCheckResult
from .violations import ViolationTextFormatter


class TextFormatter:
    """Formats analysis results as human-readable text."""

    def __init__(self) -> None:
        self._violation_formatter = ViolationTextFormatter()

    def format(
        self, result: AnalysisResult, rule_result: RuleCheckResult | None = None
    ) -> str:
        lines: list[str] = []

        # Header
        graph = result.graph
        lines.append("=" * 60)
        lines.append("GDScript Dependency Analysis")
        lines.append("=" * 60)
        lines.append("")

        # Statistics
        lines.append(f"Modules: {graph.module_count()}")
        lines.append(f"Dependencies: {graph.dependency_count()}")
        lines.append("")

        # Cycles
        if result.cycles:
            lines.append("-" * 40)
            lines.append(f"CIRCULAR DEPENDENCIES ({len(result.cycles)} found)")
            lines.append("-" * 40)
            for i, cycle in enumerate(result.cycles, start=1):
                lines.append(f"\nCycle {i}:")
                for path in cycle:
                    lines.append(f"  -> {path}")
                lines.append(f"  -> {cycle[0]} (back to start)")
            lines.append("")

        # Module details
        lines.append("-" * 40)
        lines.append("MODULE DEPENDENCIES")
        lines.append("-" * 40)

        for module in sorted(graph.all_modules(), key=lambda m: m.path):
            lines.append(f"\n{module.path}")
            if module.class_name:
                lines.append(f"  class_name: {module.class_name}")

            if module.dependencies:
                for dep in module.dependencies:
                    resolved = "" if dep.resolved else " [unresolved]"
                    line_info = f":{dep.line}" if dep.line else ""
                    lines.append(
                        f"  {dep.dep_type.value}: {dep.target}{line_info}{resolved}"
                    )
            else:
                lines.append("  (no dependencies)")

        # Rule violations
        if rule_result and rule_result.violations:
            lines.append("")
            lines.append(self._violation_formatter.format(rule_result))

        # Errors
        if result.errors:
            lines.append("")
            lines.append("-" * 40)
            lines.append("ERRORS")
            lines.append("-" * 40)
            for error in result.errors:
                lines.append(f"  {error}")

        lines.append("")
        return "\n".join(lines)
