"""
Live AI Interviewer - FastAPI Backend (Optimized)
Near-instant response times with aggressive VAD and binary passthrough.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
# MODEL_ID = "gemini-2.5-flash-preview-native-audio-dialog"
MODEL_ID = os.getenv("MODEL_ID") or "gemini-2.5-flash-preview-native-audio-dialog"


# System instruction for the AI Interviewer
INTERVIEWER_SYSTEM_INSTRUCTION = """
You are a professional technical recruiter conducting an interview for a Junior Python Developer position at a top-tier technology company.

## Your Identity & Demeanor
- You are "Alex", a Senior Technical Recruiter with 10+ years of experience
- Maintain a professional yet approachable tone
- Be slightly rigorous but fair - you want to assess skills accurately
- Show genuine interest in the candidate's responses
- Provide brief acknowledgments before moving to the next question

## Interview Structure
1. **Opening (First interaction)**:
   - Greet the candidate warmly
   - Introduce yourself briefly
   - Ask a warm-up question about their background or why they're interested in Python

2. **Technical Assessment** (Progress through these topics):
   - Python fundamentals: data types, variables, control flow
   - List comprehensions and generator expressions
   - Functions: args, kwargs, decorators, closures
   - Object-Oriented Programming in Python
   - Memory management and garbage collection basics
   - Error handling and exceptions
   - Web frameworks: FastAPI or Flask basics
   - Basic understanding of async/await

3. **Behavioral Questions**:
   - Problem-solving approach
   - Learning from mistakes
   - Team collaboration

## Important Behaviors
- **Multilingual Support**: If the candidate speaks in Hindi, Gujarati, Spanish, French, German, or any other language, seamlessly switch to that language while maintaining the technical interview context.

- **Barge-in Handling**: If the candidate starts speaking while you're talking, immediately stop and listen attentively. Acknowledge what they said before continuing.

- **Adaptive Difficulty**: Adjust question complexity based on candidate responses.

- **Time Awareness**: Keep responses concise (20-40 seconds of speech). Don't monologue.

- **Encouragement**: Provide positive reinforcement for good answers.

## Response Format
- Speak naturally as in a real conversation
- Ask one question at a time
- Keep responses SHORT and conversational

Remember: You are conducting a VOICE interview. Keep responses brief and natural.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("🚀 Live AI Interviewer starting up (Optimized)...")
    print(f"📡 Using model: {MODEL_ID}")
    
    if not GOOGLE_API_KEY:
        print("⚠️  WARNING: GOOGLE_API_KEY not found!")
    else:
        print("✅ Google API Key loaded")
    
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="Live AI Interviewer",
    description="Real-time AI interview with near-instant responses",
    version="2.0.0",
    lifespan=lifespan
)

templates = Jinja2Templates(directory="templates")


class OptimizedInterviewSession:
    """
    Optimized interview session with:
    - Binary audio passthrough (no base64 overhead)
    - Aggressive VAD settings
    - Barge-in support
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session = None
        self.is_active = False
        self.stop_event = asyncio.Event()
        self.receive_task: Optional[asyncio.Task] = None
        self.is_ai_speaking = False
        
    async def send_json(self, msg_type: str, **kwargs):
        """Send JSON message to client."""
        try:
            await self.websocket.send_json({"type": msg_type, **kwargs})
        except Exception as e:
            print(f"Send error: {e}")
    
    async def send_binary(self, data: bytes):
        """Send raw binary audio to client (zero-copy)."""
        try:
            await self.websocket.send_bytes(data)
        except Exception as e:
            print(f"Binary send error: {e}")
    
    async def handle_gemini_stream(self):
        """Process Gemini responses with minimal latency."""
        try:
            while not self.stop_event.is_set():
                try:
                    async for response in self.session.receive():
                        if self.stop_event.is_set():
                            break
                        
                        if response.server_content:
                            content = response.server_content
                            
                            # Model turn complete - ready for input
                            if content.turn_complete:
                                self.is_ai_speaking = False
                                await self.send_json("status", status="listening")
                            
                            # Stream audio chunks immediately (binary passthrough)
                            if content.model_turn and content.model_turn.parts:
                                for part in content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        self.is_ai_speaking = True
                                        # Send raw binary - no base64 encoding!
                                        await self.send_binary(part.inline_data.data)
                                        await self.send_json("status", status="speaking")
                            
                            # Stream transcription
                            if content.output_transcription and content.output_transcription.text:
                                await self.send_json(
                                    "transcript",
                                    role="interviewer",
                                    text=content.output_transcription.text
                                )
                            
                            if content.input_transcription and content.input_transcription.text:
                                await self.send_json(
                                    "transcript",
                                    role="candidate",
                                    text=content.input_transcription.text
                                )
                                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if not self.stop_event.is_set():
                        print(f"Gemini stream error: {e}")
                        await self.send_json("error", message=str(e))
                    break
                    
        except Exception as e:
            print(f"Stream handler error: {e}")
        finally:
            print("📡 Gemini stream ended")
    
    async def interrupt_ai(self):
        """Send interrupt signal to stop AI generation (barge-in)."""
        if self.session and self.is_ai_speaking:
            try:
                # Send empty audio to trigger interruption
                await self.session.send(
                    input=types.LiveClientRealtimeInput(
                        media_chunks=[
                            types.Blob(
                                data=b'',
                                mime_type="audio/pcm;rate=16000"
                            )
                        ]
                    )
                )
                self.is_ai_speaking = False
                await self.send_json("interrupt", status="interrupted")
                print("🛑 AI interrupted (barge-in)")
            except Exception as e:
                print(f"Interrupt error: {e}")
    
    async def run(self):
        """Main session loop."""
        if not GOOGLE_API_KEY:
            await self.send_json("error", message="API key not configured")
            return
        
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        # Optimized config with aggressive VAD
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=INTERVIEWER_SYSTEM_INSTRUCTION)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefix_padding_ms=100,
                    silence_duration_ms=500,  # Aggressive: respond after 500ms silence
                )
            ),
        )
        
        try:
            async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
                self.session = session
                self.is_active = True
                print("✅ Gemini session connected (optimized)")
                
                # Start response handler
                self.receive_task = asyncio.create_task(self.handle_gemini_stream())
                await self.send_json("status", status="ready")
                
                # Main message loop
                while self.is_active and not self.stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(
                            self.websocket.receive(),
                            timeout=0.1  # Fast polling
                        )
                        
                        if message["type"] == "websocket.disconnect":
                            break
                        
                        # Binary audio - direct passthrough to Gemini
                        if "bytes" in message:
                            audio_data = message["bytes"]
                            
                            # Check for barge-in signal (high volume while AI speaking)
                            if self.is_ai_speaking and len(audio_data) > 0:
                                # Simple energy detection for barge-in
                                import struct
                                try:
                                    samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
                                    energy = sum(abs(s) for s in samples[:100]) / 100
                                    if energy > 2000:  # Threshold for voice detection
                                        await self.interrupt_ai()
                                except:
                                    pass
                            
                            # Send audio to Gemini
                            try:
                                await session.send(
                                    input=types.LiveClientRealtimeInput(
                                        media_chunks=[
                                            types.Blob(
                                                data=audio_data,
                                                mime_type="audio/pcm;rate=16000"
                                            )
                                        ]
                                    )
                                )
                            except Exception as e:
                                print(f"Audio send error: {e}")
                        
                        # JSON commands
                        elif "text" in message:
                            try:
                                data = json.loads(message["text"])
                                
                                if data.get("type") == "start_interview":
                                    print("🎤 Starting interview...")
                                    await session.send(
                                        input=types.LiveClientContent(
                                            turns=[
                                                types.Content(
                                                    role="user",
                                                    parts=[types.Part(text="Begin the interview. Greet me briefly and ask your first question.")]
                                                )
                                            ],
                                            turn_complete=True
                                        )
                                    )
                                
                                elif data.get("type") == "interrupt":
                                    await self.interrupt_ai()
                                
                                elif data.get("type") == "end_session":
                                    break
                                    
                            except json.JSONDecodeError:
                                pass
                                
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        if "disconnect" in str(e).lower() or "closed" in str(e).lower():
                            break
                        print(f"Message error: {e}")
                        
        except Exception as e:
            print(f"❌ Session error: {e}")
            await self.send_json("error", message=str(e))
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        self.is_active = False
        self.stop_event.set()
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        print("🔌 Session cleaned up")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws/interview")
async def websocket_interview(websocket: WebSocket):
    await websocket.accept()
    print("🔗 WebSocket connected")
    
    session = OptimizedInterviewSession(websocket)
    
    try:
        await session.run()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
        print("👋 WebSocket closed")


@app.get("/health")
async def health():
    return {"status": "healthy", "model": MODEL_ID, "optimized": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
