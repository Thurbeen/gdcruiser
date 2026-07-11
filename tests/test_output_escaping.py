"""Tests that DOT/Mermaid labels escape adversarial characters."""

from gdcruiser.analyzer import AnalysisResult
from gdcruiser.graph.dependency import DependencyGraph
from gdcruiser.graph.node import Module
from gdcruiser.output.dot import DotFormatter
from gdcruiser.output.mermaid import MermaidFormatter
from gdcruiser.output.labels import escape_dot_label, escape_mermaid_label


def test_escape_dot_label():
    assert escape_dot_label('a"b') == 'a\\"b'
    assert escape_dot_label("a\\b") == "a\\\\b"


def test_escape_mermaid_label():
    assert escape_mermaid_label('a"b') == "a&quot;b"


def _result_with_quote():
    g = DependencyGraph()
    g.add_module(Module(path='res://a"b.gd', class_name='Wei"rd'))
    return AnalysisResult(graph=g)


def test_dot_label_has_no_bare_quote():
    out = DotFormatter().format(_result_with_quote())
    label_line = next(line for line in out.splitlines() if "label=" in line)
    # The class name's inner quote must be backslash-escaped.
    assert '\\"' in label_line


def test_mermaid_label_encodes_quote():
    out = MermaidFormatter().format(_result_with_quote())
    assert "&quot;" in out
    assert 'Wei"rd' not in out
