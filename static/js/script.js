document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const scriptInput = document.getElementById('scriptInput');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const teleprompterDisplay = document.getElementById('teleprompterDisplay');
    
    let isRecording = false;
    let mediaRecorder = null;
    let audioStream = null;

    function prepareScript(text) {
        return text.split(/\s+/).map((word, index) => {
            return `<span class="word" data-index="${index}">${word}</span>`;
        }).join(' ');
    }

    async function startRecording() {
        try {
            audioStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 44100,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            mediaRecorder = new MediaRecorder(audioStream);
            
            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0 && socket.connected) {
                    // Convert blob to base64 and send to server
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64Audio = reader.result.split(',')[1];
                        socket.emit('audio_data', { audio: base64Audio });
                    };
                    reader.readAsDataURL(event.data);
                }
            };

            mediaRecorder.start(100); // Collect 100ms of audio at a time
        } catch (err) {
            console.error('Error accessing microphone:', err);
            alert('Error accessing microphone. Please ensure you have granted microphone permissions.');
            stopRecording();
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        if (audioStream) {
            audioStream.getTracks().forEach(track => track.stop());
        }
        mediaRecorder = null;
        audioStream = null;
    }

    startButton.addEventListener('click', async () => {
        if (!scriptInput.value.trim()) {
            alert('Please enter some text first!');
            return;
        }

        const script = scriptInput.value;
        teleprompterDisplay.innerHTML = prepareScript(script);
        
        // Send script to backend
        await fetch('/upload-script', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ script: script })
        });

        isRecording = true;
        startButton.disabled = true;
        stopButton.disabled = false;
        
        // Start recording and emit event
        await startRecording();
        socket.emit('start_recording');
    });

    stopButton.addEventListener('click', () => {
        isRecording = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        
        stopRecording();
        socket.emit('stop_recording');
    });

    // Handle word recognition from backend
    socket.on('word_recognized', (data) => {
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
            } else {
                word.classList.add('upcoming-word');
                word.classList.remove('spoken-word', 'current-word');
            }
        });
    });

    // Handle transcription errors
    socket.on('transcription_error', (data) => {
        console.error('Transcription error:', data.error);
        alert('Error with transcription service. Please try again.');
        stopRecording();
        startButton.disabled = false;
        stopButton.disabled = true;
    });

    // Handle connection events
    socket.on('connect', () => {
        console.log('Connected to server');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        stopRecording();
        startButton.disabled = false;
        stopButton.disabled = true;
    });
}); 