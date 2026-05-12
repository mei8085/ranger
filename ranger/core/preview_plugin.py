# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

from collections import defaultdict
from fnmatch import fnmatch
import logging
import mimetypes


LOG = logging.getLogger(__name__)


class PreviewPluginRegistry(object):
    def __init__(self):
        self._by_extension = defaultdict(list)
        self._by_mimetype = defaultdict(list)
        self._by_extension_pattern = []
        self._by_mimetype_pattern = []

    def register(self, renderer, file_patterns=None, mime_types=None, priority=0):
        if file_patterns:
            if isinstance(file_patterns, str):
                file_patterns = [file_patterns]
            for pattern in file_patterns:
                if '*' in pattern or '?' in pattern:
                    self._by_extension_pattern.append((pattern, renderer, priority))
                else:
                    ext = pattern.lstrip('.').lower()
                    self._by_extension[ext].append((renderer, priority))
        if mime_types:
            if isinstance(mime_types, str):
                mime_types = [mime_types]
            for mime_type in mime_types:
                if '*' in mime_type or '?' in mime_type:
                    self._by_mimetype_pattern.append((mime_type, renderer, priority))
                else:
                    self._by_mimetype[mime_type].append((renderer, priority))

    def unregister(self, renderer):
        for ext in list(self._by_extension.keys()):
            self._by_extension[ext] = [(r, p) for r, p in self._by_extension[ext] if r is not renderer]
            if not self._by_extension[ext]:
                del self._by_extension[ext]
        for mime in list(self._by_mimetype.keys()):
            self._by_mimetype[mime] = [(r, p) for r, p in self._by_mimetype[mime] if r is not renderer]
            if not self._by_mimetype[mime]:
                del self._by_mimetype[mime]
        self._by_extension_pattern = [(p, r, pr) for p, r, pr in self._by_extension_pattern if r is not renderer]
        self._by_mimetype_pattern = [(p, r, pr) for p, r, pr in self._by_mimetype_pattern if r is not renderer]

    def _guess_mimetype(self, path):
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type

    def get_renderers(self, path):
        renderers = []

        basename = path.lower()
        for pattern, renderer, priority in self._by_extension_pattern:
            if fnmatch(basename, pattern.lower()):
                renderers.append((renderer, priority))

        ext = basename.split('.')[-1] if '.' in basename else ''
        if ext:
            for renderer, priority in self._by_extension.get(ext, []):
                renderers.append((renderer, priority))

        mime_type = self._guess_mimetype(path)
        if mime_type:
            for pattern, renderer, priority in self._by_mimetype_pattern:
                if fnmatch(mime_type, pattern):
                    renderers.append((renderer, priority))
            for renderer, priority in self._by_mimetype.get(mime_type, []):
                renderers.append((renderer, priority))

        renderers.sort(key=lambda x: -x[1])
        return [r for r, _ in renderers]

    def render(self, path, width, height, image_cache_path, preview_images):
        for renderer in self.get_renderers(path):
            try:
                result = renderer(
                    file_path=path,
                    width=width,
                    height=height,
                    image_cache_path=image_cache_path,
                    preview_images=preview_images,
                )
                if result is not None:
                    return result
            except Exception:
                LOG.exception("Error in preview renderer for %s", path)
        return None


preview_plugin_registry = PreviewPluginRegistry()


def register_preview_plugin(file_patterns=None, mime_types=None, priority=0):
    def decorator(func):
        preview_plugin_registry.register(func, file_patterns=file_patterns, mime_types=mime_types, priority=priority)
        return func
    return decorator


def unregister_preview_plugin(func):
    preview_plugin_registry.unregister(func)
