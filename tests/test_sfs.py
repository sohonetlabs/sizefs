__author__ = 'jjw'

import sys
import os
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sizefs import SizeFS
import unittest


class SizeFSTestCase(unittest.TestCase):

    def test_basic(self):
        sfs = SizeFS()

        # Basic Test
        self.assertEqual(len(sfs.get_size_file('1B').read(0, 1)), 1)

        # Contents Test
        self.assertEqual(sfs.get_size_file('/zeros/5B').read(0, 5), '00000')
        self.assertEqual(sfs.get_size_file('/ones/5B').read(0, 5), '11111')

        # Length Test
        self.assertEqual(len(sfs.get_size_file('128B').read(0, 127)), 128)
        self.assertEqual(len(sfs.get_size_file('128K').read(0, 128*1024-1)),
                         128*1024)
        self.assertEqual(len(sfs.get_size_file('128K-1B').read(0, 128*1024)),
                         128*1024-1)
        self.assertEqual(len(sfs.get_size_file('128K+1B').read(0, 128*1024+1)),
                         128*1024+1)
        self.assertEqual(len(sfs.get_size_file('/alpha_num/5B').read(0, 5)), 5)


if __name__ == '__main__':
    unittest.main()
