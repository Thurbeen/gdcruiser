import json

from ..analyzer import AnalysisResult
from ..rules.models import RuleCheckResult


class JsonFormatter:
    """Formats analysis results as JSON."""

    def __init__(self, indent: int = 2) -> None:
        self._indent = indent

    def format(
        self, result: AnalysisResult, rule_result: RuleCheckResult | None = None
    ) -> str:
        data = result.to_dict()
        if rule_result:
            data["rules"] = rule_result.to_dict()
        return json.dumps(data, indent=self._indent)
