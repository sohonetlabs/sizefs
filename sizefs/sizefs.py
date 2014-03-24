#!/usr/bin/env python
"""
SizeFS is a mock filesystem that exists in memory only and allows
for the creation of files of a size specified by the filename.

SizeFS is the main public class representing a Mock FileSystem

For example, reading a file named 128M+1B will return a file of 128 Megabytes
plus 1 byte, reading a file named 128M-1B will return a file of 128 Megabytes
minus 1 byte

>>> from sizefs import SizeFS
>>> sfs = SizeFS()
>>> print len(sfs.open('1B').read())
1
>>> print len(sfs.open('2B').read())
2
>>> print len(sfs.open('1K').read())
1000
>>> print len(sfs.open('128K').read())
128000

The folder structure can also be used to determine the content of the files

>>> print sfs.open('zeros/5B').read(5)
00000

>>> print sfs.open('ones/128K').read(5)
11111

File content can also be random

>>> print len(sfs.open('alpha_num/128K').read())
128000
>>> print len(sfs.open('alpha_num/128K-1B').read())
127999
>>> print len(sfs.open('alpha_num/128K+1B').read())
128001

File content for common file size limits

>>> print sfs.listdir('common')
[u'100M-1B', u'2G-1B', u'4G-1B', u'100M+1B', u'2G+1B', u'4G+1B']

See
https://code.google.com/p/macfuse/wiki/OPTIONS
http://fuse.sourceforge.net/doxygen/index.html

Usage:
  sizefs.py [--debug] <mount_point>
  sizefs.py --version

Options:
  --debug           Debug
  -h --help         Show this screen.
  --version         Show version.
"""

import logging
import datetime
import os
import stat
from docopt import docopt
from fs.path import iteratepath, pathsplit, normpath
from fs.base import FS, synchronize
from fs.errors import ResourceNotFoundError, ResourceInvalidError
from contents import (SizeFSOneGen, SizeFSZeroGen, SizeFSAlphaNumGen, ONE_K,
                      FILE_REGEX)
from sizefsFuse import SizeFSLogging, SizefsFuse


__author__ = "Mark McArdle, Joel Wright"


def __get_shift__(match):
    """
    Parses the shift part of a filename e.g. +128, -110
    """
    shift = 0
    keys = match.groupdict().keys()
    if "operator" in keys and "shift_si" in keys:
        operator = match.group('operator')
        shift_str = match.group('shift')
        if operator != '' and shift_str:
            shift = int(shift_str)
            if operator == "-":
                shift = -shift
    return shift


def __get_size__(filename):
    """
    Parses the filename to get the size of a file
    e.g. 128M+12, 110M-10
    """
    match = FILE_REGEX.search(filename)
    if match:
        size_str = match.group('size')
        si_unit = match.group('size_si')
        shift = __get_shift__(match)
        mul = 1
        if si_unit == 'B':
            mul = 1
        elif si_unit == 'K':
            mul = ONE_K
        elif si_unit == 'M':
            mul = pow(ONE_K, 2)
        elif si_unit == 'G':
            mul = pow(ONE_K, 3)
        elif si_unit == 'T':
            mul = pow(ONE_K, 4)
        size = int(size_str)
        size_in_bytes = (size * mul) + shift
        return size_in_bytes
    else:
        raise ValueError


class SizeFile(object):
    """
    A mock file object that returns a specified number of bytes
    """

    def __init__(self, path, size, filler=None):
        self.closed = False
        self.length = size
        self.pos = 0
        self.filler = filler
        if not filler:
            self.filler = SizeFSZeroGen()
        self.path = path

    def close(self):
        """ close the file to prevent further reading """
        self.closed = True

    def read(self, size=None):
        """ read size from the file, or if size is None read to end """
        if self.pos >= self.length or self.closed:
            return ''
        if size is None:
            toread = self.tell()
            self.pos += toread
            return self.filler.fill(toread)
        else:
            if size + self.pos >= self.length:
                toread = self.length - self.pos
                self.pos = self.length
                return self.filler.fill(toread)
            else:
                toread = size
                self.pos = self.pos + size
                return self.filler.fill(toread)

    def seek(self, offset):
        """ seek the position by a distance of 'offset' bytes
        """
        if self.pos + offset > self.length:
            self.pos = self.length
        else:
            self.pos = self.pos + offset

    def tell(self):
        """ return how much of the file is left to read """
        return self.length - self.pos

    def flush(self):
        """ flush the contents """
        pass

    def reset(self):
        """ Reset the object the contents """
        self.closed = False
        self.pos = 0


class DirEntry(object):  # pylint: disable=R0902
    """
    A directory entry. Can be a file or folder.
    """

    DIR_ENTRY = 'dir'
    FILE_ENTRY = 'file'
    TYPES = (DIR_ENTRY, FILE_ENTRY)

    def __init__(self, dir_type, name, contents=None,
                 filler=None, mem_file=None):

        assert dir_type in self.TYPES, "Type must be dir or file!"

        self.type = dir_type
        self.name = name

        if contents is None and dir_type == "dir":
            contents = {}

        self.filler = filler
        if not filler:
            self.filler = SizeFSZeroGen()
        self.contents = contents
        self.mem_file = mem_file
        self.created_time = datetime.datetime.now()
        self.modified_time = self.created_time
        self.accessed_time = self.created_time

        if self.type == 'file' and not mem_file:
            self.mem_file = SizeFile(name, __get_size__(name), filler=filler)

    def desc_contents(self):
        """ describes the contents of this DirEntry """
        if self.isfile():
            return "<%s %s>" % (self.type, self.name)
        elif self.isdir():
            return "<%s %s>" % (self.type, "".join(
                "%s: %s" % (k, v.desc_contents())
                for k, v in self.contents.iteritems()))

    def isdir(self):
        """ is this DirEntry a directory """
        return self.type == DirEntry.DIR_ENTRY

    def isfile(self):
        """ is this DirEntry a file """
        return self.type == DirEntry.FILE_ENTRY

    def __str__(self):
        return self.name


class SizeFS(FS):  # pylint: disable=R0902,R0904,R0921
    """
    A mock file system that returns files of specified sizes and content
    """

    def __init__(self, *args, **kwargs):
        self.verbose = kwargs.pop("verbose", False)
        super(SizeFS, self).__init__(*args, **kwargs)
        #thread_synchronize=_thread_synchronize_default)
        self.sizes = [1, 10, 100]
        self.si_units = ['K', 'M', 'G', 'B']
        files = ["%s%s" % (size, si)
                 for size in self.sizes
                 for si in self.si_units]
        self.root = DirEntry(DirEntry.DIR_ENTRY, 'root')

        self.zeros = DirEntry(DirEntry.DIR_ENTRY, 'zeros',
                              filler=SizeFSZeroGen())
        self.ones = DirEntry(DirEntry.DIR_ENTRY, 'ones',
                             filler=SizeFSOneGen())
        self.alpha_num = DirEntry(DirEntry.DIR_ENTRY, 'alpha_num',
                                  filler=SizeFSAlphaNumGen())
        self.common = DirEntry(DirEntry.DIR_ENTRY, 'common',
                               filler=SizeFSZeroGen())

        for filename in files:
            self.zeros.contents[filename] = DirEntry(
                DirEntry.FILE_ENTRY, filename, filler=SizeFSZeroGen())
            self.ones.contents[filename] = DirEntry(
                DirEntry.FILE_ENTRY, filename, filler=SizeFSOneGen())
            self.alpha_num.contents[filename] = DirEntry(
                DirEntry.FILE_ENTRY, filename,
                filler=SizeFSAlphaNumGen())

        # Create a list of common file size limits
        common_sizes = [
            '100M',  # PHP default
            '2G',  # signed int
            '4G',  # unsigned int
        ]

        for filename in common_sizes:
            # Take the base file size limit and plus/minus 1 byte
            plus_one = "%s+1B" % filename
            minus_one = "%s-1B" % filename
            self.common.contents[plus_one] = DirEntry(
                DirEntry.FILE_ENTRY, plus_one, filler=SizeFSAlphaNumGen())
            self.common.contents[minus_one] = DirEntry(
                DirEntry.FILE_ENTRY, minus_one, filler=SizeFSAlphaNumGen())

        self.root.contents['zeros'] = self.zeros
        self.root.contents['ones'] = self.ones
        self.root.contents['alpha_num'] = self.alpha_num
        self.root.contents['common'] = self.common

    def _get_dir_entry(self, dir_path):
        """
        Returns a DirEntry for a specified path 'dir_path'
        """
        dir_path = normpath(dir_path)
        current_dir = self.root
        for path_component in iteratepath(dir_path):
            dir_entry = current_dir.contents.get(path_component, None)
            if dir_entry is not None:
                return dir_entry
            current_dir = dir_entry
        return current_dir

    def isdir(self, path):
        path = normpath(path)
        if path in ('', '/'):
            return True
        dir_item = self._get_dir_entry(path)
        if dir_item is None:
            return False
        return dir_item.isdir()

    @synchronize
    def isfile(self, path):
        path = normpath(path)
        if path in ('', '/'):
            return False
        dir_name = os.path.dirname(path)
        file_name = os.path.basename(path)
        dir_item = self._get_dir_entry(dir_name)
        if dir_item is None:
            return False
        return file_name in dir_item.contents

    @synchronize
    def makedir(self, dirname, recursive=False, allow_recreate=False):
        raise NotImplementedError

    @synchronize
    def remove(self, path):
        raise NotImplementedError

    @synchronize
    def removedir(self, path, recursive=False, force=False):
        raise NotImplementedError

    @synchronize
    def rename(self, src, dst):
        raise NotImplementedError

    @synchronize
    def listdir(self, path="/", wildcard=None,  # pylint: disable=R0913
                full=False, absolute=False,
                dirs_only=False, files_only=False):
        dir_entry = self._get_dir_entry(path)
        if dir_entry is None:
            raise ResourceNotFoundError(path)
        if dir_entry.isfile():
            raise ResourceInvalidError(path, msg="not a directory: %(path)s")
        paths = dir_entry.contents.keys()
        for (i, _path) in enumerate(paths):
            if not isinstance(_path, unicode):
                paths[i] = unicode(_path)
        p_dirs = self._listdir_helper(path, paths, wildcard, full,
                                      absolute, dirs_only, files_only)
        return p_dirs

    @synchronize
    def getinfo(self, path):
        dir_entry = self._get_dir_entry(path)

        if dir_entry is None:
            raise ResourceInvalidError(path, msg="not a directory: %(path)s")

        info = {
            'created_time': dir_entry.created_time,
            'modified_time': dir_entry.modified_time,
            'accessed_time': dir_entry.accessed_time
        }

        if dir_entry.isdir():
            info['size'] = 4096
            info['st_nlink'] = 0
            info['st_mode'] = 0755 | stat.S_IFDIR
        else:
            info['size'] = dir_entry.mem_file.length
            info['st_mode'] = 0666 | stat.S_IFREG

        return info

    @synchronize
    def open(self, path, mode="r", **kwargs):
        """

        """
        path = normpath(path)
        file_path, file_name = pathsplit(path)
        parent_dir_entry = self._get_dir_entry(file_path)

        if parent_dir_entry is None or not parent_dir_entry.isdir():
            raise ResourceNotFoundError(path)

        if 'r' in mode:

            if file_name in parent_dir_entry.contents:
                file_dir_entry = parent_dir_entry.contents[file_name]
                if file_dir_entry.isdir():
                    raise ResourceInvalidError(path)
                file_dir_entry.accessed_time = datetime.datetime.now()
                file_dir_entry.mem_file.reset()
                return file_dir_entry.mem_file
            else:
                size = __get_size__(file_name)
                mem_file = SizeFile(path, size, filler=parent_dir_entry.filler)
                mem_file.reset()
                new_entry = DirEntry(DirEntry.FILE_ENTRY, path,
                                     mem_file=mem_file)

                parent_dir_entry.contents[file_name] = new_entry
                return mem_file

        elif 'w' in mode or 'a' in mode:
            raise NotImplementedError


def doc_test():
    """
    Run doctests
    """
    import doctest
    doctest.testmod()


if __name__ == '__main__':
    ARGUMENTS = docopt(__doc__, version='SizeFS 0.2.2')
    MOUNT_POINT = ARGUMENTS['<mount_point>']
    DEBUG = ARGUMENTS['--debug']
    if os.path.exists(MOUNT_POINT):
        SizefsFuse.mount(MOUNT_POINT, debug=DEBUG)
    else:
        raise IOError('Path "%s" does not exist.' % MOUNT_POINT)
