from ..analyzer import AnalysisResult
from ..graph.node import DependencyType


class DotFormatter:
    """Formats analysis results as GraphViz DOT format."""

    def __init__(self, show_type: bool = True) -> None:
        self._show_type = show_type

    def format(self, result: AnalysisResult) -> str:
        lines: list[str] = []
        lines.append("digraph dependencies {")
        lines.append("    rankdir=LR;")
        lines.append('    node [shape=box, fontname="monospace"];')
        lines.append('    edge [fontname="monospace", fontsize=10];')
        lines.append("")

        # Find cycle nodes for highlighting
        cycle_nodes: set[str] = set()
        for cycle in result.cycles:
            cycle_nodes.update(cycle)

        # Node declarations
        for module in result.graph.all_modules():
            node_id = self._node_id(module.path)
            label = self._short_path(module.path)
            if module.class_name:
                label = f"{module.class_name}\\n{label}"

            style = ""
            if module.path in cycle_nodes:
                style = ', style=filled, fillcolor="#ffcccc"'

            lines.append(f'    {node_id} [label="{label}"{style}];')

        lines.append("")

        # Edge declarations
        for module in result.graph.all_modules():
            source_id = self._node_id(module.path)
            for dep in module.dependencies:
                target_id = self._node_id(dep.target)
                attrs = []

                if self._show_type:
                    attrs.append(f'label="{self._type_label(dep.dep_type)}"')

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
        return f'"{path}"'

    def _short_path(self, path: str) -> str:
        """Shorten path for display."""
        if path.startswith("res://"):
            return path[6:]
        return path

    def _type_label(self, dep_type: DependencyType) -> str:
        """Get a short label for dependency type."""
        labels = {
            DependencyType.EXTENDS_PATH: "extends",
            DependencyType.EXTENDS_CLASS: "extends",
            DependencyType.PRELOAD: "preload",
            DependencyType.LOAD: "load",
            DependencyType.SCENE_SCRIPT: "script",
        }
        return labels.get(dep_type, "")
