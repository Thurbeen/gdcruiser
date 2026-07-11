from ..analyzer import AnalysisResult
from ..rules.models import RuleCheckResult
from .labels import cycle_node_set, escape_dot_label, short_path, type_label


class DotFormatter:
    """Formats analysis results as GraphViz DOT format."""

    def __init__(self, show_type: bool = True) -> None:
        self._show_type = show_type

    def format(
        self, result: AnalysisResult, rule_result: RuleCheckResult | None = None
    ) -> str:
        lines: list[str] = []
        lines.append("digraph dependencies {")
        lines.append("    rankdir=LR;")
        lines.append('    node [shape=box, fontname="monospace"];')
        lines.append('    edge [fontname="monospace", fontsize=10];')
        lines.append("")

        cycle_nodes = cycle_node_set(result)

        # Node declarations
        for module in result.graph.all_modules():
            node_id = self._node_id(module.path)
            label = short_path(module.path)
            if module.class_name:
                label = f"{module.class_name}\\n{label}"

            style = ""
            if module.path in cycle_nodes:
                style = ', style=filled, fillcolor="#ffcccc"'

            lines.append(f'    {node_id} [label="{escape_dot_label(label)}"{style}];')

        lines.append("")

        # Edge declarations
        for module in result.graph.all_modules():
            source_id = self._node_id(module.path)
            for dep in module.dependencies:
                target_id = self._node_id(dep.target)
                attrs = []

                if self._show_type:
                    attrs.append(
                        f'label="{escape_dot_label(type_label(dep.dep_type))}"'
                    )

                if not dep.resolved:
                    attrs.append("style=dashed")
                    attrs.append('color="red"')

                # Check if this edge is part of a cycle
                if module.path in cycle_nodes and dep.target in cycle_nodes:
                    attrs.append('color="red"')
                    attrs.append("penwidth=2")

                attr_str = f" [{', '.join(attrs)}]" if attrs else ""
                lines.append(f"    {source_id} -> {target_id}{attr_str};")

        lines.append("}")
        return "\n".join(lines)

    def _node_id(self, path: str) -> str:
        """Convert a path to a valid DOT node ID."""
        return f'"{escape_dot_label(path)}"'
