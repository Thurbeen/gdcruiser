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

# TSCN: [ext_resource ... path="res://..." ...]
TSCN_EXT_RESOURCE = re.compile(r'path="(res://[^"]+\.gd)"')

# TSCN: script = ExtResource(...)
TSCN_SCRIPT_ATTACH = re.compile(r"^\s*script\s*=\s*ExtResource")


class Patterns:
    """Container for all regex patterns."""

    EXTENDS_PATH = EXTENDS_PATH
    EXTENDS_CLASS = EXTENDS_CLASS
    CLASS_NAME = CLASS_NAME
    PRELOAD = PRELOAD
    LOAD = LOAD
    TSCN_EXT_RESOURCE = TSCN_EXT_RESOURCE
    TSCN_SCRIPT_ATTACH = TSCN_SCRIPT_ATTACH
