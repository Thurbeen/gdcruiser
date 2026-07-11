from pathlib import Path

from ..graph.node import Module, Dependency, DependencyType
from ..symbols.table import SymbolTable
from . import patterns
from .paths import to_res_path


class TresParser:
    """Parses Godot resource (.tres) files to extract dependencies.

    A `.tres` file declares a resource — typically a subclass of
    `Resource` defined by a `.gd` script. The parser extracts:

      - `script_class="ClassName"` from the `[gd_resource]` header to
        name the module after its declared class.
      - Every `path="res://..."` reference (other scripts, sub-resources,
        scene packs) as an outgoing dependency.
    """

    def __init__(self, symbol_table: SymbolTable | None = None) -> None:
        self._symbol_table = symbol_table

    def parse(self, file_path: Path, project_root: Path) -> Module:
        """Parse a .tres file and return a Module."""
        rel_path = to_res_path(file_path, project_root)
        content = file_path.read_text(encoding="utf-8")

        class_name = self._extract_script_class(content)
        dependencies = self._extract_dependencies(content)

        if class_name and self._symbol_table is not None:
            self._symbol_table.register(class_name, rel_path)

        return Module(path=rel_path, class_name=class_name, dependencies=dependencies)

    def _extract_script_class(self, content: str) -> str | None:
        match = patterns.RESOURCE_SCRIPT_CLASS.search(content)
        return match.group(1) if match else None

    def _extract_dependencies(self, content: str) -> list[Dependency]:
        dependencies: list[Dependency] = []
        seen: set[str] = set()

        for line_num, line in enumerate(content.splitlines(), start=1):
            for match in patterns.RESOURCE_PATH.finditer(line):
                target = match.group(1)
                if target in seen:
                    continue
                seen.add(target)
                dependencies.append(
                    Dependency(
                        target=target,
                        dep_type=self._classify(target),
                        line=line_num,
                    )
                )

        return dependencies

    @staticmethod
    def _classify(target: str) -> DependencyType:
        """Classify a resource reference by its target extension."""
        if target.endswith(".gd"):
            return DependencyType.SCENE_SCRIPT
        return DependencyType.RESOURCE_REF
