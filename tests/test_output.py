import json
from pathlib import Path

from gdcruiser.analyzer import Analyzer
from gdcruiser.output.text import TextFormatter
from gdcruiser.output.json import JsonFormatter
from gdcruiser.output.dot import DotFormatter


FIXTURES = Path(__file__).parent / "fixtures"


class TestTextFormatter:
    def test_format_output(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        formatter = TextFormatter()
        output = formatter.format(result)

        assert "GDScript Dependency Analysis" in output
        assert "Modules:" in output
        assert "Dependencies:" in output

    def test_format_shows_cycles(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        formatter = TextFormatter()
        output = formatter.format(result)

        assert "CIRCULAR DEPENDENCIES" in output


class TestJsonFormatter:
    def test_format_valid_json(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        formatter = JsonFormatter()
        output = formatter.format(result)

        # Should be valid JSON
        data = json.loads(output)
        assert "graph" in data
        assert "cycles" in data
        assert "symbols" in data

    def test_format_contains_modules(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        formatter = JsonFormatter()
        output = formatter.format(result)
        data = json.loads(output)

        assert "modules" in data["graph"]
        assert len(data["graph"]["modules"]) > 0


class TestDotFormatter:
    def test_format_valid_dot(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        formatter = DotFormatter()
        output = formatter.format(result)

        assert output.startswith("digraph dependencies {")
        assert output.endswith("}")

    def test_format_contains_nodes_and_edges(self):
        analyzer = Analyzer(FIXTURES)
        result = analyzer.analyze()

        formatter = DotFormatter()
        output = formatter.format(result)

        # Should have node declarations
        assert "[label=" in output
        # Should have edge declarations
        assert "->" in output
