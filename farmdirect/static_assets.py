"""Serve precompressed assets and version their URLs without runtime compression."""
import json
import mimetypes
from pathlib import Path

from flask import request, send_from_directory
from werkzeug.utils import safe_join


def install_static_assets(app):
    folder = Path(app.static_folder)
    manifest_path = folder / 'asset-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    version = manifest.get('version')
    app.config['FD_ASSET_VERSION'] = version

    @app.url_defaults
    def version_static_url(endpoint, values):
        if endpoint == 'static' and version:
            values.setdefault('v', version)

    def send_asset(filename):
        path = safe_join(str(folder), filename)
        source = Path(path) if path else None
        compressed = Path(path + '.gz') if path else None
        use_gzip = bool(
            source and source.is_file() and compressed.is_file()
            and compressed.stat().st_mtime_ns >= source.stat().st_mtime_ns
            and request.accept_encodings['gzip'] > 0
            and request.accept_encodings['gzip'] >= request.accept_encodings['identity']
        )
        versioned = bool(version and request.args.get('v') == version)
        max_age = 31536000 if versioned else app.get_send_file_max_age(filename)
        response = send_from_directory(
            app.static_folder, filename + '.gz' if use_gzip else filename,
            mimetype=mimetypes.guess_type(filename)[0] or 'application/octet-stream',
            conditional=True, max_age=max_age,
        )
        response.vary.add('Accept-Encoding')
        if use_gzip:
            response.headers['Content-Encoding'] = 'gzip'
        if versioned:
            response.cache_control.immutable = True
        return response

    app.view_functions['static'] = send_asset
