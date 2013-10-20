__author__ = 'jjw'

from sizefs import SizeFS 
from sizefs.contents import SizeFSAlphaNumGen
import unittest


class SizeFSTestCase(unittest.TestCase):

    def test_basic(self):
        # Basic Test

        sfs = SizeFS()
        self.assertEqual(len(sfs.read('/zeros/1B', 1, 0, None, create=True)), 1)
        self.assertEqual(len(sfs.read('/ones/1B', 1, 0, None, create=True)), 1)
        self.assertEqual(len(sfs.read('/alpha_num/1B', 1, 0, None, create=True)), 1)

    def test_contents(self):
        # Contents Test

        sfs = SizeFS()
        self.assertEqual(sfs.read('/zeros/5B', 5, 0, None, create=True), '00000')
        self.assertEqual(sfs.read('/ones/5B', 5, 0, None, create=True), '11111')
        for ch in sfs.read('/alpha_num/5B', 5, 0, None, create=True):
            self.assertIn(ch, SizeFSAlphaNumGen.chars)

    def test_length(self):
        # Length Test
        k128 = 128*1000
        k256 = 256*1000
        sfs = SizeFS()
        self.assertEqual(len(sfs.read('/zeros/128B', 128, 0, None, create=True)), 128)
        self.assertEqual(len(sfs.read('/zeros/128K', k128-1, 0, None, create=True)), k128-1)
        self.assertEqual(len(sfs.read('/alpha_num/128K', k128, 0, None, create=True)), k128)
        self.assertEqual(len(sfs.read('/zeros/128K+1B', k128+1, 0, None, create=True)), k128+1)
        self.assertEqual(len(sfs.read('/zeros/128K', k256, 0, None, create=True)), k128)
        self.assertEqual(len(sfs.read('/zeros/5B', 5, 0, None, create=True)), 5)
        self.assertEqual(len(sfs.read('/ones/5B', 5, 0, None, create=True)), 5)
        self.assertEqual(len(sfs.read('/alpha_num/5B', 5, 0, None, create=True)), 5)


if __name__ == '__main__':
    unittest.main()
