from flask import Flask, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from yt_dlp import YoutubeDL
import os
import uuid

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

def download_video_with_progress(video_url):
    ydl_opts = {
        'outtmpl': f'{uuid.uuid4()}.%(ext)s',
        'progress_hooks': [progress_hook],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info)

    return filename

def progress_hook(d):
    if d['status'] == 'downloading':
        percentage = d['_percent_str']
        socketio.emit('download_progress', {'percentage': percentage})

@app.route('/', methods=['GET'])
def download_video():
    video_url = request.args.get('url')
    if not video_url:
        return "No URL provided", 400

    filename = download_video_with_progress(video_url)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
