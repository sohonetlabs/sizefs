import pytest

from sizefs.contents import SizeFSAlphaNumGen


@pytest.fixture(autouse=True)
def num_chars(monkeypatch):
    # we dont need that many characters for testing
    # this makes the tests really fast
    monkeypatch.setattr(SizeFSAlphaNumGen, 'NUM_CHARS', 64)
