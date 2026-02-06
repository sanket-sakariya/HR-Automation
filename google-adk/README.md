# Live AI Interviewer

A production-ready real-time AI-powered technical interview application for Junior Python Developer positions. Built with FastAPI, Google Gemini Live API, and vanilla JavaScript.

![Interview Application](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange.svg)

## Features

- 🎤 **Real-time Voice Interaction**: Bidirectional audio streaming with Gemini Live API
- 📝 **Live Transcription**: See what both interviewer and candidate are saying in real-time
- 🌍 **Multilingual Support**: Automatically detects and responds in the candidate's language
- 🎯 **Adaptive Interviews**: AI adjusts difficulty based on candidate responses
- 🎨 **Modern UI**: Sleek black and white minimalist design with audio visualizer
- ⚡ **Low Latency**: WebSocket-based communication for instant responses
- 🔊 **Barge-in Support**: Interrupt the AI naturally, just like a real conversation

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **AI Model**: Gemini 2.5 Flash Native Audio Preview
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Communication**: WebSockets for real-time streaming
- **Audio**: Web Audio API (16kHz PCM capture, 24kHz playback)

## Quick Start

### 1. Prerequisites

- Python 3.10 or higher
- Google Cloud API Key with Gemini API access
- Modern web browser (Chrome, Firefox, Edge)

### 2. Installation

```bash
# Clone or navigate to the project directory
cd google-adk

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Google API key
# GOOGLE_API_KEY=your_actual_api_key_here
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 4. Run the Application

```bash
# Start the server
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

1. **Click "Start Interview"** - This will:
   - Request microphone permission
   - Establish WebSocket connection
   - Initialize the Gemini Live session

2. **Wait for AI Greeting** - The AI interviewer (Alex) will introduce themselves and ask the first question

3. **Respond naturally** - Speak your answers; the AI will listen and respond appropriately

4. **View Transcript** - Real-time transcript appears in the right panel

5. **End Interview** - Click "End Session" when done

## Project Structure

```
google-adk/
├── main.py                 # FastAPI backend with WebSocket handling
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from .env.example)
├── .env.example           # Example environment file
├── README.md              # This file
└── templates/
    └── index.html         # Frontend (HTML, CSS, JS)
```

## API Endpoints

| Endpoint | Type | Description |
|----------|------|-------------|
| `GET /` | HTTP | Serves the interview frontend |
| `GET /health` | HTTP | Health check endpoint |
| `WS /ws/interview` | WebSocket | Real-time interview streaming |

## WebSocket Message Types

### Client → Server

| Type | Format | Description |
|------|--------|-------------|
| `start_interview` | JSON | Initiates the interview |
| `end_session` | JSON | Ends the interview session |
| Binary | ArrayBuffer | Raw PCM audio (16-bit, 16kHz) |

### Server → Client

| Type | Format | Description |
|------|--------|-------------|
| `status` | JSON | Connection/interview status |
| `transcript` | JSON | Real-time transcription |
| `audio` | JSON (base64) | AI voice response |
| `error` | JSON | Error messages |

## Interview Topics

The AI interviewer covers:

1. **Python Fundamentals**
   - Data types and variables
   - Control flow (loops, conditionals)
   
2. **Intermediate Python**
   - List comprehensions
   - Functions (args, kwargs)
   - Decorators and closures

3. **Object-Oriented Programming**
   - Classes and inheritance
   - Magic methods

4. **Advanced Topics**
   - Memory management
   - Async/await basics
   - Error handling

5. **Web Frameworks**
   - FastAPI or Flask basics
   - REST API concepts

## Troubleshooting

### Microphone Not Working
- Ensure browser has microphone permissions
- Check that no other application is using the microphone
- Try using HTTPS (required for some browsers)

### WebSocket Connection Failed
- Verify the server is running on port 8000
- Check firewall settings
- Ensure GOOGLE_API_KEY is set correctly

### No Audio Playback
- Check browser audio permissions
- Ensure volume is not muted
- Try clicking somewhere on the page first (autoplay policy)

### API Rate Limits
- The Gemini Live API has usage limits
- Wait a few minutes and try again
- Check your Google Cloud quota

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google AI API key for Gemini |

## Browser Compatibility

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 90+ | ✅ Fully Supported |
| Firefox | 88+ | ✅ Fully Supported |
| Edge | 90+ | ✅ Fully Supported |
| Safari | 15+ | ⚠️ Limited (WebSocket issues) |

## Security Notes

- Never commit your `.env` file
- Use HTTPS in production
- Implement rate limiting for production use
- Add authentication for multi-user scenarios

## License

MIT License - Feel free to use and modify for your own projects.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

Built with ❤️ using Google Gemini and FastAPI
