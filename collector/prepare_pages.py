"""Normalize a basePath-prefixed static export for GitHub Pages artifact roots.

Pages already mounts the artifact at /repository/. Vinext emits that prefix as
an on-disk directory as well, so unwrap it while preserving URL prefixes.
"""
import os
from pathlib import Path
import shutil

root = Path('dist/client')
base = os.environ.get('PAGES_BASE_PATH', '').strip('/')
if base:
    parts = Path(base).parts
    if any(part in ('.','..') for part in parts):
        raise ValueError('Unsafe Pages base path')
    nested = root.joinpath(*parts)
    if (nested / 'index.html').exists():
        for child in list(nested.iterdir()):
            target = root / child.name
            if target.exists():
                raise ValueError(f'Unexpected export collision: {target}')
            shutil.move(str(child), str(target))
        nested.rmdir()
if not (root / 'index.html').exists():
    raise ValueError('No static homepage was generated')
(root / '.nojekyll').touch()
print('Prepared static artifact for GitHub Pages.')
