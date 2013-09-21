__author__ = 'jjw'

from sizefs.contents import XegerGen
import re
import unittest


class XegerGenTestCase(unittest.TestCase):

    def test_simple(self):
        generator = XegerGen(1024, filler="0", max_random=10)
        contents = generator.read(0, 15)
        assert contents == "0000000000000000"

    def test_repeat(self):
        generator = XegerGen(1024, filler="ab", max_random=10)
        contents = generator.read(0, 15)
        assert contents == "abababababababab"

    def test_star(self):
        generator = XegerGen(1024, filler="a(bc)*d", max_random=10)
        contents = generator.read(0, 255)
        match = re.match("a(bc)*d", contents)
        assert match is not None

    def test_plus(self):
        generator = XegerGen(1024, filler="a(bc)+d", max_random=10)
        contents = generator.read(0, 255)
        match = re.match("a(bc)+d", contents)
        assert match is not None

    def test_numbered_repeat(self):
        generator = XegerGen(1024, filler="a(bc){5}d", max_random=10)
        contents = generator.read(0, 15)
        assert contents == "abcbcbcbcbcdabcb"

    def test_choice(self):
        generator = XegerGen(1024, filler="a[012345]{14}b", max_random=10)
        contents = generator.read(0, 256)
        match = re.match("a[012345]{14}b", contents)
        assert match is not None


    def test_range(self):
        generator = XegerGen(1024, filler="a[0-9,a-z,A-Z]{5}d", max_random=10)
        contents = generator.read(0, 256)
        match = re.match("a[0-9,a-z,A-Z]{5}d", contents)
        assert match is not None

if __name__ == '__main__':
    unittest.main()
