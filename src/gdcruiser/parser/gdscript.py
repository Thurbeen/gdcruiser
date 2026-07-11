import re
from pathlib import Path

from ..graph.node import Module, Dependency, DependencyType
from ..symbols.table import SymbolTable
from . import patterns
from .paths import to_res_path


class GDScriptParser:
    """Parses GDScript files to extract dependencies."""

    def __init__(self, symbol_table: SymbolTable) -> None:
        self._symbol_table = symbol_table

    def parse(self, file_path: Path, project_root: Path) -> Module:
        """Parse a GDScript file and return a Module."""
        rel_path = to_res_path(file_path, project_root)
        content = file_path.read_text(encoding="utf-8")

        # Blank out comments and triple-quoted strings up front so that
        # `preload`/`load`/`extends`/`ClassName` text living inside them is
        # never mistaken for real code. Single-line string literals are kept
        # because preload/load/extends paths live inside them.
        code = self._preprocess(content)

        class_name = self._extract_class_name(code)
        if class_name:
            self._symbol_table.register(class_name, rel_path)

        dependencies = self._extract_dependencies(code)

        return Module(path=rel_path, class_name=class_name, dependencies=dependencies)

    @staticmethod
    def _preprocess(content: str) -> str:
        """Return a "code view" of the source for pattern matching.

        Comments (``# ...``) and triple-quoted strings are replaced with
        spaces, preserving newlines so line numbers stay accurate. Single-line
        string literals are left intact because ``preload("res://...")`` and
        ``extends "res://..."`` keep their target inside a quoted string.
        """
        out: list[str] = []
        i = 0
        n = len(content)
        state = "code"  # code | comment | line_str | triple_str
        quote = ""
        while i < n:
            ch = content[i]
            if state == "code":
                if ch == "#":
                    state = "comment"
                    out.append(" ")
                    i += 1
                elif content.startswith('"""', i) or content.startswith("'''", i):
                    quote = content[i : i + 3]
                    state = "triple_str"
                    out.append("   ")
                    i += 3
                elif ch in ('"', "'"):
                    quote = ch
                    state = "line_str"
                    out.append(ch)
                    i += 1
                else:
                    out.append(ch)
                    i += 1
            elif state == "comment":
                if ch == "\n":
                    state = "code"
                    out.append("\n")
                else:
                    out.append(" ")
                i += 1
            elif state == "line_str":
                if ch == "\\" and i + 1 < n:
                    out.append(content[i : i + 2])
                    i += 2
                elif ch == quote:
                    out.append(ch)
                    state = "code"
                    i += 1
                elif ch == "\n":
                    # Unterminated single-line string — bail back to code.
                    out.append("\n")
                    state = "code"
                    i += 1
                else:
                    out.append(ch)
                    i += 1
            else:  # triple_str
                if content.startswith(quote, i):
                    out.append("   ")
                    state = "code"
                    i += 3
                elif ch == "\n":
                    out.append("\n")
                    i += 1
                else:
                    out.append(" ")
                    i += 1
        return "".join(out)

    def resolve_class_dependencies(self, module: Module) -> None:
        """Resolve class-name dependencies using the symbol table.

        EXTENDS_CLASS deps are kept even when unresolved (they signal a
        broken or missing inheritance target). CLASS_REF deps are dropped
        when they don't resolve, since loose pattern matching produces
        many false positives (built-ins, local enums, unrelated
        identifiers) that would otherwise pollute the graph.
        """
        kept: list[Dependency] = []
        for dep in module.dependencies:
            if dep.dep_type == DependencyType.EXTENDS_CLASS:
                resolved_path = self._symbol_table.resolve(dep.target)
                if resolved_path:
                    dep.target = resolved_path
                    dep.resolved = True
                else:
                    dep.resolved = False
                kept.append(dep)
            elif dep.dep_type == DependencyType.CLASS_REF:
                resolved_path = self._symbol_table.resolve(dep.target)
                if resolved_path and resolved_path != module.path:
                    dep.target = resolved_path
                    dep.resolved = True
                    kept.append(dep)
                # else: drop unresolved or self-references
            else:
                kept.append(dep)
        module.dependencies = kept

    def _extract_class_name(self, content: str) -> str | None:
        """Extract class_name declaration from content."""
        for line in content.splitlines():
            match = patterns.CLASS_NAME.match(line)
            if match:
                return match.group(1)
        return None

    def _extract_dependencies(self, content: str) -> list[Dependency]:
        """Extract all dependencies from content (already comment/string-stripped)."""
        dependencies: list[Dependency] = []
        seen_class_refs: set[str] = set()

        for line_num, line in enumerate(content.splitlines(), start=1):
            # extends "res://..."
            match = patterns.EXTENDS_PATH.match(line)
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
            match = patterns.EXTENDS_CLASS.match(line)
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

            # class_name declaration — never a dependency.
            if patterns.CLASS_NAME.match(line):
                continue

            # preload("res://...")
            for match in patterns.PRELOAD.finditer(line):
                dependencies.append(
                    Dependency(
                        target=match.group(1),
                        dep_type=DependencyType.PRELOAD,
                        line=line_num,
                    )
                )

            # load("res://...")
            for match in patterns.LOAD.finditer(line):
                dependencies.append(
                    Dependency(
                        target=match.group(1),
                        dep_type=DependencyType.LOAD,
                        line=line_num,
                    )
                )

            # Class references in expressions (typed annotations, is/as,
            # static access). String literals and inline comments are
            # stripped first so identifiers inside them aren't matched.
            sanitized = self._sanitize_for_class_refs(line)
            for class_ref in self._find_class_refs(sanitized):
                if self._is_builtin_class(class_ref):
                    continue
                if class_ref in seen_class_refs:
                    continue
                seen_class_refs.add(class_ref)
                dependencies.append(
                    Dependency(
                        target=class_ref,
                        dep_type=DependencyType.CLASS_REF,
                        line=line_num,
                        resolved=False,
                    )
                )

        return dependencies

    @staticmethod
    def _sanitize_for_class_refs(line: str) -> str:
        """Remove string literals and inline comments from a line."""
        # Strip "..." and '...' string literals (no escaped-quote handling
        # — good enough for catching identifier patterns).
        sanitized = re.sub(r'"[^"]*"', '""', line)
        sanitized = re.sub(r"'[^']*'", "''", sanitized)
        hash_pos = sanitized.find("#")
        if hash_pos != -1:
            sanitized = sanitized[:hash_pos]
        return sanitized

    @staticmethod
    def _find_class_refs(line: str) -> list[str]:
        """Extract class-name references from a sanitized line."""
        refs: list[str] = []
        for pattern in (
            patterns.TYPED_REF,
            patterns.RETURN_TYPE,
            patterns.IS_AS_REF,
            patterns.MEMBER_ACCESS,
            patterns.GENERIC_PARAM,
        ):
            for match in pattern.finditer(line):
                refs.append(match.group(1))
        return refs

    def _is_builtin_class(self, name: str) -> bool:
        """Check if a class name is a Godot built-in."""
        return name in _BUILTIN_CLASSES


_BUILTIN_CLASSES: frozenset[str] = frozenset(
    {
        # Variant value types
        "bool",
        "int",
        "float",
        "String",
        "StringName",
        "NodePath",
        "Variant",
        "Vector2",
        "Vector2i",
        "Vector3",
        "Vector3i",
        "Vector4",
        "Vector4i",
        "Rect2",
        "Rect2i",
        "Color",
        "Transform2D",
        "Transform3D",
        "Basis",
        "Quaternion",
        "Plane",
        "AABB",
        "Projection",
        "RID",
        "Callable",
        "Signal",
        "Array",
        "Dictionary",
        "PackedByteArray",
        "PackedInt32Array",
        "PackedInt64Array",
        "PackedFloat32Array",
        "PackedFloat64Array",
        "PackedStringArray",
        "PackedVector2Array",
        "PackedVector3Array",
        "PackedVector4Array",
        "PackedColorArray",
        # Core/object types
        "Object",
        "RefCounted",
        "Reference",
        "Resource",
        "WeakRef",
        "Engine",
        "OS",
        "Time",
        "Input",
        "InputEvent",
        "InputEventKey",
        "InputEventMouse",
        "InputEventMouseButton",
        "InputEventMouseMotion",
        "InputEventJoypadButton",
        "InputEventJoypadMotion",
        "InputEventAction",
        "InputMap",
        "JSON",
        "Marshalls",
        "FileAccess",
        "DirAccess",
        "ProjectSettings",
        "ResourceLoader",
        "ResourceSaver",
        "ClassDB",
        "Performance",
        "Geometry2D",
        "Geometry3D",
        "PhysicsServer2D",
        "PhysicsServer3D",
        "RenderingServer",
        "AudioServer",
        "DisplayServer",
        "TranslationServer",
        "ThemeDB",
        "EditorInterface",
        "Error",
        "Mutex",
        "Semaphore",
        "Thread",
        "Curve",
        "Curve2D",
        "Curve3D",
        "Gradient",
        "Image",
        "ImageTexture",
        "Texture",
        "Texture2D",
        "Texture3D",
        "TextureLayered",
        "AtlasTexture",
        "CanvasTexture",
        "ViewportTexture",
        "Mesh",
        "ArrayMesh",
        "ImmediateMesh",
        "PrimitiveMesh",
        "Material",
        "ShaderMaterial",
        "StandardMaterial3D",
        "CanvasItemMaterial",
        "ParticleProcessMaterial",
        "Shader",
        "ShaderInclude",
        "Animation",
        "AnimationLibrary",
        "AnimationNode",
        "AnimationNodeStateMachine",
        "AnimationRootNode",
        "PackedScene",
        "SceneState",
        "Tween",
        "Theme",
        "StyleBox",
        "StyleBoxFlat",
        "StyleBoxTexture",
        "Font",
        "FontFile",
        "FontVariation",
        "AudioStream",
        "AudioStreamPlayback",
        "PhysicsMaterial",
        # Scene tree / nodes
        "Node",
        "Node2D",
        "Node3D",
        "Control",
        "Spatial",
        "KinematicBody",
        "KinematicBody2D",
        "RigidBody",
        "RigidBody2D",
        "RigidBody3D",
        "StaticBody",
        "StaticBody2D",
        "StaticBody3D",
        "Area",
        "Area2D",
        "Area3D",
        "CharacterBody2D",
        "CharacterBody3D",
        "Sprite",
        "Sprite2D",
        "Sprite3D",
        "AnimatedSprite",
        "AnimatedSprite2D",
        "AnimatedSprite3D",
        "Camera",
        "Camera2D",
        "Camera3D",
        "Light",
        "Light2D",
        "Light3D",
        "DirectionalLight2D",
        "DirectionalLight3D",
        "OmniLight2D",
        "OmniLight3D",
        "SpotLight2D",
        "SpotLight3D",
        "CanvasItem",
        "CanvasLayer",
        "CanvasGroup",
        "BackBufferCopy",
        "Viewport",
        "SubViewport",
        "SubViewportContainer",
        "Window",
        "Panel",
        "Button",
        "TextureButton",
        "MenuButton",
        "OptionButton",
        "CheckBox",
        "CheckButton",
        "ColorPickerButton",
        "Label",
        "Label3D",
        "LineEdit",
        "TextEdit",
        "RichTextLabel",
        "Container",
        "HBoxContainer",
        "VBoxContainer",
        "GridContainer",
        "FlowContainer",
        "HFlowContainer",
        "VFlowContainer",
        "MarginContainer",
        "CenterContainer",
        "ScrollContainer",
        "TabContainer",
        "TabBar",
        "PanelContainer",
        "SplitContainer",
        "HSplitContainer",
        "VSplitContainer",
        "AspectRatioContainer",
        "BoxContainer",
        "Range",
        "ProgressBar",
        "Slider",
        "HSlider",
        "VSlider",
        "ScrollBar",
        "HScrollBar",
        "VScrollBar",
        "ItemList",
        "Tree",
        "TreeItem",
        "PopupMenu",
        "Popup",
        "AcceptDialog",
        "ConfirmationDialog",
        "FileDialog",
        "ColorPicker",
        "ColorRect",
        "TextureRect",
        "VideoStreamPlayer",
        "Timer",
        "AudioStreamPlayer",
        "AudioStreamPlayer2D",
        "AudioStreamPlayer3D",
        "AudioListener2D",
        "AudioListener3D",
        "AnimationPlayer",
        "AnimationTree",
        "Path",
        "Path2D",
        "Path3D",
        "PathFollow",
        "PathFollow2D",
        "PathFollow3D",
        "NavigationAgent2D",
        "NavigationAgent3D",
        "NavigationRegion2D",
        "NavigationRegion3D",
        "NavigationLink2D",
        "NavigationLink3D",
        "TileMap",
        "TileMapLayer",
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
        "CollisionObject2D",
        "CollisionObject3D",
        "Joint2D",
        "Joint3D",
        "PinJoint2D",
        "HingeJoint3D",
        "PinJoint3D",
        "Marker2D",
        "Marker3D",
        "MeshInstance",
        "MeshInstance2D",
        "MeshInstance3D",
        "MultiMeshInstance2D",
        "MultiMeshInstance3D",
        "Skeleton2D",
        "Skeleton3D",
        "Bone2D",
        "BoneAttachment3D",
        "GraphEdit",
        "GraphNode",
        "GraphElement",
        "HTTPRequest",
        "WebSocketClient",
        "WebSocketServer",
        "WebSocketPeer",
        "MultiplayerSpawner",
        "MultiplayerSynchronizer",
        "MultiplayerAPI",
        "ENetMultiplayerPeer",
        "WebRTCMultiplayerPeer",
        "SceneTree",
        "SceneTreeTimer",
        "MainLoop",
        "EditorPlugin",
        "EditorScript",
        "EditorInspectorPlugin",
        "EditorImportPlugin",
        "EditorExportPlugin",
        "EditorFileSystem",
        # Abstract physics/visual bases and other commonly-extended node
        # types that are easy to omit above (an `extends` of any of these is
        # a built-in, not a broken project dependency).
        "PhysicsBody2D",
        "PhysicsBody3D",
        "CollisionObject2D",
        "GeometryInstance3D",
        "VisualInstance3D",
        "VisibleOnScreenNotifier2D",
        "VisibleOnScreenNotifier3D",
        "VisibleOnScreenEnabler2D",
        "VisibleOnScreenEnabler3D",
        "Parallax2D",
        "ParallaxBackground",
        "ParallaxLayer",
        "RemoteTransform2D",
        "RemoteTransform3D",
        "Line2D",
        "Polygon2D",
        "PointLight2D",
        "CanvasModulate",
        "GridMap",
        "WorldEnvironment",
        "SpringArm3D",
        "PhysicalBone3D",
        "SoftBody3D",
        "VehicleBody3D",
        "CSGShape3D",
        "CSGBox3D",
        "CSGCombiner3D",
        "ReflectionProbe",
        "VoxelGI",
        "LightmapGI",
        "OccluderInstance3D",
        "FogVolume",
        "Decal",
    }
)
