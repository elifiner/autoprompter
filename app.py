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
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

# Initialize AssemblyAI
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

# Store scripts, transcribers, and reading positions
scripts = {}
transcribers = {}
current_positions = {}  # Track current reading position for each session
current_sid = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-script', methods=['POST'])
def upload_script():
    script = request.json.get('script', '')
    session_id = current_sid if current_sid else 'default'
    words = script.split()
    scripts[session_id] = words
    current_positions[session_id] = 0  # Initialize reading position
    return jsonify({'status': 'success', 'session_id': session_id})

def handle_real_time_transcript(transcript, session_id):
    """Handle real-time transcript results using sequential reading assumption"""
    if not transcript.text or session_id not in scripts:
        return

    # Get the words from the transcript and script
    transcript_words = [word.lower().strip('.,!?') for word in transcript.text.split()]
    script_words = [word.lower().strip('.,!?') for word in scripts[session_id]]
    
    if not transcript_words:
        return

    current_pos = current_positions.get(session_id, 0)
    
    # Define the look-ahead window
    LOOK_AHEAD = 15  # Number of words to look ahead
    search_start = max(0, current_pos - 2)  # Allow small backtrack
    search_end = min(len(script_words), current_pos + LOOK_AHEAD)
    
    # Get the last spoken word
    last_word = transcript_words[-1].lower().strip('.,!?')
    
    # First, try exact match within window
    for i in range(search_start, search_end):
        if script_words[i] == last_word:
            # Found exact match
            current_positions[session_id] = i + 1
            socketio.emit('word_recognized', {'word_index': i + 1}, room=session_id)
            return
    
    # If no exact match, try fuzzy match (first 3 chars match)
    if len(last_word) >= 3:
        for i in range(search_start, search_end):
            if script_words[i].startswith(last_word[:3]):
                current_positions[session_id] = i + 1
                socketio.emit('word_recognized', {'word_index': i + 1}, room=session_id)
                return
    
    # If still no match, try matching two-word sequences
    if len(transcript_words) >= 2:
        last_two_words = ' '.join(transcript_words[-2:]).lower()
        script_pairs = [f"{script_words[i]} {script_words[i+1]}" for i in range(search_start, search_end-1)]
        
        for i, pair in enumerate(script_pairs):
            if pair == last_two_words:
                current_positions[session_id] = search_start + i + 2
                socketio.emit('word_recognized', {'word_index': search_start + i + 2}, room=session_id)
                return

@socketio.on('connect')
def handle_connect():
    global current_sid
    current_sid = request.sid

@socketio.on('disconnect')
def handle_disconnect():
    global current_sid
    session_id = request.sid
    if session_id in transcribers:
        transcribers[session_id].close()
        del transcribers[session_id]
    if session_id in scripts:
        del scripts[session_id]
    if session_id in current_positions:
        del current_positions[session_id]
    if current_sid == session_id:
        current_sid = None

@socketio.on('start_recording')
def handle_start_recording():
    session_id = request.sid
    
    if session_id not in scripts:
        return

    def on_data(transcript):
        handle_real_time_transcript(transcript, session_id)

    def on_error(error):
        socketio.emit('transcription_error', {'error': str(error)}, room=session_id)

    def on_open(session_opened):
        pass

    def on_close():
        pass

    try:
        transcriber = aai.RealtimeTranscriber(
            sample_rate=16000,  # Using recommended medium quality sample rate
            on_data=on_data,
            on_error=on_error,
            on_open=on_open,
            on_close=on_close,
        )
        
        transcribers[session_id] = transcriber
        transcriber.connect()

        # Start microphone stream with matching sample rate
        microphone_stream = aai.extras.MicrophoneStream(sample_rate=16000)
        transcriber.stream(microphone_stream)
    except Exception as e:
        socketio.emit('transcription_error', {'error': str(e)}, room=session_id)

@socketio.on('stop_recording')
def handle_stop_recording():
    session_id = request.sid
    if session_id in transcribers:
        transcribers[session_id].close()
        del transcribers[session_id]

@socketio.on('audio_data')
def handle_audio_data(data):
    pass  # Audio data is handled by AssemblyAI's stream

if __name__ == '__main__':
    socketio.run(app, debug=True) 