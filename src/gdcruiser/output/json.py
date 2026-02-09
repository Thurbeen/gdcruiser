import json

from ..analyzer import AnalysisResult


class JsonFormatter:
    """Formats analysis results as JSON."""

    def __init__(self, indent: int = 2) -> None:
        self._indent = indent

    def format(self, result: AnalysisResult) -> str:
        return json.dumps(result.to_dict(), indent=self._indent)
