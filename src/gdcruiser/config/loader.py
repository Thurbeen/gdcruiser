"""Configuration file discovery and loading."""

import json
from pathlib import Path

from .models import Config, ConfigOptions, PathMatcher, Rule, Severity


class ConfigError(Exception):
    """Configuration loading or parsing error."""

    pass


class ConfigLoader:
    """Discovers and loads gdcruiser configuration files."""

    CONFIG_FILENAMES = [".gdcruiser.json", "gdcruiser.json"]

    def __init__(self, project_path: Path) -> None:
        self._project_path = project_path

    def discover(self) -> Path | None:
        """Find a config file in the project directory."""
        for filename in self.CONFIG_FILENAMES:
            config_path = self._project_path / filename
            if config_path.exists():
                return config_path

        # Check for pyproject.toml with tool.gdcruiser section
        pyproject_path = self._project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                if "[tool.gdcruiser]" in content or "[[tool.gdcruiser." in content:
                    return pyproject_path
            except (OSError, UnicodeDecodeError):
                pass

        return None

    def load(self, config_path: Path | None = None) -> Config:
        """Load configuration from the specified or discovered path."""
        if config_path is None:
            config_path = self.discover()

        if config_path is None:
            return Config()

        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")

        if config_path.suffix == ".json":
            return self._load_json(config_path)
        elif config_path.name == "pyproject.toml":
            return self._load_pyproject(config_path)
        else:
            raise ConfigError(f"Unsupported config file format: {config_path}")

    def _load_json(self, path: Path) -> Config:
        """Load configuration from JSON file."""
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in {path}: {e}")
        except Exception as e:
            raise ConfigError(f"Error reading {path}: {e}")

        return self._parse_config(data)

    def _load_pyproject(self, path: Path) -> Config:
        """Load configuration from pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            raise ConfigError(
                "tomllib not available. Python 3.11+ required for TOML support."
            )

        try:
            content = path.read_text(encoding="utf-8")
            data = tomllib.loads(content)
        except Exception as e:
            raise ConfigError(f"Error reading {path}: {e}")

        tool_config = data.get("tool", {}).get("gdcruiser", {})
        if not tool_config:
            return Config()

        return self._parse_config(tool_config)

    _TOP_LEVEL_KEYS = frozenset({"forbidden", "allowed", "required", "options"})
    _RULE_KEYS = frozenset(
        {"name", "severity", "comment", "from", "to", "circular", "orphan"}
    )
    _MATCHER_KEYS = frozenset({"path", "pathNot"})
    _OPTION_KEYS = frozenset({"exclude"})

    def _parse_config(self, data: dict) -> Config:
        """Parse configuration dictionary into Config object."""
        warnings: list[str] = []
        self._warn_unknown_keys(data, self._TOP_LEVEL_KEYS, "config", warnings)

        forbidden = [
            self._parse_rule(r, f"forbidden[{i}]", warnings)
            for i, r in enumerate(data.get("forbidden", []))
        ]
        allowed = [
            self._parse_rule(r, f"allowed[{i}]", warnings)
            for i, r in enumerate(data.get("allowed", []))
        ]
        required = [
            self._parse_rule(r, f"required[{i}]", warnings)
            for i, r in enumerate(data.get("required", []))
        ]
        options = self._parse_options(data.get("options", {}), warnings)

        return Config(
            forbidden=forbidden,
            allowed=allowed,
            required=required,
            options=options,
            warnings=warnings,
        )

    def _warn_unknown_keys(
        self, data: dict, known: frozenset[str], path: str, warnings: list[str]
    ) -> None:
        """Record a warning for each key in ``data`` not in ``known``."""
        for key in data:
            if key not in known:
                warnings.append(f"{path}: unknown key '{key}' (ignored)")

    def _parse_rule(self, data: dict, path: str, warnings: list[str]) -> Rule:
        """Parse a rule dictionary into a Rule object."""
        self._warn_unknown_keys(data, self._RULE_KEYS, path, warnings)
        name = data.get("name", "unnamed")

        severity_str = str(data.get("severity", "error")).lower()
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.ERROR
            valid = ", ".join(s.value for s in Severity)
            warnings.append(
                f"{path}.severity: unknown value '{severity_str}', "
                f"defaulting to 'error' (valid: {valid})"
            )

        from_data = data.get("from", {})
        to_data = data.get("to", {})
        self._warn_unknown_keys(from_data, self._MATCHER_KEYS, f"{path}.from", warnings)
        self._warn_unknown_keys(to_data, self._MATCHER_KEYS, f"{path}.to", warnings)

        return Rule(
            name=name,
            severity=severity,
            comment=data.get("comment"),
            from_=PathMatcher(
                path=from_data.get("path"),
                pathNot=from_data.get("pathNot"),
            ),
            to=PathMatcher(
                path=to_data.get("path"),
                pathNot=to_data.get("pathNot"),
            ),
            circular=data.get("circular", False),
            orphan=data.get("orphan", False),
        )

    def _parse_options(self, data: dict, warnings: list[str]) -> ConfigOptions:
        """Parse options dictionary into ConfigOptions object."""
        self._warn_unknown_keys(data, self._OPTION_KEYS, "options", warnings)
        return ConfigOptions(
            exclude=data.get("exclude", []),
        )
