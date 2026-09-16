"""Rebuild the exact-order JS bundle and precompress text assets (no dependencies).

Run after changing static sources: python build_assets.py
CSS, animation keyframes, and vendor files are not rewritten or minified.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re

STATIC = Path(__file__).resolve().parent / 'static'
JS_SOURCES = ('app.js', 'motion_frame.js', 'cinematic.js', 'site_motion.js',
              'peak_v9.js', 'peak_v11.js', 'final.js')


def build():
    bundle = '\n'.join((STATIC/'js'/name).read_text(encoding='utf-8') for name in JS_SOURCES)
    (STATIC/'js/farmdirect-core.bundle.js').write_text(bundle, encoding='utf-8', newline='\n')
    assets = {}
    for path in sorted(STATIC.rglob('*')):
        if not path.is_file() or path.suffix == '.gz' or path.name in {'asset-manifest.json', 'sw.js'}:
            continue
        data = path.read_bytes()
        assets[path.relative_to(STATIC).as_posix()] = hashlib.sha256(data).hexdigest()[:16]
        if path.suffix in {'.css', '.js', '.svg', '.html', '.webmanifest'}:
            # Reproducible bytes, paid once at build time, never during requests.
            compressed = gzip.compress(data, compresslevel=9, mtime=0)
            if len(compressed) < len(data):
                path.with_name(path.name + '.gz').write_bytes(compressed)
    version = hashlib.sha256(json.dumps(assets, sort_keys=True).encode()).hexdigest()[:16]
    (STATIC/'asset-manifest.json').write_text(
        json.dumps({'version': version, 'assets': assets}, indent=2) + '\n', encoding='utf-8')
    worker = STATIC/'sw.js'
    source = re.sub(r"const VERSION = '[^']+';", f"const VERSION = '{version}';", worker.read_text(encoding='utf-8'))
    worker.write_text(source, encoding='utf-8', newline='\n')
    print(f'Built {len(assets)} assets; release {version}')


if __name__ == '__main__':
    build()
