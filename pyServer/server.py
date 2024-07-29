import eventlet
eventlet.monkey_patch()

from flask import Flask, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from yt_dlp import YoutubeDL
import tempfile
import os
import uuid

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

def download_video_with_progress(video_url):
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f'{uuid.uuid4()}.mp4')

    ydl_opts = {
        'outtmpl': filename,
        'progress_hooks': [progress_hook],
        'format': 'best',
        'merge_output_format': 'mp4',
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
        return "No URL providedd", 400

    filename = download_video_with_progress(video_url)
    response = send_file(filename, as_attachment=True)

    # Ensure the file is removed after it is sent to the client
    response.call_on_close(lambda: os.remove(filename))

    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
