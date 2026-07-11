class SymbolTable:
    """Maps class_name declarations to their file paths."""

    def __init__(self) -> None:
        self._class_to_path: dict[str, str] = {}
        self._path_to_class: dict[str, str] = {}
        # (class_name, existing_path, new_path) for each name registered more
        # than once to a *different* path — Godot itself rejects duplicate
        # global class names, so these are surfaced as warnings.
        self._collisions: list[tuple[str, str, str]] = []

    def register(self, class_name: str, path: str) -> None:
        """Register a class_name declaration."""
        existing = self._class_to_path.get(class_name)
        if existing is not None and existing != path:
            self._collisions.append((class_name, existing, path))
        self._class_to_path[class_name] = path
        self._path_to_class[path] = class_name

    def collisions(self) -> list[tuple[str, str, str]]:
        """Return recorded duplicate-registration collisions."""
        return list(self._collisions)

    def resolve(self, class_name: str) -> str | None:
        """Resolve a class_name to its file path."""
        return self._class_to_path.get(class_name)

    def get_class_name(self, path: str) -> str | None:
        """Get the class_name for a file path."""
        return self._path_to_class.get(path)

    def has_class(self, class_name: str) -> bool:
        """Check if a class_name is registered."""
        return class_name in self._class_to_path

    def all_classes(self) -> dict[str, str]:
        """Return all class_name to path mappings."""
        return dict(self._class_to_path)
