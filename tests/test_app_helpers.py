# Unit tests for app.py helpers.
import pytest

from app import is_positive_int

@pytest.mark.parametrize("value", [1, 42])
def test_positive_whole_numbers_are_accepted(value):
    assert is_positive_int(value) is True

@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "1", None])
def test_other_values_are_rejected(value):
    assert is_positive_int(value) is False
