import unittest

from trashcli.list import TrashDirsSelector
from trashcli.trash import trash_dir_found


class MockScanner:
    def __init__(self, name):
        self.name = name

    def scan_trash_dirs(self, environ, uid):
        return [self.name, environ, uid]


class TestTrashDirsSelector(unittest.TestCase):
    def setUp(self):
        self.volume_of = lambda x: "volume_of %s" % x
        self.selector = TrashDirsSelector(MockScanner("user"),
                                          MockScanner("all"),
                                          self.volume_of)

    def test_default(self):
        result = list(self.selector.select(False, [], 'environ', 'uid'))

        assert result == ['user', 'environ', 'uid']

    def test_user_specified(self):
        result = list(self.selector.select(False, ['user-specified-dirs'],
                                           'environ', 'uid'))

        assert result == [(trash_dir_found, ('user-specified-dirs',
                                             'volume_of user-specified-dirs'))]

    def test_all_user_specified(self):
        result = list(self.selector.select(True, ['user-specified-dirs'],
                                           'environ', 'uid'))

        assert result == ['all', 'environ', 'uid']
