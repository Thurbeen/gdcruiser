import sys
from unittest.mock import patch

from gdcruiser import main


def test_main_returns_int():
    """Test that main() returns an integer exit code."""
    with patch.object(sys, "argv", ["gdcruiser", "--help"]):
        try:
            result = main()
        except SystemExit as e:
            result = e.code
    assert isinstance(result, int)
