__author__ = 'jjw'

from sizefs import SizeFS, SIZEFSCHARS
import unittest


class SizeFSTestCase(unittest.TestCase):

    def test_basic(self):
        # Basic Test

        sfs = SizeFS()
        self.assertEqual(len(sfs.read('/zeros/1B', 1, 0, None)), 1)
        self.assertEqual(len(sfs.read('/ones/1B', 1, 0, None)), 1)
        self.assertEqual(len(sfs.read('/alpha_num/1B', 1, 0, None)), 1)

    def test_contents(self):
        # Contents Test

        sfs = SizeFS()
        self.assertEqual(sfs.read('/zeros/5B', 5, 0, None), '00000')
        self.assertEqual(sfs.read('/ones/5B', 5, 0, None), '11111')
        for ch in sfs.read('/alpha_num/5B', 5, 0, None):
            self.assertIn(ch, SIZEFSCHARS)

    def test_length(self):
        # Length Test
        k128 = 128*1000
        sfs = SizeFS()
        self.assertEqual(len(sfs.read('/128B', 128, 0, None)), 128)
        self.assertEqual(len(sfs.read('/128K', k128-1, 0, None)), k128-1)
        self.assertEqual(len(sfs.read('/128K', k128, 0, None)), k128)
        self.assertEqual(len(sfs.read('/128K+1B', k128+1, 0, None)), k128+1)
        self.assertEqual(len(sfs.read('/zeros/5B', 5, 0, None)), 5)
        self.assertEqual(len(sfs.read('/ones/5B', 5, 0, None)), 5)
        self.assertEqual(len(sfs.read('/alpha_num/5B', 5, 0, None)), 5)


if __name__ == '__main__':
    unittest.main()
