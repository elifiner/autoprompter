document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const teleprompterDisplay = document.getElementById('teleprompterDisplay');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const fontSizeSlider = document.getElementById('fontSize');
    const fontSizeValue = document.getElementById('fontSizeValue');
    const textWidthSlider = document.getElementById('textWidth');
    const textWidthValue = document.getElementById('textWidthValue');

    // Initial instructions text
    const INSTRUCTIONS_TEXT = `Welcome to Auto Teleprompter!

Simply select and replace this text with your script.

Tips:
• Adjust the font size and width using the sliders below
• Click 'Start' when ready to begin
• Speak naturally - the text will automatically scroll
• The current word will be highlighted in yellow
• Click 'Stop' when finished

Try it now by selecting this text and pasting your script!`;
    
    let isRecording = false;

    function formatText(text, shouldWrapWords = false) {
        // Split into paragraphs, trim each one, and remove empty ones
        const paragraphs = text.split(/\n+/).map(p => p.trim()).filter(p => p);
        
        const formattedParagraphs = paragraphs.map(paragraph => {
            if (shouldWrapWords) {
                // For recording mode: wrap words in spans
                const words = paragraph.split(/\s+/).map((word, index) => {
                    return `<span class="word" data-index="${index}">${word}</span>`;
                }).join(' ');
                return `<div class="paragraph">${words}</div>`;
            } else {
                // For editing mode: just wrap paragraphs
                return `<div class="paragraph">${paragraph}</div>`;
            }
        });

        // Join with newlines and preserve them in HTML
        return formattedParagraphs.join('\n');
    }

    // Initialize with formatted instructions
    teleprompterDisplay.innerHTML = formatText(INSTRUCTIONS_TEXT);

    // Handle font size changes
    fontSizeSlider.addEventListener('input', () => {
        const size = fontSizeSlider.value;
        fontSizeValue.textContent = `${size}px`;
        teleprompterDisplay.style.fontSize = `${size}px`;
    });

    // Handle width changes
    textWidthSlider.addEventListener('input', () => {
        const width = textWidthSlider.value;
        textWidthValue.textContent = `${width}px`;
        teleprompterDisplay.style.width = `${width}px`;
    });

    startButton.addEventListener('click', async () => {
        // Get raw text and split into paragraphs, handling any nested structure
        const rawText = teleprompterDisplay.innerText.trim();
        const text = rawText.split(/\n+/).map(p => p.trim()).filter(p => p).join('\n\n');
        
        if (!text || text === INSTRUCTIONS_TEXT.trim()) {
            alert('Please replace the instructions with your script first!');
            return;
        }

        // Make teleprompter uneditable during recording
        teleprompterDisplay.contentEditable = 'false';
        teleprompterDisplay.innerHTML = formatText(text, true); // true for word wrapping
        
        // Send script to backend
        try {
            const response = await fetch('/upload-script', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ script: text })
            });
            await response.json();

            isRecording = true;
            startButton.disabled = true;
            stopButton.disabled = false;
            
            socket.emit('start_recording');
        } catch (error) {
            console.error('Error uploading script:', error);
            alert('Error uploading script. Please try again.');
            teleprompterDisplay.contentEditable = 'true';
            teleprompterDisplay.innerHTML = formatText(text); // Restore original formatting
        }
    });

    stopButton.addEventListener('click', () => {
        isRecording = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        teleprompterDisplay.contentEditable = 'true';
        
        // Restore original formatting without word wrapping
        const text = teleprompterDisplay.textContent.trim();
        teleprompterDisplay.innerHTML = formatText(text);
        
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
                
                // Scroll the current word to top with offset
                const wordTop = word.offsetTop;
                const containerHeight = teleprompterDisplay.clientHeight;
                const scrollPosition = wordTop - 100; // 100px from top
                teleprompterDisplay.scrollTo({
                    top: scrollPosition,
                    behavior: 'smooth'
                });
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
        startButton.disabled = false;
        stopButton.disabled = true;
        teleprompterDisplay.contentEditable = 'true';
    });

    // Handle connection events
    socket.on('connect', () => {
        // Connection established
    });

    socket.on('disconnect', () => {
        startButton.disabled = false;
        stopButton.disabled = true;
        teleprompterDisplay.contentEditable = 'true';
    });
}); 