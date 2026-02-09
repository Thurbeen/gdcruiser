from dataclasses import dataclass, field
from pathlib import Path

from .scanner import Scanner
from .parser.gdscript import GDScriptParser
from .parser.tscn import TscnParser
from .graph.dependency import DependencyGraph
from .graph.cycles import CycleDetector
from .symbols.table import SymbolTable


@dataclass
class AnalysisResult:
    """Result of analyzing a Godot project."""

    graph: DependencyGraph
    cycles: list[list[str]] = field(default_factory=list)
    symbol_table: SymbolTable = field(default_factory=SymbolTable)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "graph": self.graph.to_dict(),
            "cycles": self.cycles,
            "symbols": self.symbol_table.all_classes(),
            "errors": self.errors,
        }


class Analyzer:
    """Orchestrates parsing and graph building for a Godot project."""

    def __init__(
        self,
        project_path: Path,
        verbose: bool = False,
        exclude: list[str] | None = None,
    ) -> None:
        self._scanner = Scanner(project_path, exclude=exclude)
        self._symbol_table = SymbolTable()
        self._gd_parser = GDScriptParser(self._symbol_table)
        self._tscn_parser = TscnParser()
        self._graph = DependencyGraph()
        self._verbose = verbose
        self._errors: list[str] = []

    def analyze(self, detect_cycles: bool = True) -> AnalysisResult:
        """Analyze the project and return results."""
        gd_files, tscn_files = self._scanner.find_all_files()
        root = self._scanner.root

        if self._verbose:
            print(f"Found {len(gd_files)} GDScript files")
            print(f"Found {len(tscn_files)} scene files")

        # First pass: parse all GDScript files to build symbol table
        modules = []
        for gd_file in gd_files:
            try:
                module = self._gd_parser.parse(gd_file, root)
                modules.append(module)
                self._graph.add_module(module)
            except Exception as e:
                self._errors.append(f"Error parsing {gd_file}: {e}")

        # Second pass: resolve class name dependencies
        for module in modules:
            self._gd_parser.resolve_class_dependencies(module)

        # Parse scene files
        for tscn_file in tscn_files:
            try:
                module = self._tscn_parser.parse(tscn_file, root)
                self._graph.add_module(module)
            except Exception as e:
                self._errors.append(f"Error parsing {tscn_file}: {e}")

        # Detect cycles
        cycles: list[list[str]] = []
        if detect_cycles:
            detector = CycleDetector(self._graph)
            cycles = detector.find_cycles()
            if self._verbose:
                print(f"Found {len(cycles)} cycles")

        return AnalysisResult(
            graph=self._graph,
            cycles=cycles,
            symbol_table=self._symbol_table,
            errors=self._errors,
        )
