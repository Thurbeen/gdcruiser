from pathlib import Path

from .patterns import Patterns


def parse_autoloads(project_root: Path) -> dict[str, str]:
    """Parse the `[autoload]` section of `project.godot`.

    Returns a mapping from autoload identifier (the global singleton
    name, e.g. `TurnManager`) to its `res://` path. Entries with the
    leading `*` "enabled singleton" marker are stripped to a bare path.
    Returns an empty dict when there is no `project.godot` or no
    `[autoload]` section.
    """
    project_file = project_root / "project.godot"
    if not project_file.exists():
        return {}

    autoloads: dict[str, str] = {}
    in_section = False
    for line in project_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            continue

        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == "[autoload]"
            continue

        if not in_section:
            continue

        match = Patterns.AUTOLOAD_ENTRY.match(stripped)
        if match:
            identifier, path = match.group(1), match.group(2)
            autoloads[identifier] = path

    return autoloads
