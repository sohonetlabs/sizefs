__author__ = 'jjw'

from sizefs import SizeFS
import re
import unittest


class XegerGenTestCase(unittest.TestCase):

    def test_regex_dir(self):
        sfs = SizeFS()
        sfs.mkdir("/regex1", None)
        sfs.setxattr("/regex1", "filler", "a(bcd)*e{4}", None)
        sfs.create("/regex1/128K", None)
        regex_file_contents = sfs.read("/regex1/128K", 128 * 1024, 0, None)
        match = re.match("a(bcd)*e{4}", regex_file_contents)
        self.assertIsNotNone(match)
        self.assertEqual(len(regex_file_contents), 131072)
