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

# Store scripts and transcriber instances
scripts = {}
transcribers = {}
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
    return jsonify({'status': 'success', 'session_id': session_id})

def handle_real_time_transcript(transcript, session_id):
    """Handle real-time transcript results"""
    if not transcript.text or session_id not in scripts:
        return
        
    # Get the words from the transcript and script
    transcript_words = [word.lower().strip('.,!?') for word in transcript.text.split()]
    script_words = [word.lower().strip('.,!?') for word in scripts[session_id]]
    
    if not transcript_words:
        return

    # Look for the longest matching sequence from the end of the transcript
    max_context_length = 3  # Number of words to match for context
    context_length = min(len(transcript_words), max_context_length)
    
    while context_length > 0:
        # Get the last N words from the transcript
        last_words = transcript_words[-context_length:]
        
        # Look for this sequence in the script
        for i in range(len(script_words) - context_length + 1):
            script_sequence = script_words[i:i + context_length]
            
            if last_words == script_sequence:
                # Found a match - the next word should be highlighted
                next_word_index = i + context_length
                
                if next_word_index < len(script_words):
                    socketio.emit('word_recognized', {'word_index': next_word_index}, room=session_id)
                return
                
        # If no match found with current context length, try with one word less
        context_length -= 1

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