from dataclasses import dataclass, field
from pathlib import Path

from .cache import ParseCache
from .scanner import Scanner
from .parser.gdscript import GDScriptParser
from .parser.tscn import TscnParser
from .parser.tres import TresParser
from .parser.project_godot import parse_autoloads
from .graph.dependency import DependencyGraph
from .graph.cycles import CycleDetector
from .graph.node import Module
from .symbols.table import SymbolTable


@dataclass
class AnalysisResult:
    """Result of analyzing a Godot project."""

    graph: DependencyGraph
    cycles: list[list[str]] = field(default_factory=list)
    symbol_table: SymbolTable = field(default_factory=SymbolTable)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "graph": self.graph.to_dict(),
            "cycles": self.cycles,
            "symbols": self.symbol_table.all_classes(),
            "errors": self.errors,
            "warnings": self.warnings,
        }


class Analyzer:
    """Orchestrates parsing and graph building for a Godot project."""

    def __init__(
        self,
        project_path: Path,
        verbose: bool = False,
        exclude: list[str] | None = None,
        cache: ParseCache | None = None,
    ) -> None:
        self._scanner = Scanner(project_path, exclude=exclude)
        self._symbol_table = SymbolTable()
        self._gd_parser = GDScriptParser(self._symbol_table)
        self._tscn_parser = TscnParser()
        self._tres_parser = TresParser(self._symbol_table)
        self._graph = DependencyGraph()
        self._verbose = verbose
        self._cache = cache
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def analyze(self, detect_cycles: bool = True) -> AnalysisResult:
        """Analyze the project and return results."""
        gd_files, tscn_files, tres_files = self._scanner.find_all_files()
        root = self._scanner.root

        # Register project.godot [autoload] singletons before any class-ref
        # resolution runs — `TurnManager.foo` then resolves the same way as
        # any other class_name reference. A malformed/unreadable project.godot
        # must not abort the whole analysis.
        try:
            autoloads = parse_autoloads(root)
        except Exception as e:
            autoloads = {}
            self._errors.append(f"Error parsing project.godot: {e}")
        for identifier, path in autoloads.items():
            self._symbol_table.register(identifier, path)

        if self._verbose:
            print(f"Found {len(gd_files)} GDScript files")
            print(f"Found {len(tscn_files)} scene files")
            print(f"Found {len(tres_files)} resource files")
            if autoloads:
                print(f"Registered {len(autoloads)} autoload singletons")

        # First pass: parse all GDScript files to build symbol table
        modules = []
        for gd_file in gd_files:
            module = self._parse_file(gd_file, self._gd_parser, root)
            if module is not None:
                modules.append(module)
                self._graph.add_module(module)

        # Second pass: resolve class name dependencies
        for module in modules:
            self._gd_parser.resolve_class_dependencies(module)

        # Parse scene files
        for tscn_file in tscn_files:
            module = self._parse_file(tscn_file, self._tscn_parser, root)
            if module is not None:
                self._graph.add_module(module)

        # Parse resource (.tres) files
        for tres_file in tres_files:
            module = self._parse_file(tres_file, self._tres_parser, root)
            if module is not None:
                self._graph.add_module(module)

        if self._cache is not None:
            self._cache.save()
            if self._verbose:
                print(
                    f"Parse cache: {self._cache.hits} hits, {self._cache.misses} misses"
                )

        # Detect cycles
        cycles: list[list[str]] = []
        if detect_cycles:
            detector = CycleDetector(self._graph)
            cycles = detector.find_cycles()
            if self._verbose:
                print(f"Found {len(cycles)} cycles")

        # Surface duplicate class_name / autoload registrations as warnings.
        for name, existing, new in self._symbol_table.collisions():
            self._warnings.append(
                f"Duplicate symbol '{name}': registered by both "
                f"{existing} and {new} (using {new})"
            )

        return AnalysisResult(
            graph=self._graph,
            cycles=cycles,
            symbol_table=self._symbol_table,
            errors=self._errors,
            warnings=self._warnings,
        )

    def _parse_file(self, file_path: Path, parser, root: Path) -> Module | None:
        """Parse a file, restoring it from the cache when unchanged.

        Cached modules are returned verbatim, but their declared class_name is
        re-registered in the symbol table so cross-file resolution still works
        without re-parsing the file body.
        """
        try:
            if self._cache is not None:
                key = self._cache.stat_key(file_path)
                cached = self._cache.get(file_path, key)
                if cached is not None:
                    if cached.class_name:
                        self._symbol_table.register(cached.class_name, cached.path)
                    return cached
                module = parser.parse(file_path, root)
                self._cache.put(file_path, key, module)
                return module
            return parser.parse(file_path, root)
        except Exception as e:
            self._errors.append(f"Error parsing {file_path}: {e}")
            return None
