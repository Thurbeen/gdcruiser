import argparse
import sys
from pathlib import Path

from .analyzer import Analyzer
from .output.text import TextFormatter
from .output.json import JsonFormatter
from .output.dot import DotFormatter


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gdcruiser",
        description="Dependency analyzer for Godot/GDScript projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gdcruiser .                    Analyze current directory
  gdcruiser /path/to/project     Analyze specific project
  gdcruiser . -f json            Output as JSON
  gdcruiser . -f dot -o deps.dot Output DOT file for GraphViz
  gdcruiser . --no-cycles        Skip cycle detection
""",
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Godot project path (default: current directory)",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json", "dot"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file (default: stdout)",
    )

    parser.add_argument(
        "--no-cycles",
        action="store_true",
        help="Skip cycle detection",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    return parser


def run(args: argparse.Namespace) -> int:
    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"Error: Path does not exist: {project_path}", file=sys.stderr)
        return 1

    if not project_path.is_dir():
        print(f"Error: Path is not a directory: {project_path}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Analyzing: {project_path}")

    analyzer = Analyzer(project_path, verbose=args.verbose)
    result = analyzer.analyze(detect_cycles=not args.no_cycles)

    # Format output
    if args.format == "json":
        formatter = JsonFormatter()
    elif args.format == "dot":
        formatter = DotFormatter()
    else:
        formatter = TextFormatter()

    output = formatter.format(result)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding="utf-8")
        if args.verbose:
            print(f"Output written to: {output_path}")
    else:
        print(output)

    # Return non-zero if cycles found
    if result.cycles and not args.no_cycles:
        return 1

    return 0


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    return run(args)
