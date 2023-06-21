from flask import Flask, render_template, Response, request
from flask_socketio import SocketIO, emit
import requests
import re

app = Flask(__name__)
socketio = SocketIO(app)

# Azure Blob Storage link for the movie
movie_url = "https://streamxonline.blob.core.windows.net/streamx/The.Hobbit.An.Unexpected.Journey.mp4"

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('sdp')
def handle_sdp(sdp):
    # Broadcast the SDP to other clients
    emit('sdp', sdp, broadcast=True, include_self=False)

@socketio.on('ice_candidate')
def handle_ice_candidate(candidate):
    # Broadcast the ICE candidate to other clients
    emit('ice_candidate', candidate, broadcast=True, include_self=False)

@app.route('/video')
def video():
    range_header = request.headers.get('Range', 'bytes=0-')
    size = None

    # Make a HEAD request to get the file size
    head_response = requests.head(movie_url)
    if 'Content-Length' in head_response.headers:
        size = int(head_response.headers['Content-Length'])

    # Parse range header
    byte1, byte2 = 0, None
    match = re.search('(\d+)-(\d*)', range_header)
    groups = match.groups()

    byte1 = int(groups[0])
    if groups[1]:
        byte2 = int(groups[1])

    if byte2 is None:
        byte2 = size - 1

    length = byte2 - byte1 + 1

    # Make a GET request to get the content
    headers = {'Range': f'bytes={byte1}-{byte2}'}
    response = requests.get(movie_url, headers=headers, stream=True)

    # Serve video stream
    def generate():
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    rv = Response(generate(), 206, mimetype='video/mp4')
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    rv.headers.add('Content-Length', str(length))

    return rv

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
