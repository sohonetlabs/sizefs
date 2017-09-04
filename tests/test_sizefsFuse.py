import mock
import pytest

from fuse import FuseOSError

from sizefs.contents import SizeFSOneGen
from sizefs.sizefsFuse import SizefsFuse
import sizefs


@pytest.fixture
def sfs_fuse():
    return SizefsFuse()


def test_sfs_fuse(sfs_fuse):
    test_contents = 'tests'

    sfs_fuse.mkdir('/regex1', None)

    sfs_fuse.setxattr('/regex1', 'generator', 'regex', None)
    sfs_fuse.setxattr('/regex1', 'filler', test_contents, None)

    # Test multiple reads
    assert test_contents == sfs_fuse.read('/regex1/5B', 5, 0, None)
    assert test_contents == sfs_fuse.read('/regex1/5B', 5, 0, None)

    # Test simple regex
    sfs_fuse.setxattr('/regex1/5B', 'filler', 'a{2}b{2}c', None)
    assert 'aabbc' == sfs_fuse.read('/regex1/5B', 5, 0, None)


def test_sfs_fuse_create(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    assert '/10B' in sfs_fuse.files
    assert sfs_fuse.files['/10B']['attrs']['st_mode']
    assert sfs_fuse.files['/10B']['attrs']['st_nlink']
    assert sfs_fuse.files['/10B']['attrs']['st_size'] == 10
    assert sfs_fuse.files['/10B']['attrs']['st_ctime']
    assert sfs_fuse.files['/10B']['attrs']['st_mtime']
    assert sfs_fuse.files['/10B']['attrs']['st_atime']
    assert type(sfs_fuse.files['/10B']['generator']) == SizeFSOneGen


def test_sfs_fuse_get_attrs_file(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    assert set(sfs_fuse.getattr('/10B').keys()) == set([
        'st_atime', 'st_ctime', 'st_mtime', 'st_size', 'st_mode', 'st_nlink'
    ])


def test_sfs_fuse_get_attrs_folder(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    assert set(sfs_fuse.getattr('/').keys()) == set([
        'st_atime', 'st_ctime', 'st_mtime', 'st_mode', 'st_nlink'
    ])


def test_sfs_fuse_get_attrs_current_folder(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    assert set(sfs_fuse.getattr('/.').keys()) == set([
        'st_atime', 'st_ctime', 'st_mtime', 'st_mode', 'st_nlink'
    ])


def test_sfs_fuse_get_attrs_prev_folder(sfs_fuse):
    sfs_fuse.create('/zeros/10B', 'mode')
    assert set(sfs_fuse.getattr('/zeros/..').keys()) == set([
        'st_atime', 'st_ctime', 'st_mtime', 'st_mode', 'st_nlink'
    ])


def test_sfs_fuse_get_attrs_errors(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.getattr('/xxx')


def test_sfs_fuse_get_attrs_errors_current_dir(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.getattr('/zeros/xxx/.')


def test_sfs_fuse_get_attrs_errors_prev_dir(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.getattr('/zeros/xxx/yyy/..')


def test_sfs_fuse_get_attrs_trailing_slash(sfs_fuse, monkeypatch):
    with pytest.raises(FuseOSError):
        sfs_fuse.getattr('xxx/')

    def mock_create_error(path, mode):
        raise FuseOSError(errno=999)
    monkeypatch.setattr(sfs_fuse, 'create', mock_create_error)

    with pytest.raises(FuseOSError):
        sfs_fuse.getattr('xxx/')


def test_sfs_fuse_get_xattrs(sfs_fuse):

    sfs_fuse.xattrs = {
        'path': {
            'user.attr1': 'value1',
            'user.attr2': 'value2'
        }
    }

    assert sfs_fuse.getxattr('path', 'attr1') is 'value1'
    assert sfs_fuse.getxattr('path', 'user.attr2') is 'value2'


def test_sfs_fuse_list_xattrs(sfs_fuse):

    sfs_fuse.xattrs = {
        'path': {
            'xxxx.attr1': 'value1',
            'user.attr2': 'value2'
        }
    }

    assert set(sfs_fuse.listxattr('path')) == set(['attr1', 'user.attr2'])


def test_sfs_fuse_get_xattrs_apple(sfs_fuse):
    sfs_fuse.xattrs = {'path': {}}
    with pytest.raises(FuseOSError):
        assert sfs_fuse.getxattr('path', 'com.apple.attr1') is 'value1'


def test_sfs_fuse_get_xattrs_errors(sfs_fuse):
    with pytest.raises(FuseOSError):
        assert sfs_fuse.getxattr('/', 'name') is None


def test_sfs_fuse_get_xattrs_no_such_file(sfs_fuse):
    assert sfs_fuse.getxattr('/xxx', 'name') is None


def test_sfs_fuse_create_errors(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.create('/XXXX_BAD_FILE', '')
    with pytest.raises(FuseOSError):
        sfs_fuse.create('non_existant_folder/', '')


def test_sfs_fuse_not_implemented(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.chmod('', '')
    with pytest.raises(FuseOSError):
        sfs_fuse.chown('', '', '')


def test_sfs_fuse_open_bad_file(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.open('/XXXX_BAD_FILE', '')


def test_sfs_fuse_open_file(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    current_fd = sfs_fuse.fd
    assert sfs_fuse.open('/10B', '') == current_fd + 1


def test_sfs_fuse_read(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    assert sfs_fuse.read('/10B', 10, 0, None) == '1' * 10
    assert sfs_fuse.read('/10B', 10, 10, None) == ''


def test_sfs_fuse_readdir_root(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    sfs_fuse.create('/20B', 'mode')
    assert set(sfs_fuse.readdir('/', None)) == set([
        '.', '..', 'zeros', 'ones', 'alpha_num', '10B', '20B'
    ])


def test_sfs_fuse_readdir_folder(sfs_fuse):
    sfs_fuse.mkdir('/dir', 'mode')
    sfs_fuse.create('/dir/10B', 'mode')
    sfs_fuse.create('/dir/20B', 'mode')

    assert set(sfs_fuse.readdir('/dir', None)) == set([
        '.', '..', '10B', '20B'
    ])


def test_sfs_fuse_removexattr(sfs_fuse):

    sfs_fuse.xattrs = {
        'path': {
            'user.attr1': 'value1',
            'user.attr2': 'value2'
        }
    }

    sfs_fuse.removexattr('path', 'attr1')

    assert sfs_fuse.xattrs == {
        'path': {
            'user.attr2': 'value2'
        }
    }

    sfs_fuse.removexattr('path', 'user.attr2')

    assert sfs_fuse.xattrs == {'path': {}}


def test_sfs_fuse_removexattr_non_existant(sfs_fuse):
    sfs_fuse.xattrs = {'path': {}}
    with pytest.raises(FuseOSError):
        sfs_fuse.removexattr('path', 'attrX')


def test_sfs_fuse_removexattr_existing_file(sfs_fuse):
    sfs_fuse.create('/10B', 'mode')
    sfs_fuse.xattrs = {'/10B': {'user.attr': 'value'}}
    sfs_fuse.removexattr('/10B', 'attr')

    assert sfs_fuse.files['/10B']['attrs']['st_size'] == 10


def test_sfs_fuse_removexattr_existing_folder(sfs_fuse):
    sfs_fuse.mkdir('/dir', 'mode')
    sfs_fuse.create('/dir/10B', 'mode')

    sfs_fuse.xattrs = {
        '/dir': {'user.attr': 'value'},
        '/dir/10B': {'user.attr': 'value'},
    }
    sfs_fuse.removexattr('/dir', 'attr')

    assert sfs_fuse.xattrs == {
        '/dir': {},
        '/dir/10B': {'user.generator': 'ones'}
    }
    assert sfs_fuse.files['/dir/10B']['attrs']['st_size'] == 10


def test_sfs_fuse_rename(sfs_fuse):
    sfs_fuse.mkdir('/dir1', 'mode')
    assert '/dir1' in sfs_fuse.folders
    sfs_fuse.rename('/dir1', '/dir2')
    assert '/dir2' in sfs_fuse.folders


def test_sfs_fuse_rename_non_existant(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.rename('/dir1', '/dir2')


def test_sfs_fuse_rename_existing_new(sfs_fuse):
    sfs_fuse.mkdir('/dir1', 'mode')
    sfs_fuse.mkdir('/dir2', 'mode')
    with pytest.raises(FuseOSError):
        sfs_fuse.rename('/dir1', '/dir2')


def test_sfs_fuse_rename_with_files(sfs_fuse):
    sfs_fuse.mkdir('/dir1', 'mode')
    sfs_fuse.create('/dir1/10B', 'mode')
    sfs_fuse.rename('/dir1', '/dir2')

    assert sfs_fuse.folders['/dir2']
    assert type(sfs_fuse.files['/dir2/10B']['generator']) == SizeFSOneGen
    assert '/dir1' not in sfs_fuse.folders


def test_sfs_fuse_rmdir(sfs_fuse):
    sfs_fuse.mkdir('/dir1', 'mode')
    sfs_fuse.rmdir('/dir1')
    assert '/dir1' not in sfs_fuse.folders


def test_sfs_fuse_rmdir_non_existant(sfs_fuse):
    with pytest.raises(FuseOSError):
        sfs_fuse.rmdir('/dir2')


def test_sfs_fuse_mount(monkeypatch):
    fuse_mock = mock.Mock()
    monkeypatch.setattr(sizefs.sizefsFuse, 'FUSE', fuse_mock)
    SizefsFuse.mount('/tmp')
    SizefsFuse.mount('/tmp', debug=True)
    assert fuse_mock.mock_calls == [
        mock.call(mock.ANY, '/tmp', foreground=False, nolocalcaches=True),
        mock.call(mock.ANY, '/tmp', foreground=True, nolocalcaches=True)
    ]
