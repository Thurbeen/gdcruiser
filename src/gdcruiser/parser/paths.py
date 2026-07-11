from pathlib import Path


def to_res_path(file_path: Path, project_root: Path) -> str:
    """Convert an absolute path to a ``res://`` path relative to the project root."""
    rel = file_path.resolve().relative_to(project_root.resolve())
    return f"res://{rel.as_posix()}"
