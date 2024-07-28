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
    filename = f'{uuid.uuid4()}.mp4'
    ydl_opts = {
        'outtmpl': filename,
        'progress_hooks': [progress_hook],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return filename

def progress_hook(d):
    if d['status'] == 'downloading':
        percentage = d['_percent_str']
        socketio.emit('download_progress', {'percentage': percentage})

@app.route('/download', methods=['GET'])
def download_video():
    video_url = request.args.get('url')
    if not video_url:
        return "No URL provided", 400

    try:
        filename = download_video_with_progress(video_url)
        return send_file(filename, as_attachment=True, download_name=filename)
    except Exception as e:
        return str(e), 500
    finally:
        # Clean up the file after sending
        if 'filename' in locals():
            os.remove(filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
else:
    # This is for Gunicorn to use
    socketio.init_app(app)
