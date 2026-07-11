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

    def _successors(self, path: str) -> list[str]:
        """Return in-graph dependency targets for a node (deduplicated)."""
        seen: set[str] = set()
        targets: list[str] = []
        for dep in self._graph.get_dependencies(path):
            target = dep.target
            if target in seen or not self._graph.has_module(target):
                continue
            seen.add(target)
            targets.append(target)
        return targets

    def _strongconnect(self, start: str) -> None:
        """Iterative Tarjan's algorithm (explicit stack avoids RecursionError)."""
        successors: dict[str, list[str]] = {}
        # Each work-stack frame is [node, next-successor-index].
        work: list[list] = [[start, 0]]

        while work:
            frame = work[-1]
            node, next_i = frame

            if next_i == 0:
                self._indices[node] = self._index
                self._lowlinks[node] = self._index
                self._index += 1
                self._stack.append(node)
                self._on_stack.add(node)
                successors[node] = self._successors(node)

            recursed = False
            node_successors = successors[node]
            while next_i < len(node_successors):
                target = node_successors[next_i]
                next_i += 1
                if target not in self._indices:
                    frame[1] = next_i
                    work.append([target, 0])
                    recursed = True
                    break
                elif target in self._on_stack:
                    self._lowlinks[node] = min(
                        self._lowlinks[node], self._indices[target]
                    )

            if recursed:
                continue

            # All successors processed — close out this node.
            if self._lowlinks[node] == self._indices[node]:
                scc: list[str] = []
                while True:
                    w = self._stack.pop()
                    self._on_stack.remove(w)
                    scc.append(w)
                    if w == node:
                        break
                self._sccs.append(scc)

            work.pop()
            if work:
                parent = work[-1][0]
                self._lowlinks[parent] = min(
                    self._lowlinks[parent], self._lowlinks[node]
                )
