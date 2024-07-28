from flask import Flask, request, send_file, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from yt_dlp import YoutubeDL
import os
import uuid
import tempfile

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Backend functions

def download_video_with_progress(video_url, output_path):
    filename = os.path.join(output_path, f'{uuid.uuid4()}.mp4')
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

    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            filename = download_video_with_progress(video_url, tmpdirname)
            return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))
        except Exception as e:
            app.logger.error(f"Error downloading video: {str(e)}")
            return str(e), 500

@app.route('/stream', methods=['GET'])
def stream_video():
    video_url = request.args.get('url')
    if not video_url:
        return "No URL provided", 400

    def generate():
        ydl_opts = {
            'format': 'best',
            'outtmpl': '-',
        }
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(video_url, download=False)
            for chunk in ydl.download_with_info_file(result):
                yield chunk

    return Response(generate(), mimetype='video/mp4')

# Frontend (served as a string, not ideal for production)
@app.route('/')
def serve_frontend():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Downloader</title>
        <script src="https://unpkg.com/react@17/umd/react.development.js"></script>
        <script src="https://unpkg.com/react-dom@17/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/babel-standalone@6/babel.min.js"></script>
        <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    </head>
    <body>
        <div id="root"></div>
        <script type="text/babel">
            function App() {
                const [videoUrl, setVideoUrl] = React.useState('');
                const [isLoading, setIsLoading] = React.useState(false);
                const [downloadProgress, setDownloadProgress] = React.useState(null);
                const [error, setError] = React.useState(null);

                React.useEffect(() => {
                    const socket = io();
                    socket.on('download_progress', (data) => {
                        setDownloadProgress(data.percentage);
                    });
                    return () => socket.disconnect();
                }, []);

                const handleDownload = async () => {
                    setIsLoading(true);
                    setError(null);

                    try {
                        const response = await axios.get('/download', {
                            params: { url: videoUrl },
                            responseType: 'blob',
                        });

                        const url = window.URL.createObjectURL(new Blob([response.data]));
                        const link = document.createElement('a');
                        link.href = url;
                        link.setAttribute('download', 'video.mp4');
                        document.body.appendChild(link);
                        link.click();
                        link.remove();
                    } catch (err) {
                        setError('Error downloading video: ' + err.message);
                    } finally {
                        setIsLoading(false);
                        setDownloadProgress(null);
                    }
                };

                return (
                    <div className="App">
                        <header className="App-header">
                            <h1>Download Video</h1>
                            <input
                                type="text"
                                value={videoUrl}
                                onChange={(e) => setVideoUrl(e.target.value)}
                                placeholder="Enter video URL"
                            />
                            <button onClick={handleDownload} disabled={isLoading}>
                                {isLoading ? 'Downloading...' : 'Download'}
                            </button>
                            {downloadProgress && <p>Download Progress: {downloadProgress}</p>}
                            {error && <p>{error}</p>}
                        </header>
                    </div>
                );
            }

            ReactDOM.render(<App />, document.getElementById('root'));
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
else:
    # This is for Gunicorn to use
    socketio.init_app(app)
