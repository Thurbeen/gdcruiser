from .dependency import DependencyGraph


class CycleDetector:
    """Detects cycles in dependency graph using Tarjan's algorithm."""

    def __init__(self, graph: DependencyGraph) -> None:
        self._graph = graph
        self._index = 0
        self._stack: list[str] = []
        self._on_stack: set[str] = set()
        self._indices: dict[str, int] = {}
        self._lowlinks: dict[str, int] = {}
        self._sccs: list[list[str]] = []

    def find_cycles(self) -> list[list[str]]:
        """Find all strongly connected components with more than one node (cycles)."""
        self._index = 0
        self._stack = []
        self._on_stack = set()
        self._indices = {}
        self._lowlinks = {}
        self._sccs = []

        for module in self._graph.all_modules():
            if module.path not in self._indices:
                self._strongconnect(module.path)

        return [scc for scc in self._sccs if len(scc) > 1]

    def _strongconnect(self, path: str) -> None:
        """Tarjan's algorithm recursive helper."""
        self._indices[path] = self._index
        self._lowlinks[path] = self._index
        self._index += 1
        self._stack.append(path)
        self._on_stack.add(path)

        for dep in self._graph.get_dependencies(path):
            target = dep.target
            if not self._graph.has_module(target):
                continue

            if target not in self._indices:
                self._strongconnect(target)
                self._lowlinks[path] = min(self._lowlinks[path], self._lowlinks[target])
            elif target in self._on_stack:
                self._lowlinks[path] = min(self._lowlinks[path], self._indices[target])

        if self._lowlinks[path] == self._indices[path]:
            scc: list[str] = []
            while True:
                w = self._stack.pop()
                self._on_stack.remove(w)
                scc.append(w)
                if w == path:
                    break
            self._sccs.append(scc)
