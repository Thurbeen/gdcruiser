from pathlib import Path

from ..graph.node import Module, Dependency, DependencyType
from ..symbols.table import SymbolTable
from .patterns import Patterns


class GDScriptParser:
    """Parses GDScript files to extract dependencies."""

    def __init__(self, symbol_table: SymbolTable) -> None:
        self._symbol_table = symbol_table

    def parse(self, file_path: Path, project_root: Path) -> Module:
        """Parse a GDScript file and return a Module."""
        rel_path = self._to_res_path(file_path, project_root)
        content = file_path.read_text(encoding="utf-8")

        class_name = self._extract_class_name(content)
        if class_name:
            self._symbol_table.register(class_name, rel_path)

        dependencies = self._extract_dependencies(content)

        return Module(path=rel_path, class_name=class_name, dependencies=dependencies)

    def resolve_class_dependencies(self, module: Module) -> None:
        """Resolve extends ClassName dependencies using the symbol table."""
        for dep in module.dependencies:
            if dep.dep_type == DependencyType.EXTENDS_CLASS:
                resolved_path = self._symbol_table.resolve(dep.target)
                if resolved_path:
                    dep.target = resolved_path
                    dep.resolved = True
                else:
                    dep.resolved = False

    def _to_res_path(self, file_path: Path, project_root: Path) -> str:
        """Convert absolute path to res:// path."""
        rel = file_path.resolve().relative_to(project_root.resolve())
        return f"res://{rel.as_posix()}"

    def _extract_class_name(self, content: str) -> str | None:
        """Extract class_name declaration from content."""
        for line in content.splitlines():
            match = Patterns.CLASS_NAME.match(line)
            if match:
                return match.group(1)
        return None

    def _extract_dependencies(self, content: str) -> list[Dependency]:
        """Extract all dependencies from content."""
        dependencies: list[Dependency] = []

        for line_num, line in enumerate(content.splitlines(), start=1):
            # Skip comments
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue

            # extends "res://..."
            match = Patterns.EXTENDS_PATH.match(line)
            if match:
                dependencies.append(
                    Dependency(
                        target=match.group(1),
                        dep_type=DependencyType.EXTENDS_PATH,
                        line=line_num,
                    )
                )
                continue

            # extends ClassName
            match = Patterns.EXTENDS_CLASS.match(line)
            if match:
                class_ref = match.group(1)
                # Skip built-in classes (Node, Resource, etc.)
                if not self._is_builtin_class(class_ref):
                    dependencies.append(
                        Dependency(
                            target=class_ref,
                            dep_type=DependencyType.EXTENDS_CLASS,
                            line=line_num,
                            resolved=False,
                        )
                    )
                continue

            # preload("res://...")
            for match in Patterns.PRELOAD.finditer(line):
                dependencies.append(
                    Dependency(
                        target=match.group(1),
                        dep_type=DependencyType.PRELOAD,
                        line=line_num,
                    )
                )

            # load("res://...")
            for match in Patterns.LOAD.finditer(line):
                dependencies.append(
                    Dependency(
                        target=match.group(1),
                        dep_type=DependencyType.LOAD,
                        line=line_num,
                    )
                )

        return dependencies

    def _is_builtin_class(self, name: str) -> bool:
        """Check if a class name is a Godot built-in."""
        builtins = {
            "Node",
            "Node2D",
            "Node3D",
            "Control",
            "Resource",
            "Object",
            "RefCounted",
            "Reference",
            "Spatial",
            "KinematicBody",
            "KinematicBody2D",
            "RigidBody",
            "RigidBody2D",
            "StaticBody",
            "StaticBody2D",
            "Area",
            "Area2D",
            "CharacterBody2D",
            "CharacterBody3D",
            "Sprite",
            "Sprite2D",
            "Sprite3D",
            "AnimatedSprite",
            "AnimatedSprite2D",
            "Camera",
            "Camera2D",
            "Camera3D",
            "Light",
            "Light2D",
            "CanvasItem",
            "CanvasLayer",
            "Viewport",
            "SubViewport",
            "Window",
            "Panel",
            "Button",
            "Label",
            "LineEdit",
            "TextEdit",
            "RichTextLabel",
            "Container",
            "HBoxContainer",
            "VBoxContainer",
            "GridContainer",
            "MarginContainer",
            "CenterContainer",
            "ScrollContainer",
            "TabContainer",
            "PanelContainer",
            "Timer",
            "AudioStreamPlayer",
            "AudioStreamPlayer2D",
            "AudioStreamPlayer3D",
            "AnimationPlayer",
            "AnimationTree",
            "Tween",
            "Path",
            "Path2D",
            "PathFollow",
            "PathFollow2D",
            "PathFollow3D",
            "NavigationAgent2D",
            "NavigationAgent3D",
            "TileMap",
            "TileSet",
            "ParticleEmitter",
            "GPUParticles2D",
            "GPUParticles3D",
            "CPUParticles2D",
            "CPUParticles3D",
            "RayCast",
            "RayCast2D",
            "RayCast3D",
            "ShapeCast2D",
            "ShapeCast3D",
            "CollisionShape",
            "CollisionShape2D",
            "CollisionShape3D",
            "CollisionPolygon2D",
            "CollisionPolygon3D",
            "HTTPRequest",
            "WebSocketClient",
            "WebSocketServer",
            "MultiplayerSpawner",
            "MultiplayerSynchronizer",
            "SceneTree",
            "MainLoop",
            "EditorPlugin",
            "EditorScript",
        }
        return name in builtins
