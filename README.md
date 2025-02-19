# Auto Teleprompter

A web-based teleprompter application that tracks speech using the microphone and highlights words as they are being read. Built with Python, Flask, and AssemblyAI for real-time speech recognition.

Note: Server needs to run locally and have access to the microphone.

## Features

- Real-time speech recognition
- Automatic word highlighting
- Smooth text scrolling
- Easy-to-use web interface
- Responsive design

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- An AssemblyAI API key
- Running the server locally

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd teleprompter
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your AssemblyAI API key:
```
ASSEMBLYAI_API_KEY=your_api_key_here
SECRET_KEY=your-secret-key-here
```

4. Run the application:
```bash
python app.py
```

5. Open your web browser and navigate to `http://localhost:8000`

## Usage

1. Enter or paste your script into the text area
2. Click "Start" to begin
3. Start reading the text
4. The application will highlight words as you speak them
5. Click "Stop" when you're finished

## Note

Make sure your microphone is properly connected and you have granted the necessary permissions in your web browser for microphone access. 