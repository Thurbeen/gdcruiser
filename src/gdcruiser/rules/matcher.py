"""Path matching for rule evaluation."""

import re

from ..config.models import PathMatcher


class PathMatcherCompiled:
    """Compiled path matcher for efficient rule evaluation."""

    def __init__(self, matcher: PathMatcher) -> None:
        self._path_re = re.compile(matcher.path) if matcher.path else None
        self._path_not_re = re.compile(matcher.pathNot) if matcher.pathNot else None

    def matches(self, path: str) -> bool:
        """Check if a path matches the matcher criteria."""
        # If no patterns defined, match everything
        if self._path_re is None and self._path_not_re is None:
            return True

        # Check positive match
        if self._path_re is not None:
            if not self._path_re.search(path):
                return False

        # Check negative match
        if self._path_not_re is not None:
            if self._path_not_re.search(path):
                return False

        return True

    def matches_any(self) -> bool:
        """Check if this matcher would match anything (no patterns defined)."""
        return self._path_re is None and self._path_not_re is None
