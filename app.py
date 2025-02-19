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
    print(f"[DEBUG] Uploaded script for session {session_id}")
    print(f"[DEBUG] Script words: {words}")
    return jsonify({'status': 'success', 'session_id': session_id})

def handle_real_time_transcript(transcript, session_id):
    """Handle real-time transcript results"""
    if not transcript.text:
        print(f"[DEBUG] Empty transcript received for session {session_id}")
        return
        
    if session_id not in scripts:
        print(f"[DEBUG] No script found for session {session_id}")
        return
        
    print(f"[DEBUG] Received transcript for session {session_id}: {transcript.text}")
    
    # Get the words from the transcript and script
    transcript_words = transcript.text.lower().split()
    script_words = [word.lower() for word in scripts[session_id]]
    
    print(f"[DEBUG] Transcript words: {transcript_words}")
    print(f"[DEBUG] Script words: {script_words}")
    
    if not transcript_words:
        print("[DEBUG] No words in transcript")
        return
        
    # Get the last word from the transcript
    last_word = transcript_words[-1]
    print(f"[DEBUG] Looking for match for last word: '{last_word}'")
    
    # Find matching words in the script
    for i, script_word in enumerate(script_words):
        print(f"[DEBUG] Comparing '{last_word}' with script word '{script_word}'")
        if last_word == script_word:
            print(f"[DEBUG] Found match at index {i}: '{script_word}'")
            socketio.emit('word_recognized', {'word_index': i}, room=session_id)
            break

@socketio.on('connect')
def handle_connect():
    global current_sid
    current_sid = request.sid
    print(f"[DEBUG] Client connected: {current_sid}")

@socketio.on('disconnect')
def handle_disconnect():
    global current_sid
    session_id = request.sid
    print(f"[DEBUG] Client disconnecting: {session_id}")
    if session_id in transcribers:
        transcribers[session_id].close()
        del transcribers[session_id]
    if session_id in scripts:
        del scripts[session_id]
    if current_sid == session_id:
        current_sid = None
    print(f"[DEBUG] Client disconnected and cleaned up: {session_id}")

@socketio.on('start_recording')
def handle_start_recording():
    session_id = request.sid
    print(f"[DEBUG] Starting recording for session: {session_id}")
    
    if session_id not in scripts:
        print(f"[DEBUG] No script found for session {session_id}")
        return

    def on_data(transcript):
        print(f"[DEBUG] Received data from AssemblyAI for session {session_id}")
        handle_real_time_transcript(transcript, session_id)

    def on_error(error):
        print(f"[DEBUG] Error in transcription for session {session_id}: {error}")
        socketio.emit('transcription_error', {'error': str(error)}, room=session_id)

    def on_open(session_opened):
        print(f"[DEBUG] AssemblyAI session opened: {session_opened.session_id}")

    def on_close():
        print(f"[DEBUG] AssemblyAI session closed for {session_id}")

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
        print(f"[DEBUG] Starting microphone stream for session {session_id}")
        transcriber.stream(microphone_stream)
        print(f"[DEBUG] Microphone stream started for session {session_id}")
    except Exception as e:
        print(f"[DEBUG] Error setting up transcription: {str(e)}")
        socketio.emit('transcription_error', {'error': str(e)}, room=session_id)

@socketio.on('stop_recording')
def handle_stop_recording():
    session_id = request.sid
    print(f"[DEBUG] Stopping recording for session: {session_id}")
    if session_id in transcribers:
        transcribers[session_id].close()
        del transcribers[session_id]
        print(f"[DEBUG] Transcriber closed and removed for session: {session_id}")

@socketio.on('audio_data')
def handle_audio_data(data):
    session_id = request.sid
    if session_id not in scripts:
        print(f"[DEBUG] Received audio data but no script found for session {session_id}")
    else:
        print(f"[DEBUG] Received audio data from client {session_id}")

if __name__ == '__main__':
    socketio.run(app, debug=True) 