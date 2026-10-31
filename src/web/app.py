import mimetypes
import os
import re
import secrets
from datetime import timedelta

from flask import Flask, Response, redirect, render_template, request, send_from_directory, url_for

from urllib.parse import urlparse

from werkzeug.middleware.proxy_fix import ProxyFix

from ..composition import countdown_service
from ..infrastructure.spotify.auth import configured_redirect_uri
from .auth import install_auth
from .library import callback as spotify_callback, library_bp
from .presenters import countdown_view
from .upload import upload_bp

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",  # the browser won't send the login cookie on cross-site POSTs (CSRF)
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "").lower() in ("1", "true", "yes"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

# Behind a reverse proxy (Caddy, a load balancer), trust its forwarded address so the login lockout sees the
# real client. Set TRUSTED_PROXY_HOPS to the number of proxies in front of the app; leave it 0 otherwise.
_proxy_hops = int(os.getenv("TRUSTED_PROXY_HOPS", "0") or 0)
if _proxy_hops:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_proxy_hops, x_proto=_proxy_hops, x_host=_proxy_hops)

install_auth(app)  # everything needs a login except the login page, /healthz and static files
app.register_blueprint(library_bp)
app.register_blueprint(upload_bp)
# Also answer at /callback, so a redirect URI like http://127.0.0.1:8888/callback works
app.add_url_rule('/callback', endpoint='oauth_callback', view_func=spotify_callback)


@app.route('/healthz')
def healthz():
    """For load balancer and container health checks. Public, and touches nothing."""
    return 'ok'


@app.route('/')
def home():
    return render_template('home.html', error=request.args.get('error'), notice=request.args.get('notice'))


@app.route('/countdown')
def countdown():
    service = countdown_service()
    report = service.validate()
    if not report['ok']:
        return redirect(url_for('home', error=report['message']))

    entries = [countdown_view(p) for p in service.playable_entries()]
    image_directory = os.path.join(app.static_folder, "images")
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    image_urls = [
        url_for("static", filename=f"images/{filename}")
        for filename in sorted(os.listdir(image_directory))
        if os.path.isfile(os.path.join(image_directory, filename))
        and os.path.splitext(filename)[1].lower() in image_extensions
    ] if os.path.isdir(image_directory) else []
    return render_template('index.html', entries=entries, image_urls=image_urls)


@app.route('/video/<filename>')
def stream_video(filename):
    """Serve video with Range support for seeking."""
    service = countdown_service()
    video_path = service.video_path(filename)
    if video_path is None:
        return "Video not found", 404

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)

    if not range_header:
        return send_from_directory(service.videos_dir, filename)

    # Parse "bytes=start-end"
    match = re.search(r'bytes=(\d+)-(\d*)', range_header)
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else file_size - 1
    end = min(end, file_size - 1)

    if start >= file_size:
        return "file size range error", 416

    chunk_size = end - start + 1
    with open(video_path, 'rb') as f:
        f.seek(start)
        data = f.read(chunk_size)

    mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(chunk_size),
        'Content-Type': mime_type
    }
    return Response(data, status=206, headers=headers, direct_passthrough=True)


if __name__ == '__main__':
    # Listen where Spotify redirects users after login
    port = urlparse(configured_redirect_uri()).port or 5000
    app.run(host='0.0.0.0', port=port, debug=True)
