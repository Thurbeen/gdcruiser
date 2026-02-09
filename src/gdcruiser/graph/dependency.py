from .node import Module, Dependency


class DependencyGraph:
    """Adjacency list representation of module dependencies."""

    def __init__(self) -> None:
        self._modules: dict[str, Module] = {}

    def add_module(self, module: Module) -> None:
        """Add a module to the graph."""
        self._modules[module.path] = module

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
        dependents = []
        for module in self._modules.values():
            for dep in module.dependencies:
                if dep.target == path:
                    dependents.append((module.path, dep))
        return dependents

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
