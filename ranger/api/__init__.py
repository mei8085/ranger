# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

"""Files in this module contain helper functions used in configuration files."""

from __future__ import (absolute_import, division, print_function)

import ranger
from ranger.core.linemode import LinemodeBase


__all__ = [
    'ranger',
    'LinemodeBase',
    'hook_init',
    'hook_ready',
    'register_linemode',
    'register_preview_plugin',
    'unregister_preview_plugin',
]


# Hooks for use in plugins:
def hook_init(fm):  # pylint: disable=unused-argument
    """A hook that is called when ranger starts up.

    Parameters:
      fm = the file manager instance
    Return Value:
      ignored

    This hook is executed after fm is initialized but before fm.ui is
    initialized.  You can safely print to stdout and have access to fm to add
    keybindings and such.
    """


def hook_ready(fm):  # pylint: disable=unused-argument
    """A hook that is called after the ranger UI is initialized.

    Parameters:
      fm = the file manager instance
    Return Value:
      ignored

    This hook is executed after the user interface is initialized.  You should
    NOT print anything anymore from here on.  Use fm.notify instead.
    """


def register_linemode(linemode_class):
    """Add a custom linemode class.  See ranger.core.linemode"""
    from ranger.container.fsobject import FileSystemObject
    FileSystemObject.linemode_dict[linemode_class.name] = linemode_class()
    return linemode_class


def register_preview_plugin(file_patterns=None, mime_types=None, priority=0):
    """Register a preview plugin.

    This decorator registers a function that generates file previews in Python.
    The plugin will be checked before scope.sh is called.

    Parameters:
      file_patterns: A string or list of strings, representing file extensions
          or glob patterns to match. Examples: 'json', '.py', '*.txt', 'test*'
      mime_types: A string or list of strings, representing MIME types or
          glob patterns to match. Examples: 'application/json', 'text/*'
      priority: Integer priority value. Higher priority renderers are tried first.

    The decorated function should have the following signature:

        def my_renderer(file_path, width, height, image_cache_path, preview_images):
            '''
            Args:
                file_path: Full path to the file
                width: Width of the preview pane (characters)
                height: Height of the preview pane (characters)
                image_cache_path: Path for caching image previews
                preview_images: True if image previews are enabled

            Returns:
                None if this renderer cannot handle the file (try next one)
                Or a tuple (content, exit_code) where:
                    content: The preview content as a string (or None for images)
                    exit_code: Same as scope.sh exit codes:
                        0: success, display content
                        1: no preview
                        2: plain text, display file content directly
                        3: fix width (don't reload on width change)
                        4: fix height (don't reload on height change)
                        5: fix both (don't reload)
                        6: image preview (use image_cache_path)
                        7: direct image preview (use file_path)
            '''
            return (content, exit_code)  # or None

    Example usage:

        @register_preview_plugin(file_patterns='json')
        def json_preview(file_path, width, height, image_cache_path, preview_images):
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
            return (json.dumps(data, indent=2), 0)
    """
    from ranger.core.preview_plugin import register_preview_plugin as _register
    return _register(file_patterns=file_patterns, mime_types=mime_types, priority=priority)


def unregister_preview_plugin(func):
    """Unregister a preview plugin.

    Parameters:
      func: The function that was previously registered
    """
    from ranger.core.preview_plugin import unregister_preview_plugin as _unregister
    _unregister(func)
