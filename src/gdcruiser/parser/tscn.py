from pathlib import Path

from ..graph.node import Module, Dependency, DependencyType
from .patterns import Patterns


class TscnParser:
    """Parses TSCN scene files to extract script dependencies."""

    def parse(self, file_path: Path, project_root: Path) -> Module:
        """Parse a TSCN file and return a Module."""
        rel_path = self._to_res_path(file_path, project_root)
        content = file_path.read_text(encoding="utf-8")

        dependencies = self._extract_dependencies(content)

        return Module(path=rel_path, class_name=None, dependencies=dependencies)

    def _to_res_path(self, file_path: Path, project_root: Path) -> str:
        """Convert absolute path to res:// path."""
        rel = file_path.resolve().relative_to(project_root.resolve())
        return f"res://{rel.as_posix()}"

    def _extract_dependencies(self, content: str) -> list[Dependency]:
        """Extract script dependencies from TSCN content."""
        dependencies: list[Dependency] = []
        seen_scripts: set[str] = set()

        for line_num, line in enumerate(content.splitlines(), start=1):
            # Find external resource declarations for .gd files
            match = Patterns.TSCN_EXT_RESOURCE.search(line)
            if match:
                script_path = match.group(1)
                if script_path not in seen_scripts:
                    seen_scripts.add(script_path)
                    dependencies.append(
                        Dependency(
                            target=script_path,
                            dep_type=DependencyType.SCENE_SCRIPT,
                            line=line_num,
                        )
                    )

        return dependencies
