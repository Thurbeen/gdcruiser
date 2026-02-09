import re
from pathlib import Path


class Scanner:
    """Discovers GDScript and scene files in a Godot project."""

    def __init__(self, project_root: Path, exclude: list[str] | None = None) -> None:
        self._root = project_root.resolve()
        self._exclude_patterns = [re.compile(p) for p in exclude] if exclude else []

    def _filter(self, files: list[Path]) -> list[Path]:
        """Remove files whose res:// path matches any exclude pattern."""
        if not self._exclude_patterns:
            return files
        result = []
        for f in files:
            rel = "res://" + f.relative_to(self._root).as_posix()
            if not any(p.search(rel) for p in self._exclude_patterns):
                result.append(f)
        return result

    def find_gdscript_files(self) -> list[Path]:
        """Find all .gd files in the project."""
        return self._filter(sorted(self._root.rglob("*.gd")))

    def find_scene_files(self) -> list[Path]:
        """Find all .tscn files in the project."""
        return self._filter(sorted(self._root.rglob("*.tscn")))

    def find_all_files(self) -> tuple[list[Path], list[Path]]:
        """Find all .gd and .tscn files."""
        return self.find_gdscript_files(), self.find_scene_files()

    def is_godot_project(self) -> bool:
        """Check if the directory is a Godot project (has project.godot)."""
        return (self._root / "project.godot").exists()

    @property
    def root(self) -> Path:
        """Return the project root path."""
        return self._root
