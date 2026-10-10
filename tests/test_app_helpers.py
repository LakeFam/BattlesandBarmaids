# Unit tests for app.py's small helper functions. No database or HTTP needed.
import pytest

from app import is_positive_int

@pytest.mark.parametrize("value", [1, 42])
def test_positive_whole_numbers_are_accepted(value):
    assert is_positive_int(value) is True

# True is an int in Python, so it needs its own check.
@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "1", None])
def test_other_values_are_rejected(value):
    assert is_positive_int(value) is False
