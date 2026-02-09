from dataclasses import dataclass, field
from enum import Enum


class DependencyType(Enum):
    """Types of dependencies in GDScript."""

    EXTENDS_PATH = "extends_path"
    EXTENDS_CLASS = "extends_class"
    PRELOAD = "preload"
    LOAD = "load"
    SCENE_SCRIPT = "scene_script"


@dataclass
class Dependency:
    """Represents a dependency from one module to another."""

    target: str
    dep_type: DependencyType
    line: int | None = None
    resolved: bool = True

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "type": self.dep_type.value,
            "line": self.line,
            "resolved": self.resolved,
        }


@dataclass
class Module:
    """Represents a GDScript or scene file."""

    path: str
    class_name: str | None = None
    dependencies: list[Dependency] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "class_name": self.class_name,
            "dependencies": [d.to_dict() for d in self.dependencies],
        }
