#!/usr/bin/env python
import re

from sizefs.contents import XegerGen

__author__ = "Joel Wright, Mark McArdle"


def test_simple():
    generator = XegerGen(1024, filler="0", max_random=10)
    contents = generator.read(0, 15)
    assert contents == "0000000000000000"


def test_padding():
    # Default padding
    generator = XegerGen(64, filler="55555", max_random=10)
    contents = generator.read(0, 63)
    assert contents.endswith("50000")
    # Longer padding sequence (should be truncated)
    generator = XegerGen(64, filler="55555", padder="longer", max_random=10)
    contents = generator.read(0, 63)
    assert contents.endswith("5long")
    # Longer padding and suffix
    generator = XegerGen(64, filler="55555", padder="longer",
                         max_random=10, suffix="9999999999")
    contents = generator.read(0, 63)
    assert contents.endswith("5long9999999999")


def test_prefix():
    generator = XegerGen(1024, prefix="11", filler="0", max_random=10)
    contents = generator.read(0, 15)
    assert contents == "1100000000000000"


def test_suffix():
    generator = XegerGen(16, suffix="1111", filler="0", max_random=10)
    contents = generator.read(0, 15)
    assert contents == "0000000000001111"


def test_repeat():
    generator = XegerGen(1024, filler="ab", max_random=10)
    contents = generator.read(0, 15)
    assert contents == "abababababababab"


def test_star():
    for _ in range(0, 128):
        generator = XegerGen(1024, filler="a(bc)*d", max_random=10)
        contents = generator.read(0, 255)
        match = re.match("a(bc)*d", contents)
        assert match is not None


def test_plus():
    for _ in range(0, 128):
        generator = XegerGen(1024, filler="a(bc)+d", max_random=10)
        contents = generator.read(0, 255)
        match = re.match("a(bc)+d", contents)
        assert match is not None


def test_numbered_repeat():
    # Test repeats without overrun
    generator = XegerGen(1024, filler="a(bc){5}d", max_random=10)
    contents = generator.read(0, 15)
    assert contents == "abcbcbcbcbcdabcb"
    assert generator._remainder == "cbcbcbcd"
    # Test repeats with overrun
    generator = XegerGen(16, filler="a(bc){5}d", max_random=10)
    contents = generator.read(0, 15)
    assert contents == "abcbcbcbcbcd0000"


def test_choice():
    for _ in range(0, 128):
        generator = XegerGen(1024, filler="a[012345]{14}b", max_random=10)
        contents = generator.read(0, 15)
        match = re.match("a[012345]{14}b", contents)
        assert match is not None


def test_range():
    for _ in range(0, 128):
        generator = XegerGen(1024, filler="a[0-9,a-z,A-Z]{5}d", max_random=10)
        contents = generator.read(0, 256)
        match = re.match("a[0-9,a-z,A-Z]{5}d", contents)
        assert match is not None
