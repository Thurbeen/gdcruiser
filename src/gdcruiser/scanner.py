import re
from pathlib import Path


class Scanner:
    """Discovers GDScript and scene files in a Godot project."""

    def __init__(self, project_root: Path, exclude: list[str] | None = None) -> None:
        self._root = project_root.resolve()
        self._exclude_patterns = [re.compile(p) for p in exclude] if exclude else []

    # Suffixes bucketed by a single directory walk.
    _SUFFIXES = (".gd", ".tscn", ".tres")

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

    def _scan(self) -> dict[str, list[Path]]:
        """Walk the project tree once, bucketing files by suffix."""
        buckets: dict[str, list[Path]] = {suffix: [] for suffix in self._SUFFIXES}
        for path in self._root.rglob("*"):
            files = buckets.get(path.suffix)
            if files is not None and path.is_file():
                files.append(path)
        return {
            suffix: self._filter(sorted(paths)) for suffix, paths in buckets.items()
        }

    def find_gdscript_files(self) -> list[Path]:
        """Find all .gd files in the project."""
        return self._scan()[".gd"]

    def find_scene_files(self) -> list[Path]:
        """Find all .tscn files in the project."""
        return self._scan()[".tscn"]

    def find_resource_files(self) -> list[Path]:
        """Find all .tres files in the project."""
        return self._scan()[".tres"]

    def find_all_files(self) -> tuple[list[Path], list[Path], list[Path]]:
        """Find all .gd, .tscn, and .tres files in a single directory walk."""
        buckets = self._scan()
        return (buckets[".gd"], buckets[".tscn"], buckets[".tres"])

    def is_godot_project(self) -> bool:
        """Check if the directory is a Godot project (has project.godot)."""
        return (self._root / "project.godot").exists()

    @property
    def root(self) -> Path:
        """Return the project root path."""
        return self._root
