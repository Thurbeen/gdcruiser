from pathlib import Path

from gdcruiser.cli import create_parser, run


FIXTURES = Path(__file__).parent / "fixtures"


class TestCLIParser:
    def test_default_values(self):
        parser = create_parser()
        args = parser.parse_args([])

        assert args.path == "."
        assert args.format == "text"
        assert args.output is None
        assert args.no_cycles is False
        assert args.verbose is False

    def test_path_argument(self):
        parser = create_parser()
        args = parser.parse_args(["/path/to/project"])

        assert args.path == "/path/to/project"

    def test_format_option(self):
        parser = create_parser()

        args = parser.parse_args(["-f", "json"])
        assert args.format == "json"

        args = parser.parse_args(["--format", "dot"])
        assert args.format == "dot"

    def test_output_option(self):
        parser = create_parser()
        args = parser.parse_args(["-o", "output.txt"])

        assert args.output == "output.txt"

    def test_no_cycles_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--no-cycles"])

        assert args.no_cycles is True

    def test_verbose_flag(self):
        parser = create_parser()
        args = parser.parse_args(["-v"])

        assert args.verbose is True

    def test_exclude_default_is_none(self):
        parser = create_parser()
        args = parser.parse_args([])

        assert args.exclude is None

    def test_exclude_single_pattern(self):
        parser = create_parser()
        args = parser.parse_args(["--exclude", "addons"])

        assert args.exclude == ["addons"]

    def test_exclude_multiple_patterns(self):
        parser = create_parser()
        args = parser.parse_args(["--exclude", "addons", "--exclude", "tests"])

        assert args.exclude == ["addons", "tests"]


class TestCLIRun:
    def test_run_text_output(self, capsys):
        parser = create_parser()
        args = parser.parse_args([str(FIXTURES)])

        # Will return 1 due to cycles
        run(args)

        captured = capsys.readouterr()
        assert "GDScript Dependency Analysis" in captured.out

    def test_run_json_output(self, capsys):
        parser = create_parser()
        args = parser.parse_args([str(FIXTURES), "-f", "json"])

        run(args)

        captured = capsys.readouterr()
        assert '"graph"' in captured.out
        assert '"modules"' in captured.out

    def test_run_nonexistent_path(self, capsys):
        parser = create_parser()
        args = parser.parse_args(["/nonexistent/path"])

        result = run(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_run_returns_1_on_cycles(self):
        parser = create_parser()
        args = parser.parse_args([str(FIXTURES)])

        result = run(args)

        # Should return 1 because cycles exist
        assert result == 1

    def test_run_returns_0_with_no_cycles_flag(self):
        parser = create_parser()
        args = parser.parse_args([str(FIXTURES), "--no-cycles"])

        result = run(args)

        assert result == 0
