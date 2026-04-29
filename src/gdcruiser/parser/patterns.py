import re

# Match: extends "res://path/to/script.gd"
EXTENDS_PATH = re.compile(r'^\s*extends\s+"(res://[^"]+)"')

# Match: extends ClassName
EXTENDS_CLASS = re.compile(r"^\s*extends\s+([A-Z][A-Za-z0-9_]*)\s*(?:#.*)?$")

# Match: class_name ClassName
CLASS_NAME = re.compile(r"^\s*class_name\s+([A-Z][A-Za-z0-9_]*)")

# Match: preload("res://path/to/file.gd")
PRELOAD = re.compile(r'preload\s*\(\s*"(res://[^"]+)"\s*\)')

# Match: load("res://path/to/file.gd")
LOAD = re.compile(r'(?<!pre)load\s*\(\s*"(res://[^"]+)"\s*\)')

# Match typed annotations: `: ClassName` (var/param/const types)
TYPED_REF = re.compile(r":\s*([A-Z][A-Za-z0-9_]*)\b")

# Match return-type annotation: `-> ClassName`
RETURN_TYPE = re.compile(r"->\s*([A-Z][A-Za-z0-9_]*)\b")

# Match `is ClassName` and `as ClassName`
IS_AS_REF = re.compile(r"\b(?:is|as)\s+([A-Z][A-Za-z0-9_]*)\b")

# Match static call / constant access: `ClassName.member`
# Negative lookbehind avoids matching `obj.Foo.bar` (Foo is a property, not a class).
MEMBER_ACCESS = re.compile(r"(?<![A-Za-z0-9_.])([A-Z][A-Za-z0-9_]*)\s*\.")

# Match typed-collection params: `Array[Foo]`, `Dictionary[String, Foo]`
GENERIC_PARAM = re.compile(r"[\[,]\s*([A-Z][A-Za-z0-9_]*)\b")

# TSCN: [ext_resource ... path="res://..." ...] — script attachments only
TSCN_EXT_RESOURCE = re.compile(r'path="(res://[^"]+\.gd)"')

# TSCN: script = ExtResource(...)
TSCN_SCRIPT_ATTACH = re.compile(r"^\s*script\s*=\s*ExtResource")

# Resource files (.tres / .tscn): any path="res://..." reference
RESOURCE_PATH = re.compile(r'path="(res://[^"]+)"')

# Resource header: [gd_resource ... script_class="ClassName" ...]
RESOURCE_SCRIPT_CLASS = re.compile(r'script_class="([A-Z][A-Za-z0-9_]*)"')


class Patterns:
    """Container for all regex patterns."""

    EXTENDS_PATH = EXTENDS_PATH
    EXTENDS_CLASS = EXTENDS_CLASS
    CLASS_NAME = CLASS_NAME
    PRELOAD = PRELOAD
    LOAD = LOAD
    TYPED_REF = TYPED_REF
    RETURN_TYPE = RETURN_TYPE
    IS_AS_REF = IS_AS_REF
    MEMBER_ACCESS = MEMBER_ACCESS
    GENERIC_PARAM = GENERIC_PARAM
    TSCN_EXT_RESOURCE = TSCN_EXT_RESOURCE
    TSCN_SCRIPT_ATTACH = TSCN_SCRIPT_ATTACH
    RESOURCE_PATH = RESOURCE_PATH
    RESOURCE_SCRIPT_CLASS = RESOURCE_SCRIPT_CLASS
