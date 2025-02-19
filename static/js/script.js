document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const scriptInput = document.getElementById('scriptInput');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const teleprompterDisplay = document.getElementById('teleprompterDisplay');
    
    let isRecording = false;
    let mediaRecorder = null;
    let audioStream = null;

    function log(message) {
        console.log(`[DEBUG] ${message}`);
    }

    function prepareScript(text) {
        log(`Preparing script text: ${text.substring(0, 100)}...`);
        const prepared = text.split(/\s+/).map((word, index) => {
            return `<span class="word" data-index="${index}">${word}</span>`;
        }).join(' ');
        log(`Script prepared with ${text.split(/\s+/).length} words`);
        return prepared;
    }

    async function startRecording() {
        try {
            log('Requesting microphone access...');
            audioStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            log('Microphone access granted');
            
            mediaRecorder = new MediaRecorder(audioStream);
            log(`MediaRecorder created with state: ${mediaRecorder.state}`);
            
            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0 && socket.connected) {
                    log(`Audio data available: ${event.data.size} bytes`);
                    // Convert blob to base64 and send to server
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64Audio = reader.result.split(',')[1];
                        log('Sending audio data to server');
                        socket.emit('audio_data', { audio: base64Audio });
                    };
                    reader.readAsDataURL(event.data);
                }
            };

            mediaRecorder.start(100); // Collect 100ms of audio at a time
            log('MediaRecorder started');
        } catch (err) {
            console.error('Error accessing microphone:', err);
            alert('Error accessing microphone. Please ensure you have granted microphone permissions.');
            stopRecording();
        }
    }

    function stopRecording() {
        log('Stopping recording...');
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            log('MediaRecorder stopped');
        }
        if (audioStream) {
            audioStream.getTracks().forEach(track => {
                track.stop();
                log('Audio track stopped');
            });
        }
        mediaRecorder = null;
        audioStream = null;
        log('Recording cleanup completed');
    }

    startButton.addEventListener('click', async () => {
        if (!scriptInput.value.trim()) {
            alert('Please enter some text first!');
            return;
        }

        const script = scriptInput.value;
        log('Start button clicked, preparing display');
        teleprompterDisplay.innerHTML = prepareScript(script);
        
        // Send script to backend
        log('Sending script to server');
        try {
            const response = await fetch('/upload-script', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ script: script })
            });
            const data = await response.json();
            log(`Script sent to server with session ID: ${data.session_id}`);

            isRecording = true;
            startButton.disabled = true;
            stopButton.disabled = false;
            
            // Start recording and emit event
            log('Starting recording process');
            await startRecording();
            socket.emit('start_recording');
            log('Start recording event emitted');
        } catch (error) {
            console.error('Error uploading script:', error);
            alert('Error uploading script. Please try again.');
        }
    });

    stopButton.addEventListener('click', () => {
        log('Stop button clicked');
        isRecording = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        
        stopRecording();
        socket.emit('stop_recording');
        log('Stop recording event emitted');
    });

    // Handle word recognition from backend
    socket.on('word_recognized', (data) => {
        log(`Word recognized event received with index: ${data.word_index}`);
        const words = teleprompterDisplay.getElementsByClassName('word');
        const currentIndex = data.word_index;
        
        Array.from(words).forEach((word, index) => {
            if (index < currentIndex) {
                word.classList.add('spoken-word');
                word.classList.remove('current-word', 'upcoming-word');
            } else if (index === currentIndex) {
                word.classList.add('current-word');
                word.classList.remove('spoken-word', 'upcoming-word');
                word.scrollIntoView({ behavior: 'smooth', block: 'center' });
                log(`Highlighted word at index ${index}: "${word.textContent}"`);
            } else {
                word.classList.add('upcoming-word');
                word.classList.remove('spoken-word', 'current-word');
            }
        });
    });

    // Handle transcription errors
    socket.on('transcription_error', (data) => {
        console.error('[DEBUG] Transcription error:', data.error);
        alert('Error with transcription service. Please try again.');
        stopRecording();
        startButton.disabled = false;
        stopButton.disabled = true;
    });

    // Handle connection events
    socket.on('connect', () => {
        log(`Connected to server with socket ID: ${socket.id}`);
    });

    socket.on('disconnect', () => {
        log('Disconnected from server');
        stopRecording();
        startButton.disabled = false;
        stopButton.disabled = true;
    });
}); 