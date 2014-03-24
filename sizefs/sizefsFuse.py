#!/usr/bin/env python
"""
SizeFS content generators
"""

from collections import defaultdict
from errno import ENOENT, EPERM, ENODATA, ENOTEMPTY
from stat import S_IFDIR, S_IFREG
from time import time
import logging
import os
from contents import (XegerGen, SizeFSZeroGen, SizeFSOneGen, FILE_REGEX,
                      SizeFSAlphaNumGen, SizeFSGeneratorType, ONE_K)

from fuse import FuseOSError, Operations, LoggingMixIn

__author__ = "Mark McArdle, Joel Wright"


class SizefsFuse(Operations):
    """
    Size Filesystem.

    Allows 1 level of folders to be created that have an xattr describing how
    files should be filled (regex). Each directory contains a list of commonly
    useful file sizes, however non-listed files of arbitrary size can be opened
    and read from. The size spec comes from the filename, e.g.

      open("/<folder>/1.1T-1B")
    """

    default_files = ['100K', '4M', '4M-1B', '4M+1B']
    sizes = {'B': 1, 'K': ONE_K, 'M': ONE_K**2, 'G': ONE_K**3,
             'T': ONE_K**4, 'P': ONE_K**5, 'E': ONE_K**6}

    def __init__(self):
        self.folders = {}
        self.files = {}
        self.xattrs = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.folders['/'] = dict(st_mode=(S_IFDIR | 0664), st_ctime=now,
                                 st_mtime=now, st_atime=now, st_nlink=0)
        self.xattrs['/'] = {}

        # Create the default dirs (zeros, ones, common)
        self.mkdir('/zeros', (S_IFDIR | 0664))
        self.setxattr('/zeros', u'user.generator',
                      SizeFSGeneratorType.ZEROS, None)
        self._add_default_files('/zeros')
        self.mkdir('/ones', (S_IFDIR | 0664))
        self.setxattr('/ones', u'user.generator',
                      SizeFSGeneratorType.ONES, None)
        self._add_default_files('/ones')
        self.mkdir('/alpha_num', (S_IFDIR | 0664))
        self.setxattr('/alpha_num', u'user.generator',
                      SizeFSGeneratorType.ALPHA_NUM, None)
        self._add_default_files('/alpha_num')

    def chmod(self, path, mode):
        """
        We'll return EPERM error to indicate that the user cannot change the
        permissions of files/folders
        """
        raise FuseOSError(EPERM)

    def chown(self, path, uid, gid):
        """
        We'll return EPERM error to indicate that the user cannot change the
        ownership of files/folders
        """
        raise FuseOSError(EPERM)

    def create(self, path, mode, fi=None):
        """
        We'll return EPERM error to indicate that the user cannot create files
        anywhere but within folders created to serve regex filled files, and
        only with valid filenames
        """
        (folder, filename) = os.path.split(path)

        if folder in self.folders:
            _m = FILE_REGEX.match(filename)
            if _m:
                attrs = self._file_attrs(_m)
                size_bytes = attrs['st_size']

                # Get the inherited xattrs from the containing folder and
                # create the content generator
                folder_xattrs = self.xattrs[folder]
                generator = folder_xattrs.get(u'user.generator', None)
                filler = folder_xattrs.get(u'user.filler', None)
                prefix = folder_xattrs.get(u'user.prefix', None)
                suffix = folder_xattrs.get(u'user.suffix', None)
                padder = folder_xattrs.get(u'user.padder', None)
                max_random = folder_xattrs.get(u'user.max_random', u'10')

                self.xattrs[path] = {}
                if generator is not None:
                    self.setxattr(path, u'user.generator', generator, None)
                if filler is not None:
                    self.setxattr(path, u'user.filler', filler, None)
                if prefix is not None:
                    self.setxattr(path, u'user.prefix', prefix, None)
                if suffix is not None:
                    self.setxattr(path, u'user.suffix', suffix, None)
                if padder is not None:
                    self.setxattr(path, u'user.padder', padder, None)
                self.setxattr(path, u'user.max_random', max_random, None)

                self.files[path] = {
                    'attrs': attrs,
                    'generator': self._create_generator(path, size_bytes)
                }
            else:
                raise FuseOSError(EPERM)
        else:
            raise FuseOSError(EPERM)

        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        """
        Getattr either returns an attribute dict for a folder from the
        self.folders map, or it returns a standard attribute dict for any valid
        files
        """
        if path in self.folders:
            return self.folders[path]

        if path in self.files:
            return self.files[path]['attrs']

        (folder, filename) = os.path.split(path)

        if filename == ".":
            if folder in self.folders:
                return self.folders[folder]
            else:
                raise FuseOSError(ENOENT)

        if filename == "..":
            (parent_folder, child_folder) = os.path.split(folder)
            if parent_folder in self.folders:
                return self.folders[parent_folder]
            else:
                raise FuseOSError(ENOENT)

        if folder == "/":
            raise FuseOSError(ENOENT)
        else:
            try:
                self.create(path, 0444)
                return self.getattr(path)
            except FuseOSError as e:
                if e.errno == EPERM:
                    raise FuseOSError(ENOENT)
                else:
                    raise e

    def getxattr(self, path, name, position=0):
        """
        Returns an extended attribute of a file/folder

        If the xattr does not exist we return ENODATA (synonymous with ENOATTR)
        """
        if not '.' in name and not name.startswith(u'user.'):
            name = u'user.%s' % name
        else:
            name = u'%s' % name

        if path in self.xattrs:
            path_xattrs = self.xattrs[path]
            if name in path_xattrs:
                return path_xattrs[name]

            if name.startswith(u'com.apple.'):
                try:
                    from errno import ENOTSUP
                    raise FuseOSError(ENOTSUP)
                except ImportError:
                    raise FuseOSError(ENODATA)
            else:
                raise FuseOSError(ENODATA)

    def listxattr(self, path):
        """
        Return a list of all extended attribute names for a file/folder
        """
        path_xattrs = self.xattrs.get(path, {})
        xattr_names = map(lambda xa: xa if xa.startswith(u'user.') else xa[5:],
                          path_xattrs)
        return xattr_names

    def mkdir(self, path, mode):
        """
        Here we ignore the mode because we only allow 0444 directories to be
        created
        """
        (parent, folder) = os.path.split(path)

        if not parent == "/":
            raise FuseOSError(EPERM)

        self.folders[path] = dict(st_mode=(S_IFDIR | 0664), st_nlink=2,
                                  st_size=0, st_ctime=time(), st_mtime=time(),
                                  st_atime=time())
        self.xattrs[path] = {}
        self.xattrs[path][u'user.generator'] = SizeFSGeneratorType.ONES
        self.folders['/']['st_nlink'] += 1

    def open(self, path, flags):
        """
        We check that a file exists in the file dictionary and return a
        unique file descriptor if so
        """
        if not path in self.files:
            raise FuseOSError(ENOENT)

        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        """
        Returns content based on the pattern of the containing folder
        """
        if path in self.files:
            size_bytes = self.files[path]['attrs']['st_size']
            if offset > (size_bytes - 1):
                return ""
            else:
                end_of_content = min(offset+size-1, size_bytes-1)
                content = self.files[path]['generator'].read(offset,
                                                             end_of_content)
                return content
        else:
            self.create(path, 0444)
            return self.read(path, size, offset, fh)

    def readdir(self, path, fh):
        contents = ['.', '..']

        if path == "/":
            for folder_path in self.folders:
                if not folder_path == "/":
                    (parent, folder_name) = os.path.split(folder_path)
                    if parent == path:
                        contents.append(folder_name)
            for file_path in self.files:
                (folder, filename) = os.path.split(file_path)
                if folder == "/":
                    contents.append(filename)
        else:
            for file_path in self.files:
                if file_path.startswith(path):
                    (folder, filename) = os.path.split(file_path)
                    contents.append(filename)

        return contents

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        if not '.' in name and not name.startswith(u'user.'):
            name = u'user.%s' % name
        else:
            name = u'%s' % name

        path_xattrs = self.xattrs[path]

        if name in path_xattrs:
            del path_xattrs[name]
            self._update_mtime(path)
        else:
            raise FuseOSError(ENODATA)

        if path in self.folders:
            file_names = self.files.keys()
            files_to_update = [filename for filename in file_names
                               if filename.startswith(path)]
            for file in files_to_update:
                self.removexattr(file, name)
        elif path in self.files:
            size_bytes = self.files[path]['attrs']['st_size']
            self.files[path]['generator'] =\
                self._create_generator(path, size_bytes)

    def rename(self, old, new):
        """
        Rename a folder

        We allow renaming of folders as this will not affect the contents of
        the folder. We raise a permissions error for files, because renaming
        a file changes the meaning of its content generator.
        """
        if old in self.folders:
            if new in self.folders:
                raise FuseOSError(EPERM)

            self.folders[new] = self.folders.pop(old)
            for file in self.files:
                (folder, filename) = os.path.split(file)
                if old == folder:
                    new_path = os.path.join(new, filename)
                    self.files[new_path] = self.files.pop(file)

        if old in self.files:
            raise FuseOSError(EPERM)

        raise FuseOSError(ENOENT)

    def rmdir(self, path):
        if path in self.folders:
            for file in self.files:
                (parent_folder, filename) = os.path.split(file)
                if parent_folder == path:
                    raise FuseOSError(ENOTEMPTY)

            del self.folders[path]
            del self.xattrs[path]
            self.folders['/']['st_nlink'] -= 1
        else:
            raise FuseOSError(ENOENT)

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options

        if not '.' in name and not name.startswith(u'user.'):
            name = u'user.%s' % name
        else:
            name = u'%s' % name

        if path in self.xattrs:
            path_xattrs = self.xattrs[path]
            if name in path_xattrs and value == path_xattrs[name]:
                return
            else:
                self._update_mtime(path)
            path_xattrs[name] = value
        else:
            raise FuseOSError(ENOENT)

        if path in self.folders:
            filenames = self.files.keys()
            files_to_update = [filename for filename in filenames
                               if filename.startswith(path)]
            for file in files_to_update:
                self.setxattr(file, name, value, options, position)

        elif path in self.files:
            size_bytes = self.files[path]['attrs']['st_size']
            self.files[path]['generator'] =\
                self._create_generator(path, size_bytes)

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        raise FuseOSError(EPERM)

    def truncate(self, path, length, fh=None):
        raise FuseOSError(EPERM)

    def unlink(self, path):
        if path in self.files:
            del self.files[path]
            del self.xattrs[path]
        else:
            raise FuseOSError(ENOENT)

    def utimens(self, path, times=None):
        pass

    def write(self, path, data, offset, fh):
        raise FuseOSError(EPERM)

    def _calculate_file_size(self, regex_match):
        file_groupdict = regex_match.groupdict()
        init_size = float(file_groupdict["size"])
        size_unit = self.sizes[file_groupdict["size_si"]]
        size = int(init_size * size_unit)

        operator = file_groupdict["operator"]
        if operator is not None:
            shift = file_groupdict["shift"]
            shift_unit = self.sizes[file_groupdict["shift_si"]]
            shift_size = int(shift) * shift_unit
            if operator == "-":
                size -= shift_size
            elif operator == "+":
                size += shift_size

        if size < 0:
            return 0
        else:
            return int(size)

    def _file_attrs(self, m):
        size = self._calculate_file_size(m)
        return dict(st_mode=(S_IFREG | 0444), st_nlink=1,
                    st_size=size, st_ctime=time(),
                    st_mtime=time(), st_atime=time())

    def _update_mtime(self, path):
        if path in self.folders:
            self.folders[path]['st_mtime'] = time()
        elif path in self.files:
            self.files[path]['attrs']['st_mtime'] = time()

    def _add_default_files(self, path):
        """
        Add a set of example files to a directory (only for demo dirs)
        """
        for default_file in self.default_files:
            new_filepath = os.path.join(path, default_file)
            self.create(new_filepath, 0444)
            #attr = self._file_attrs(FILE_REGEX.match(default_file))
            #self.files.setdefault(new_filepath, {"attrs": attr})

    def _create_generator(self, path, size_bytes):
        """
        Create a generator from xattr values
        """
        generator = self.xattrs[path].get(u'user.generator', None)
        if generator == SizeFSGeneratorType.ALPHA_NUM:
            return SizeFSAlphaNumGen()
        elif generator == SizeFSGeneratorType.ZEROS:
            return SizeFSZeroGen()
        elif generator == SizeFSGeneratorType.ONES:
            return SizeFSOneGen()
        elif generator == SizeFSGeneratorType.REGEX:
            filler = self.xattrs[path].get(u'user.filler', None)
            prefix = self.xattrs[path].get(u'user.prefix', None)
            suffix = self.xattrs[path].get(u'user.suffix', None)
            padder = self.xattrs[path].get(u'user.padder', None)
            max_random = self.xattrs[path].get(u'user.max_random', u'10')

            genr = XegerGen(size_bytes,
                            filler=filler,
                            prefix=prefix,
                            suffix=suffix,
                            padder=padder,
                            max_random=int(max_random))

            return genr
        else:
            logging.log(logging.WARNING,
                        'Unknown generator %s for %s' % (generator, path))
            self.xattrs[path][u'user.generator'] = SizeFSGeneratorType.ONES
            return SizeFSOneGen()

    @classmethod
    def mount(cls, mount_point, debug=False):
        from fuse import FUSE
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.log(logging.DEBUG, "Starting Debug Logging")

            return FUSE(SizeFSLogging(), mount_point, nolocalcaches=True,
                        foreground=True)
        else:
            return FUSE(SizefsFuse(), mount_point, nolocalcaches=True,
                        foreground=False)


class SizeFSLogging(LoggingMixIn, SizefsFuse):
    """
    SizeFS with logging MixIn
    """
