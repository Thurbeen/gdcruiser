"""Configuration models for gdcruiser custom rules."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Rule violation severity levels."""

    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    IGNORE = "ignore"


@dataclass
class PathMatcher:
    """Matches module paths using regex patterns."""

    path: str | None = None
    pathNot: str | None = None


@dataclass
class Rule:
    """A dependency rule definition."""

    name: str
    severity: Severity = Severity.ERROR
    comment: str | None = None
    from_: PathMatcher | None = None
    to: PathMatcher | None = None
    circular: bool = False
    orphan: bool = False

    def __post_init__(self) -> None:
        if self.from_ is None:
            self.from_ = PathMatcher()
        if self.to is None:
            self.to = PathMatcher()


@dataclass
class ConfigOptions:
    """Global configuration options."""

    exclude: list[str] = field(default_factory=list)


@dataclass
class Config:
    """Root configuration for gdcruiser rules."""

    forbidden: list[Rule] = field(default_factory=list)
    allowed: list[Rule] = field(default_factory=list)
    required: list[Rule] = field(default_factory=list)
    options: ConfigOptions = field(default_factory=ConfigOptions)

    def has_rules(self) -> bool:
        """Check if any rules are defined."""
        return bool(self.forbidden or self.allowed or self.required)

    def all_rules(self) -> list[tuple[str, Rule]]:
        """Return all rules with their type."""
        rules: list[tuple[str, Rule]] = []
        for rule in self.forbidden:
            rules.append(("forbidden", rule))
        for rule in self.allowed:
            rules.append(("allowed", rule))
        for rule in self.required:
            rules.append(("required", rule))
        return rules
