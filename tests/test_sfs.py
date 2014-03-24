#!/usr/bin/env python
import unittest2
from fs.errors import ResourceInvalidError, ResourceNotFoundError
from sizefs.sizefs import SizeFS, SizeFile, DirEntry, doc_test
from sizefs.contents import (SizeFSAlphaNumGen, ONE_K, SizeFSOneGen,
                             SizeFSZeroGen)
from sizefs.sizefsFuse import SizefsFuse

__author__ = "Mark McArdle, Joel Wright"


class SizeFSTestCase(unittest2.TestCase):

    def setUp(self):
        self.sfs = SizeFS()

    def test_doc_test(self):
        doc_test()

    def test_basic(self):
        # Basic Test
        self.assertEqual(len(self.sfs.open('/1B').read(1)), 1)
        self.assertEqual(len(self.sfs.open('/zeros/1B').read(1)), 1)
        self.assertEqual(len(self.sfs.open('/ones/1B').read(1)), 1)
        self.assertEqual(len(self.sfs.open('/alpha_num/1B').read(1)), 1)

    def test_large_files(self):
        self.assertEqual(len(self.sfs.open('/1B').read(1)), 1)
        self.assertEqual(len(self.sfs.open('/1M').read(1)), 1)
        self.assertEqual(len(self.sfs.open('/1G').read(1)), 1)
        self.assertEqual(len(self.sfs.open('/1T').read(1)), 1)

    def test_bad_files(self):
        self.assertRaises(ValueError, self.sfs.open, 'X')
        self.assertRaises(ValueError, self.sfs.open, '/X')
        self.assertRaises(ValueError, self.sfs.open, '/1X')

    def test_contents(self):
        # Contents Test
        self.assertEqual(self.sfs.open('/zeros/5B').read(5), '00000')
        self.assertEqual(self.sfs.open('/ones/5B').read(5), '11111')
        for ch in self.sfs.open('/alpha_num/5B').read(5):
            self.assertTrue(ch in SizeFSAlphaNumGen.CHARS)

    def test_size_file(self):
        self.assertEqual(SizeFile('/1', 1).read(1), '0')
        zero_sf = SizeFile('/1', 1, filler=SizeFSZeroGen())
        self.assertEqual(zero_sf.read(1), '0')
        one_sf = SizeFile('/1', 1, filler=SizeFSOneGen())
        self.assertEqual(one_sf.read(1), '1')
        alpha_sf = SizeFile('/1', 1, filler=SizeFSAlphaNumGen())
        self.assertIn(alpha_sf.read(1), SizeFSAlphaNumGen.CHARS)

    def test_files(self):
        self.assertFalse(self.sfs.isfile('/nofile'))

        # Not Implemented
        dir_name = 'dir'
        self.assertRaises(NotImplementedError, self.sfs.open, '/1B', 'w')
        self.assertRaises(NotImplementedError, self.sfs.open, '/1B', 'a')
        self.assertRaises(NotImplementedError, self.sfs.makedir, dir_name)
        self.assertRaises(NotImplementedError, self.sfs.remove, dir_name)
        self.assertRaises(NotImplementedError, self.sfs.removedir, dir_name)
        self.assertRaises(NotImplementedError, self.sfs.rename, dir_name,
                          dir_name)

        # Non Existing
        self.assertFalse(self.sfs.isdir('/nodir'))
        self.assertFalse(self.sfs.isfile(''))
        self.assertFalse(self.sfs.isfile('/'))
        self.assertFalse(self.sfs.isfile('/sub/file'))

        # Existing
        self.assertTrue(self.sfs.isdir(''))
        self.assertTrue(self.sfs.isdir('/'))
        self.assertTrue(self.sfs.isdir('ones'))
        self.assertTrue(self.sfs.isdir('zeros'))
        self.assertTrue(self.sfs.isdir('alpha_num'))
        self.assertTrue(self.sfs.isdir('common'))
        self.sfs.open('/20B')
        self.assertTrue(self.sfs.isfile('/20B'))

        required_keys = ['created_time', 'accessed_time', 'st_mode',
                         'modified_time', 'size']
        info_keys = self.sfs.getinfo('/').keys()
        for key in required_keys:
            self.assertIn(key, info_keys)

        info_keys = self.sfs.getinfo('/20B').keys()
        for key in required_keys:
            self.assertIn(key, info_keys)
        self.assertEqual(len(self.sfs.listdir('/ones')), 12)

        self.assertRaises(ResourceInvalidError, self.sfs.getinfo, '/no_dir')
        self.assertRaises(ResourceNotFoundError, self.sfs.listdir, '/no_dir')
        self.assertRaises(ResourceInvalidError, self.sfs.listdir, '/20B')
        self.assertRaises(ResourceInvalidError, self.sfs.open, '/ones')
        self.assertRaises(ResourceNotFoundError, self.sfs.open, '/sub/sub')

    def test_read_size_file(self):
        size = 1000
        chunk = 100
        beyond = size + 10
        chunks = int(size/chunk)
        name = '/%s' % size

        sf = SizeFile(name, size)
        count = 0
        while sf.tell() > 0:
            sf.read(chunk)
            count += 1
        self.assertEqual(count, chunks)
        self.assertEqual(sf.tell(), 0)

        # Read in 10 bytes chunks
        sf2 = SizeFile(name, size)
        read = sf2.read(sf2.tell())
        self.assertEqual(read, SizeFSZeroGen.CHARS*size)

        # Read whole file
        sf3 = SizeFile(name, size)
        read = sf3.read()
        self.assertEqual(read, SizeFSZeroGen.CHARS*size)

        # Read beyond end of file
        sf3 = SizeFile(name, size)
        sf3.read(size)
        read = sf3.read(chunk)
        self.assertEqual(read, '')

        # Seek beyond end of file
        sf4 = SizeFile(name, size)
        sf4.seek(size+chunk)
        read = sf4.read(chunk)
        self.assertEqual(read, '')

        # Read and Seek
        sf5 = SizeFile(name, size)
        sf5.read(chunk)
        self.assertEqual(sf5.pos, chunk)
        sf5.seek(chunk)
        self.assertEqual(sf5.pos, chunk + chunk)
        sf5.seek(beyond)
        self.assertEqual(sf5.pos, size)

        # Closed File
        sf6 = SizeFile(name, size)
        sf6.close()
        self.assertEqual(sf6.read(), '')
        self.assertTrue(sf6.closed)
        sf6.flush()

    def test_dir_entry(self):
        dir_name = 'directory'
        dir_entry = DirEntry(DirEntry.DIR_ENTRY, dir_name)
        self.assertEqual(dir_entry.desc_contents(), '<dir >')
        self.assertEqual(dir_entry.__str__(), dir_entry.name)
        self.assertTrue(dir_entry.isdir())

        file_name = '1B'
        file_entry = DirEntry(DirEntry.FILE_ENTRY, file_name)
        self.assertEqual(file_entry.desc_contents(), '<file 1B>')
        self.assertEqual(file_entry.__str__(), file_entry.name)
        self.assertTrue(file_entry.isfile())

    def test_length(self):
        # Length Test
        k64 = 64 * ONE_K
        k128 = 128 * ONE_K
        k256 = 256 * ONE_K
        self.assertEqual(len(self.sfs.open('/zeros/128B').read(128)), 128)
        self.assertEqual(len(self.sfs.open('/zeros/128K').read(k128-1)),
                         k128-1)
        self.assertEqual(len(self.sfs.open('/alpha_num/128K').read(k128)),
                         k128)
        self.assertEqual(len(self.sfs.open('/zeros/128K+1B').read(k128+1)),
                         k128+1)

        # Read same file twice
        self.assertEqual(len(self.sfs.open('/zeros/64K').read(k128)), k64)
        self.assertEqual(len(self.sfs.open('/zeros/64K').read(k128)), k64)

        self.assertEqual(len(self.sfs.open('/zeros/5B').read(5)), 5)
        self.assertEqual(len(self.sfs.open('/ones/5B').read(5)), 5)
        self.assertEqual(len(self.sfs.open('/alpha_num/5B').read(5)), 5)


class SizeFSFuseTestCase(unittest2.TestCase):

    def setUp(self):
        self.sfs = SizefsFuse()

    def test_sfs_fuse(self):
        test_contents = 'tests'
        self.sfs.mkdir('/regex1', None)

        self.sfs.setxattr('/regex1', 'generator', 'regex', None)
        self.sfs.setxattr('/regex1', 'filler', test_contents, None)

        # Test multiple reads
        self.assertEqual(test_contents,
                         self.sfs.read('/regex1/5B', 5, 0, None))
        self.assertEqual(test_contents,
                         self.sfs.read('/regex1/5B', 5, 0, None))

        # Test simple regex
        self.sfs.setxattr('/regex1/5B', 'filler', 'a{2}b{2}c', None)
        self.assertEqual('aabbc', self.sfs.read('/regex1/5B', 5, 0, None))


if __name__ == '__main__':
    unittest2.main()
