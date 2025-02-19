from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO
import os
import assemblyai as aai
from dotenv import load_dotenv
import asyncio
import json
from threading import Thread

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize AssemblyAI
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

# Store scripts and transcriber instances
scripts = {}
transcribers = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-script', methods=['POST'])
def upload_script():
    script = request.json.get('script', '')
    session_id = request.sid if hasattr(request, 'sid') else 'default'
    scripts[session_id] = script.split()
    return jsonify({'status': 'success'})

def handle_real_time_transcript(transcript, session_id):
    """Handle real-time transcript results"""
    if transcript.text and session_id in scripts:
        words = transcript.text.split()
        script_words = scripts[session_id]
        
        # Find matching words in the script
        for i, script_word in enumerate(script_words):
            if i < len(words) and words[-1].lower() == script_word.lower():
                socketio.emit('word_recognized', {'word_index': i}, room=session_id)
                break

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in transcribers:
        transcribers[session_id].close()
        del transcribers[session_id]
    if session_id in scripts:
        del scripts[session_id]
    print(f"Client disconnected: {session_id}")

@socketio.on('start_recording')
def handle_start_recording():
    session_id = request.sid
    
    def transcript_handler(transcript):
        handle_real_time_transcript(transcript, session_id)

    def error_handler(error):
        print(f"Error in transcription: {error}")
        socketio.emit('transcription_error', {'error': str(error)}, room=session_id)

    transcriber = aai.Transcriber(
        on_data=transcript_handler,
        on_error=error_handler,
        sample_rate=44_100,
    )
    
    transcribers[session_id] = transcriber
    transcriber.connect()

    # Start microphone stream
    microphone_stream = aai.extras.MicrophoneStream()
    transcriber.stream(microphone_stream)

@socketio.on('stop_recording')
def handle_stop_recording():
    session_id = request.sid
    if session_id in transcribers:
        transcribers[session_id].close()
        del transcribers[session_id]

if __name__ == '__main__':
    socketio.run(app, debug=True) 