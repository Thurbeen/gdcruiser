"""Shared helpers for graph output formatters (DOT, Mermaid)."""

from ..analyzer import AnalysisResult
from ..graph.node import DependencyType

_TYPE_LABELS: dict[DependencyType, str] = {
    DependencyType.EXTENDS_PATH: "extends",
    DependencyType.EXTENDS_CLASS: "extends",
    DependencyType.PRELOAD: "preload",
    DependencyType.LOAD: "load",
    DependencyType.SCENE_SCRIPT: "script",
    DependencyType.CLASS_REF: "uses",
    DependencyType.RESOURCE_REF: "resource",
}


def type_label(dep_type: DependencyType) -> str:
    """Return a short human-readable label for a dependency type."""
    return _TYPE_LABELS.get(dep_type, "")


def short_path(path: str) -> str:
    """Strip the ``res://`` prefix for display."""
    if path.startswith("res://"):
        return path[6:]
    return path


def cycle_node_set(result: AnalysisResult) -> set[str]:
    """Return the set of all module paths that participate in a cycle."""
    nodes: set[str] = set()
    for cycle in result.cycles:
        nodes.update(cycle)
    return nodes


def escape_dot_label(label: str) -> str:
    """Escape a string for use inside a DOT double-quoted label."""
    return label.replace("\\", "\\\\").replace('"', '\\"')


def escape_mermaid_label(label: str) -> str:
    """Escape a string for use inside a Mermaid ``["..."]`` label.

    Mermaid has no backslash escape; double quotes are encoded as the HTML
    entity ``&quot;`` (already-safe ``<br/>`` separators are inserted by the
    caller and must survive, so only quotes are touched here).
    """
    return label.replace('"', "&quot;")
