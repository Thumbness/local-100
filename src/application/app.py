import os
import re
import json
import mimetypes
from ..config.AppConfig import APP_PARAMS
from flask import Flask, render_template, request, Response, send_from_directory, jsonify

app = Flask(__name__)

VIDEO_DIR = APP_PARAMS["COUNTDOWN.RESULTS.VIDEOS.DIRECTORY"]
RESULTS_FILE = APP_PARAMS["COUNTDOWN.RESULTS.DATA.FILEPATH"]

def ordinal(n):
    """Format an integer as an ordinal, e.g. 1 -> 1st, 112 -> 112th."""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def get_countdown_entries():
    """Load results ordered lowest-ranked first, skipping entries whose video is missing."""
    with open(RESULTS_FILE, encoding='utf-8') as f:
        results = json.load(f)["results"]

    entries = []
    for r in sorted(results, key=lambda r: r["rank"], reverse=True):
        filename = os.path.basename(r["video_file_location"])
        if not os.path.isfile(os.path.join(VIDEO_DIR, filename)):
            continue
        entries.append({
            "filename": filename,
            "title": r["title"],
            "artist": r["artist"],
            "rank": ordinal(r["rank"]),
            "points": r["points"],
            "voters": [
                {"name": v["name"], "position": ordinal(v["position"])}
                for v in r["voters"]
            ],
        })
    return entries

@app.route('/')
def index():
    entries = get_countdown_entries()
    return render_template('index.html', entries=entries)

@app.route('/video/<filename>')
def stream_video(filename):
    """Serve video with Range support for seeking."""
    video_path = os.path.join(VIDEO_DIR, filename)

    if not os.path.exists(video_path) or not os.path.isfile(video_path):
        return "Video not found", 404

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)

    if not range_header:
        return send_from_directory(VIDEO_DIR, filename)

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
    app.run(host='0.0.0.0', port=5000, debug=True)   