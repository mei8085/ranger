from __future__ import absolute_import

import os
import sys
import tempfile
from unittest import mock

import pytest


_mock_curses = mock.MagicMock()
_mock_curses.tigetnum.return_value = 8
_mock_curses.A_BOLD = 1
_mock_curses.A_NORMAL = 0
_mock_curses.A_REVERSE = 2
_mock_curses.A_UNDERLINE = 4
_mock_curses.COLOR_PAIRS = 256
_mock_curses.COLORS = 8
_mock_curses.color_pair.return_value = 0
_mock_curses.ascii = mock.MagicMock()
_mock_curses.ascii.isalnum.return_value = True
_mock_curses.ascii.isalpha.return_value = True
_mock_curses.ascii.iscntrl.return_value = False
_mock_curses.ascii.isdigit.return_value = False
_mock_curses.ascii.isgraph.return_value = True
_mock_curses.ascii.islower.return_value = False
_mock_curses.ascii.isprint.return_value = True
_mock_curses.ascii.ispunct.return_value = False
_mock_curses.ascii.isspace.return_value = False
_mock_curses.ascii.isupper.return_value = False
_mock_curses.ascii.isxdigit.return_value = False
_mock_curses.ascii.altkeysym = lambda x: x
_mock_curses.ascii.ctrl = lambda x: x
_mock_curses.ascii.unctrl = lambda x: '^' + chr(ord(x) ^ 64) if x < 32 else chr(x)

sys.modules['grp'] = mock.MagicMock()
sys.modules['pwd'] = mock.MagicMock()
sys.modules['_curses'] = mock.MagicMock()
sys.modules['curses'] = _mock_curses
sys.modules['curses.ascii'] = _mock_curses.ascii
sys.modules['curses.color_pair'] = _mock_curses.color_pair

from ranger.core.actions import Actions
from ranger.core.preview_plugin import PreviewPluginRegistry


@pytest.fixture
def temp_json_file():
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    with open(path, 'w') as f:
        f.write('{"test": 1}')
    yield path
    os.unlink(path)


@pytest.fixture
def temp_png_file():
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
    yield path
    os.unlink(path)


@pytest.fixture
def fake_scope_sh():
    fd, path = tempfile.mkstemp(suffix='.sh')
    os.close(fd)
    os.chmod(path, 0o755)
    yield path
    os.unlink(path)


@pytest.fixture
def fake_cache_dir():
    path = tempfile.mkdtemp()
    yield path
    import shutil
    shutil.rmtree(path)


class TestGetPreviewEntry:
    def _create_mock_actions(self, temp_file, scope_sh_path, cache_dir):
        actions = mock.MagicMock(spec=Actions)

        actions.settings = mock.MagicMock()
        actions.settings.preview_script = scope_sh_path
        actions.settings.use_preview_script = True
        actions.settings.preview_images = False

        actions.ui = mock.MagicMock()
        mock_pager = mock.MagicMock()
        actions.ui.get_pager.return_value = mock_pager

        actions.previews = {}
        actions.loader = mock.MagicMock()

        actions.fm = mock.MagicMock()
        actions.fm.notify = mock.MagicMock()

        actions.sha512_encode = mock.MagicMock(return_value='fake_hash')

        actions.read_text_file = mock.MagicMock(return_value='file content')

        real_stat = os.stat
        def mock_stat(path):
            if path == scope_sh_path:
                s = mock.MagicMock()
                s.st_mode = 0o755
                return s
            return real_stat(path)

        fobj = mock.MagicMock()
        fobj.realpath = temp_file
        fobj.stat = mock.MagicMock()
        fobj.stat.st_ino = 12345
        fobj.stat.st_mtime = 1234567890
        fobj.load_if_outdated = mock.MagicMock()

        return actions, fobj, mock_pager, mock_stat

    def _run_get_preview(
        self,
        actions,
        fobj,
        width,
        height,
        mock_stat,
        cache_dir,
        test_registry=None,
        mock_command_loader=None,
        preview_images=False,
    ):
        import ranger
        original_args = getattr(ranger, 'args', None)
        ranger.args = mock.MagicMock()
        ranger.args.cachedir = cache_dir

        try:
            with mock.patch('ranger.core.actions.os.stat', side_effect=mock_stat):
                with mock.patch('ranger.core.actions.os.makedirs'):
                    with mock.patch(
                        'ranger.core.actions.preview_plugin_registry',
                        test_registry if test_registry else mock.MagicMock()
                    ):
                        if mock_command_loader is not None:
                            with mock.patch(
                                'ranger.core.actions.CommandLoader',
                                mock_command_loader
                            ):
                                import ranger.core.actions as actions_module
                                return actions_module.Actions.get_preview(
                                    actions, fobj, width, height
                                )
                        else:
                            import ranger.core.actions as actions_module
                            return actions_module.Actions.get_preview(
                                actions, fobj, width, height
                            )
        finally:
            if original_args is not None:
                ranger.args = original_args

    def test_plugin_hits_returns_content_directly(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('plugin rendered json content', 0)

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result == 'plugin rendered json content'
        mock_command_loader.assert_not_called()
        actions.loader.add.assert_not_called()

    def test_plugin_returns_none_creates_command_loader(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return None

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()
        mock_command_loader.return_value = mock.MagicMock()
        mock_command_loader.return_value.signal_bind = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result is None
        mock_command_loader.assert_called_once()
        actions.loader.add.assert_called_once()

    def test_no_plugin_matches_creates_command_loader(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def txt_renderer(**kwargs):
            return ('txt content', 0)

        test_registry.register(txt_renderer, file_patterns='txt')

        mock_command_loader = mock.MagicMock()
        mock_command_loader.return_value = mock.MagicMock()
        mock_command_loader.return_value.signal_bind = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result is None
        mock_command_loader.assert_called_once()
        actions.loader.add.assert_called_once()

    def test_plugin_with_exit_code_5_caches_result(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('cached content', 5)

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result == 'cached content'
        mock_command_loader.assert_not_called()
        actions.loader.add.assert_not_called()

    def test_plugin_with_exit_code_6_image_cache(self, temp_png_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_png_file, fake_scope_sh, fake_cache_dir
        )
        actions.settings.preview_images = True

        test_registry = PreviewPluginRegistry()

        def png_renderer(**kwargs):
            return (None, 6)

        test_registry.register(png_renderer, file_patterns='png')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
            preview_images=True,
        )

        expected_cache_path = os.path.join(fake_cache_dir, 'fake_hash')
        assert result == expected_cache_path
        mock_command_loader.assert_not_called()
        actions.loader.add.assert_not_called()
        mock_pager.set_image.assert_called_once_with(expected_cache_path)

    def test_plugin_with_exit_code_7_direct_image(self, temp_png_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_png_file, fake_scope_sh, fake_cache_dir
        )
        actions.settings.preview_images = True

        test_registry = PreviewPluginRegistry()

        def jpg_renderer(**kwargs):
            return (None, 7)

        test_registry.register(jpg_renderer, file_patterns='png')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
            preview_images=True,
        )

        assert result == temp_png_file
        mock_command_loader.assert_not_called()
        actions.loader.add.assert_not_called()
        mock_pager.set_image.assert_called_once_with(temp_png_file)

    def test_plugin_exception_falls_back_to_scope_sh(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def bad_renderer(**kwargs):
            raise RuntimeError('test error')

        test_registry.register(bad_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()
        mock_command_loader.return_value = mock.MagicMock()
        mock_command_loader.return_value.signal_bind = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result is None
        mock_command_loader.assert_called_once()
        actions.loader.add.assert_called_once()

    def test_multiple_plugins_first_delegates_second_handles(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()
        order_called = []

        def first(**kwargs):
            order_called.append('first')
            return None

        def second(**kwargs):
            order_called.append('second')
            return ('handled by second plugin', 0)

        test_registry.register(first, file_patterns='json', priority=10)
        test_registry.register(second, file_patterns='json', priority=5)

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result == 'handled by second plugin'
        mock_command_loader.assert_not_called()
        actions.loader.add.assert_not_called()
        assert order_called == ['first', 'second']

    def test_plugin_with_exit_code_0_success(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('success content', 0)

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result == 'success content'
        mock_command_loader.assert_not_called()

    def test_plugin_with_exit_code_1_no_preview(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return (None, 1)

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result is None
        mock_command_loader.assert_not_called()

    def test_plugin_with_exit_code_2_plain_text(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return (None, 2)

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result == 'file content'
        mock_command_loader.assert_not_called()
        actions.read_text_file.assert_called_once()

    def test_plugin_with_exit_code_3_fix_width(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('fixed width content', 3)

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result == 'fixed width content'
        mock_command_loader.assert_not_called()

    def test_plugin_with_exit_code_4_fix_height(self, temp_json_file, fake_scope_sh, fake_cache_dir):
        actions, fobj, mock_pager, mock_stat = self._create_mock_actions(
            temp_json_file, fake_scope_sh, fake_cache_dir
        )

        test_registry = PreviewPluginRegistry()

        def json_renderer(**kwargs):
            return ('fixed height content', 4)

        test_registry.register(json_renderer, file_patterns='json')

        mock_command_loader = mock.MagicMock()

        result = self._run_get_preview(
            actions,
            fobj,
            80,
            24,
            mock_stat,
            fake_cache_dir,
            test_registry=test_registry,
            mock_command_loader=mock_command_loader,
        )

        assert result == 'fixed height content'
        mock_command_loader.assert_not_called()
