#!/usr/bin/env python
import pytest
import re

from sizefs.contents import (
    XegerExpression, XegerGen, XegerError, XegerMultiplier,
    SizeFSGen, SizeFSZeroGen,
)

__author__ = "Joel Wright, Mark McArdle"


def test_sizefs_gen():
    generator = SizeFSGen()
    contents = generator.read(0, 15)
    assert contents == "XXXXXXXXXXXXXXX"


def test_sizefs_zero_gen():
    generator = SizeFSZeroGen()
    contents = generator.read(0, 15)
    assert contents == "000000000000000"


def test_xeger_gen():
    generator = XegerGen(1024, filler="0", max_random=10)
    contents = generator.read(0, 15)
    assert contents == "0000000000000000"


def test_xeger_gen_empty_filler():
    generator = XegerGen(64, filler="", max_random=10)
    assert generator._filler._pattern._sequence == '0'


def test_xeger_gen_empty_padder():
    generator = XegerGen(64, padder="", max_random=10)
    assert generator._padder._pattern._sequence == '0'


def test_xeger_gen_empty_prefix():
    generator = XegerGen(64, prefix="", max_random=10)
    assert generator._prefix == ""


def test_xeger_gen_empty_suffix():
    generator = XegerGen(64, suffix="", max_random=10)
    assert generator._suffix == ""


def test_xeger_gen_read_beyond_length():
    generator = XegerGen(10, prefix='XX')
    contents1 = generator.read(0, 10)
    assert contents1 == "XX00000000"
    contents2 = generator.read(0, 10)
    assert contents2 == "XX00000000"


def test_xeger_read_beyond_prefix():
    generator = XegerGen(20, prefix='XX')
    contents1 = generator.read(10, 20)
    assert contents1 == "0000000000"  # note no prefix


def test_xeger_gen_read_before_beginning():
    generator = XegerGen(10, prefix='XX')
    contents = generator.read(-10, 10)
    assert contents == "XX00000000"


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


def tests_xeger_expression_multiplier():
    xger = XegerExpression(['a{2}b{2}c'])
    assert xger._generator._sequence == 'a{2}b{2}c'
    assert xger._constant_multiplier is None
    assert xger._multiplier is None


def tests_xeger_multiplier_illegal_end_of_mulitplier():
    with pytest.raises(XegerError):
        XegerMultiplier(['}'])


def tests_xeger_multiplier_illegal_pattern():
    with pytest.raises(XegerError):
        XegerMultiplier(['{', '*'])


def tests_xeger_multiplier_illegal_end():
    with pytest.raises(XegerError):
        XegerMultiplier(['{'])
