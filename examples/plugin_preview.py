from __future__ import (absolute_import, division, print_function)

import json

import ranger.api


@ranger.api.register_preview_plugin(file_patterns='json')
def json_preview(file_path, width, height, image_cache_path, preview_images):
    """Pretty-print JSON files with Python's json module."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return (json.dumps(data, indent=2, ensure_ascii=False), 0)
    except (IOError, ValueError):
        return None


@ranger.api.register_preview_plugin(file_patterns=['yaml', 'yml'])
def yaml_preview(file_path, width, height, image_cache_path, preview_images):
    """Preview YAML files using PyYAML if available."""
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return (json.dumps(data, indent=2, default=str), 0)
    except (IOError, yaml.YAMLError):
        return None


@ranger.api.register_preview_plugin(mime_types='text/*', priority=-10)
def text_file_info(file_path, width, height, image_cache_path, preview_images):
    """Low-priority fallback for text files: show line count."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        return ('Line count: %d\n\nFirst 10 lines:\n%s' % (
            len(lines),
            ''.join(lines[:10])
        ), 5)
    except IOError:
        return None
