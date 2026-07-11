from .text import TextFormatter
from .json import JsonFormatter
from .dot import DotFormatter
from .mermaid import MermaidFormatter

# Registry keyed by the CLI `--format` value. Every formatter exposes the same
# ``format(result, rule_result=None)`` signature so the CLI can dispatch by name.
FORMATTERS = {
    "text": TextFormatter,
    "json": JsonFormatter,
    "dot": DotFormatter,
    "mermaid": MermaidFormatter,
}

__all__ = [
    "TextFormatter",
    "JsonFormatter",
    "DotFormatter",
    "MermaidFormatter",
    "FORMATTERS",
]
