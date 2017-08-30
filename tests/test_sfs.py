import pytest

from fs.errors import ResourceInvalidError, ResourceNotFoundError

from sizefs.contents import (
    SizeFSAlphaNumGen, SizeFSOneGen, SizeFSZeroGen
)
from sizefs.sizefs import SizeFS, SizeFile, DirEntry, doc_test


__author__ = "Mark McArdle, Joel Wright"


@pytest.fixture
def sfs():
    return SizeFS()


def test_doc_test():
    doc_test()


def test_large_files(sfs):
    assert len(sfs.open('/1B').read(1)) == 1
    assert len(sfs.open('/1M').read(1)) == 1
    assert len(sfs.open('/1G').read(1)) == 1
    assert len(sfs.open('/1T').read(1)) == 1


def test_multiple_reads(sfs):
    sf = sfs.open('/10B')
    assert sf.read(4) == '0000'
    assert sf.read(4) == '0000'
    assert sf.read(4) == '00'
    assert sf.read(4) == ''


def test_binary_files(sfs):
    assert sfs.open('/1B', mode='rb').read(1) == b'0'
    assert sfs.open('/1M', mode='rb').read(1) == b'0'
    assert sfs.open('/1G', mode='rb').read(1) == b'0'
    assert sfs.open('/1T', mode='rb').read(1) == b'0'


def test_multiple_binary_reads(sfs):
    sf = sfs.open('/10B', 'rb')
    assert sf.read(4) == b'0000'
    assert sf.read(4) == b'0000'
    assert sf.read(4) == b'00'
    assert sf.read(4) == b''


def test_bad_files(sfs):
    sfs = SizeFS()
    with pytest.raises(ValueError):
        sfs.open('X')
    with pytest.raises(ValueError):
        sfs.open('/X')
    with pytest.raises(ValueError):
        sfs.open('/1X')


def test_size_file():
    assert SizeFile('/1', 1).read(1) == '0'
    zero_sf = SizeFile('/1', 1, filler=SizeFSZeroGen())
    assert zero_sf.read(1) == '0'
    one_sf = SizeFile('/1', 1, filler=SizeFSOneGen())
    assert one_sf.read(1) == '1'
    alpha_sf = SizeFile('/1', 1, filler=SizeFSAlphaNumGen())
    assert alpha_sf.read(1) in SizeFSAlphaNumGen.CHARS


def test_files(sfs):
    sfs = SizeFS()
    assert not sfs.isfile('/nofile')

    # Not Implemented
    dir_name = 'dir'
    with pytest.raises(NotImplementedError):
        sfs.open('/1B', 'w')
    with pytest.raises(NotImplementedError):
        sfs.open('/1B', 'a')
    with pytest.raises(NotImplementedError):
        sfs.makedir(dir_name)
    with pytest.raises(NotImplementedError):
        sfs.remove(dir_name)
    with pytest.raises(NotImplementedError):
        sfs.removedir(dir_name)
    with pytest.raises(NotImplementedError):
        sfs.rename(dir_name, dir_name)

    # Non Existing
    assert not sfs.isdir('/nodir')
    assert not sfs.isfile('')
    assert not sfs.isfile('/')
    assert not sfs.isfile('/sub/file')

    # Existing
    assert sfs.isdir('')
    assert sfs.isdir('/')
    assert sfs.isdir('ones')
    assert sfs.isdir('zeros')
    assert sfs.isdir('alpha_num')
    assert sfs.isdir('common')
    sfs.open('/20B')
    assert sfs.isfile('/20B')

    required_keys = ['created_time', 'accessed_time', 'st_mode',
                     'modified_time', 'size']
    info_keys = sfs.getinfo('/').keys()
    for key in required_keys:
        assert key in info_keys

    info_keys = sfs.getinfo('/20B').keys()
    for key in required_keys:
        assert key in info_keys
    assert len(sfs.listdir('/ones')) == 12

    with pytest.raises(ResourceInvalidError):
        sfs.getinfo('/no_dir')
    with pytest.raises(ResourceNotFoundError):
        sfs.listdir('/no_dir')
    with pytest.raises(ResourceInvalidError):
        sfs.listdir('/20B')
    with pytest.raises(ResourceInvalidError):
        sfs.open('/ones')
    with pytest.raises(ResourceNotFoundError):
        sfs.open('/sub/sub')


def test_read_size_file(sfs):
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
    assert count == chunks
    assert sf.tell() == 0

    # Read in 10 bytes chunks
    sf2 = SizeFile(name, size)
    read = sf2.read(sf2.tell())
    assert read == SizeFSZeroGen.CHARS*size

    # Read whole file
    sf3 = SizeFile(name, size)
    read = sf3.read()
    assert read == SizeFSZeroGen.CHARS*size

    # Read beyond end of file
    sf3 = SizeFile(name, size)
    sf3.read(size)
    read = sf3.read(chunk)
    assert read == ''

    # Seek beyond end of file
    sf4 = SizeFile(name, size)
    sf4.seek(size+chunk)
    read = sf4.read(chunk)
    assert read == ''

    # Read and Seek
    sf5 = SizeFile(name, size)
    sf5.read(chunk)
    assert sf5.pos == chunk
    sf5.seek(chunk)
    assert sf5.pos == chunk + chunk
    sf5.seek(beyond)
    assert sf5.pos == size

    # Closed File
    sf6 = SizeFile(name, size)
    sf6.close()
    assert sf6.read() == ''
    assert sf6.closed
    sf6.flush()


def test_dir_entry():
    dir_name = 'directory'
    dir_entry = DirEntry(DirEntry.DIR_ENTRY, dir_name)
    assert dir_entry.desc_contents() == '<dir >'
    assert dir_entry.__str__() == dir_entry.name
    assert dir_entry.isdir()

    file_name = '1B'
    file_entry = DirEntry(DirEntry.FILE_ENTRY, file_name)
    assert file_entry.desc_contents() == '<file 1B>'
    assert file_entry.__str__() == file_entry.name
    assert file_entry.isfile()


def test_basic(sfs):
    assert len(sfs.open('/1B').read(1)) == 1
    assert len(sfs.open('/1B').read(2)) == 1
    assert len(sfs.open('/2B').read(2)) == 2


def test_zeros(sfs):
    assert len(sfs.open('/zeros/1B').read(1)) == 1
    assert len(sfs.open('/zeros/1B').read(2)) == 1
    assert len(sfs.open('/zeros/2B').read(2)) == 2


def test_ones(sfs):
    assert len(sfs.open('/ones/1B').read(1)) == 1
    assert len(sfs.open('/ones/1B').read(2)) == 1
    assert len(sfs.open('/ones/2B').read(2)) == 2


def test_alpha_num(sfs):
    assert len(sfs.open('/alpha_num/1B').read(1)) == 1
    assert len(sfs.open('/alpha_num/1B').read(2)) == 1
    assert len(sfs.open('/alpha_num/2B').read(2)) == 2


def test_contents(sfs):
    # Contents Test
    assert sfs.open('/zeros/5B').read(5) == '00000'
    assert sfs.open('/ones/5B').read(5) == '11111'
    for ch in sfs.open('/alpha_num/5B').read(5):
        assert ch in SizeFSAlphaNumGen.CHARS


def test_length(sfs):
    k128 = 128*1000
    k256 = 256*1000
    assert len(sfs.open('/zeros/128B').read(128)) == 128
    assert len(sfs.open('/zeros/128K').read(k128-1)) == k128 - 1
    assert len(sfs.open('/alpha_num/128K').read(k128)) == k128
    assert len(sfs.open('/zeros/128K+1B').read(k128+1)) == k128+1
    assert len(sfs.open('/zeros/128K').read(k256)) == k128
    assert len(sfs.open('/zeros/5B').read(5)) == 5
    assert len(sfs.open('/ones/5B').read(5)) == 5
    assert len(sfs.open('/alpha_num/5B').read(5)) == 5
