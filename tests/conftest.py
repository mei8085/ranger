import sys
import importlib.util
import os
import shutil
import pytest


def _mock_unix_modules():
    for module_name in ['grp', 'pwd']:
        if module_name not in sys.modules:
            spec = importlib.util.spec_from_loader(module_name, loader=None)
            module = importlib.util.module_from_spec(spec)

            if module_name == 'grp':
                class MockGroup:
                    def __init__(self):
                        self.gr_name = 'users'

                def getgrgid(gid):
                    return MockGroup()

                module.getgrgid = getgrgid

            elif module_name == 'pwd':
                class MockPasswd:
                    def __init__(self):
                        self.pw_name = 'user'

                def getpwuid(uid):
                    return MockPasswd()

                module.getpwuid = getpwuid

            sys.modules[module_name] = module


def _mock_os_chown():
    if not hasattr(os, 'chown'):
        def mock_chown(path, uid, gid):
            pass
        os.chown = mock_chown


def _mock_os_rename_for_windows():
    original_rename = os.rename

    def safe_rename(src, dst):
        try:
            original_rename(src, dst)
        except OSError:
            if os.path.exists(dst):
                os.remove(dst)
            original_rename(src, dst)

    os.rename = safe_rename


_mock_unix_modules()
_mock_os_chown()
_mock_os_rename_for_windows()


class MockFM:
    def __init__(self):
        self.notifications = []

    def notify(self, msg, bad=False):
        self.notifications.append((msg, bad))


@pytest.fixture
def tmp_bookmark_file(tmpdir):
    return str(tmpdir.join("bookmarkfile"))


@pytest.fixture
def mock_fm():
    return MockFM()

