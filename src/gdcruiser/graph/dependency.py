from .node import Module, Dependency


class DependencyGraph:
    """Adjacency list representation of module dependencies."""

    def __init__(self) -> None:
        self._modules: dict[str, Module] = {}
        # Reverse adjacency (target path -> list of (source path, dep)), built
        # lazily on first `get_dependents` call and invalidated whenever a
        # module is added. Avoids re-scanning every module on each lookup.
        self._dependents_index: dict[str, list[tuple[str, Dependency]]] | None = None

    def add_module(self, module: Module) -> None:
        """Add a module to the graph."""
        self._modules[module.path] = module
        self._dependents_index = None

    def get_module(self, path: str) -> Module | None:
        """Get a module by path."""
        return self._modules.get(path)

    def has_module(self, path: str) -> bool:
        """Check if a module exists in the graph."""
        return path in self._modules

    def all_modules(self) -> list[Module]:
        """Return all modules in the graph."""
        return list(self._modules.values())

    def get_dependencies(self, path: str) -> list[Dependency]:
        """Get all dependencies for a module."""
        module = self._modules.get(path)
        return module.dependencies if module else []

    def get_dependents(self, path: str) -> list[tuple[str, Dependency]]:
        """Get all modules that depend on the given path."""
        if self._dependents_index is None:
            self._dependents_index = self._build_dependents_index()
        return self._dependents_index.get(path, [])

    def _build_dependents_index(self) -> dict[str, list[tuple[str, Dependency]]]:
        """Build the reverse adjacency index in a single pass over all edges."""
        index: dict[str, list[tuple[str, Dependency]]] = {}
        for module in self._modules.values():
            for dep in module.dependencies:
                index.setdefault(dep.target, []).append((module.path, dep))
        return index

    def module_count(self) -> int:
        """Return the number of modules in the graph."""
        return len(self._modules)

    def dependency_count(self) -> int:
        """Return the total number of dependencies."""
        return sum(len(m.dependencies) for m in self._modules.values())

    def to_dict(self) -> dict:
        """Convert graph to dictionary representation."""
        return {
            "modules": {path: m.to_dict() for path, m in self._modules.items()},
            "stats": {
                "module_count": self.module_count(),
                "dependency_count": self.dependency_count(),
            },
        }
