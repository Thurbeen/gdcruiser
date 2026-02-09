import argparse
import sys
from pathlib import Path

from .analyzer import Analyzer
from .config import ConfigError, ConfigLoader, ConfigValidator
from .output.dot import DotFormatter
from .output.json import JsonFormatter
from .output.text import TextFormatter
from .rules import RuleEngine


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
  gdcruiser . --config rules.json Use custom config file
  gdcruiser . --validate-config  Validate config without analyzing
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

    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Path to config file (.gdcruiser.json or pyproject.toml)",
    )

    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate config file and exit",
    )

    parser.add_argument(
        "--ignore-rules",
        action="store_true",
        help="Skip rule evaluation",
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

    # Load configuration
    config_path = Path(args.config) if args.config else None
    loader = ConfigLoader(project_path)

    try:
        config = loader.load(config_path)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Validate config
    if config.has_rules() or args.validate_config:
        validator = ConfigValidator()
        validation = validator.validate(config)

        if args.verbose or args.validate_config:
            if validation.warnings:
                for w in validation.warnings:
                    print(f"Warning: {w.path}: {w.message}", file=sys.stderr)

        if not validation.is_valid():
            for e in validation.errors:
                print(f"Error: {e.path}: {e.message}", file=sys.stderr)
            return 1

        if args.validate_config:
            config_file = config_path or loader.discover()
            if config_file:
                print(f"Config valid: {config_file}")
                print(f"  Forbidden rules: {len(config.forbidden)}")
                print(f"  Allowed rules: {len(config.allowed)}")
                print(f"  Required rules: {len(config.required)}")
            else:
                print("No config file found")
            return 0

    if args.verbose:
        print(f"Analyzing: {project_path}")
        if config.has_rules():
            print(f"Rules loaded: {len(config.all_rules())}")

    analyzer = Analyzer(project_path, verbose=args.verbose)
    result = analyzer.analyze(detect_cycles=not args.no_cycles)

    # Evaluate rules
    rule_result = None
    if config.has_rules() and not args.ignore_rules:
        engine = RuleEngine(config, result.graph)
        rule_result = engine.check_all(cycles=result.cycles)

        if args.verbose:
            print(
                f"Rule violations: {rule_result.error_count()} errors, "
                f"{rule_result.warning_count()} warnings"
            )

    # Format output
    if args.format == "json":
        formatter = JsonFormatter()
        output = formatter.format(result, rule_result)
    elif args.format == "dot":
        formatter = DotFormatter()
        output = formatter.format(result)
    else:
        formatter = TextFormatter()
        output = formatter.format(result, rule_result)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding="utf-8")
        if args.verbose:
            print(f"Output written to: {output_path}")
    else:
        print(output)

    # Return non-zero if rule errors or cycles found
    if rule_result and rule_result.has_errors():
        return 1

    if result.cycles and not args.no_cycles:
        return 1

    return 0


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    return run(args)
