from ..analyzer import AnalysisResult
from ..graph.node import DependencyType


class MermaidFormatter:
    """Formats analysis results as a Mermaid flowchart diagram."""

    def __init__(self, show_type: bool = True) -> None:
        self._show_type = show_type

    def format(self, result: AnalysisResult) -> str:
        lines: list[str] = []
        lines.append("graph LR")

        # Find cycle nodes for highlighting
        cycle_nodes: set[str] = set()
        for cycle in result.cycles:
            cycle_nodes.update(cycle)

        # Node declarations
        cycle_node_ids: list[str] = []
        for module in result.graph.all_modules():
            node_id = self._node_id(module.path)
            label = self._short_path(module.path)
            if module.class_name:
                label = f"{module.class_name}<br/>{label}"

            lines.append(f'    {node_id}["{label}"]')

            if module.path in cycle_nodes:
                cycle_node_ids.append(node_id)

        lines.append("")

        # Edge declarations
        edge_index = 0
        unresolved_edges: list[int] = []
        for module in result.graph.all_modules():
            source_id = self._node_id(module.path)
            for dep in module.dependencies:
                target_id = self._node_id(dep.target)
                type_label = self._type_label(dep.dep_type) if self._show_type else ""
                is_cycle_edge = module.path in cycle_nodes and dep.target in cycle_nodes

                if is_cycle_edge:
                    if type_label:
                        lines.append(f"    {source_id} == {type_label} ==> {target_id}")
                    else:
                        lines.append(f"    {source_id} ==> {target_id}")
                elif type_label:
                    lines.append(f"    {source_id} -- {type_label} --> {target_id}")
                else:
                    lines.append(f"    {source_id} --> {target_id}")

                if not dep.resolved:
                    unresolved_edges.append(edge_index)

                edge_index += 1

        # Style definitions
        if cycle_node_ids:
            lines.append("")
            lines.append("    classDef cycle fill:#ffcccc,stroke:#cc0000")
            lines.append(f"    class {','.join(cycle_node_ids)} cycle")

        for idx in unresolved_edges:
            lines.append(f"    linkStyle {idx} stroke-dasharray:5,stroke:red")

        return "\n".join(lines)

    def _node_id(self, path: str) -> str:
        """Convert a res:// path to a valid Mermaid node ID."""
        return path.replace("://", "_").replace("/", "_").replace(".", "_")

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
