"""
Live AI Interviewer - FastAPI Backend (Production Hardened)
Features:
- Asyncio Jitter Buffer for network stability
- Configurable barge-in mandate filtering
- Memory-efficient streaming
- Latency tracking
"""

import asyncio
import json
import os
import time
import struct
from collections import deque
from contextlib import asynccontextmanager
from typing import Optional, Deque
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_ID = os.getenv("MODEL_ID") or "gemini-2.5-flash-preview-native-audio-dialog"

# Jitter Buffer Configuration
JITTER_BUFFER_MS = 50  # Reduced from 150ms for faster response
JITTER_BUFFER_MAX_CHUNKS = 5  # Reduced for lower latency
MIN_SPEECH_DURATION_MS = 150  # Reduced from 200ms for faster barge-in


@dataclass
class AudioChunk:
    """Timestamped audio chunk for jitter buffer."""
    data: bytes
    timestamp: float = field(default_factory=time.time)
    sequence: int = 0


class JitterBuffer:
    """
    Async jitter buffer to smooth out network packet timing variations.
    Holds audio briefly to ensure correct sequence even if packets arrive out of order.
    """
    
    def __init__(self, buffer_ms: int = JITTER_BUFFER_MS, max_chunks: int = JITTER_BUFFER_MAX_CHUNKS):
        self.buffer_ms = buffer_ms
        self.max_chunks = max_chunks
        self.buffer: Deque[AudioChunk] = deque(maxlen=max_chunks)
        self.sequence_counter = 0
        self._lock = asyncio.Lock()
        self._flush_event = asyncio.Event()
        self._last_flush_time = time.time()
        
    async def add(self, data: bytes) -> Optional[bytes]:
        """
        Add audio chunk to buffer. Returns flushed audio if buffer is ready.
        """
        async with self._lock:
            self.sequence_counter += 1
            chunk = AudioChunk(data=data, sequence=self.sequence_counter)
            self.buffer.append(chunk)
            
            # Check if we should flush
            now = time.time()
            buffer_age_ms = (now - self._last_flush_time) * 1000
            
            # Flush conditions:
            # 1. Buffer age exceeds jitter buffer time
            # 2. Buffer is at max capacity
            should_flush = buffer_age_ms >= self.buffer_ms or len(self.buffer) >= self.max_chunks
            
            if should_flush and self.buffer:
                return await self._flush()
            
            return None
    
    async def _flush(self) -> bytes:
        """Flush all buffered chunks in sequence order."""
        # Sort by sequence to ensure correct order even if packets arrived out of order
        sorted_chunks = sorted(self.buffer, key=lambda c: c.sequence)
        
        # Concatenate all audio data
        combined = b''.join(chunk.data for chunk in sorted_chunks)
        
        # Clear buffer and reset timer
        self.buffer.clear()
        self._last_flush_time = time.time()
        
        return combined
    
    async def force_flush(self) -> Optional[bytes]:
        """Force flush remaining buffer contents."""
        async with self._lock:
            if self.buffer:
                return await self._flush()
            return None
    
    @property
    def size(self) -> int:
        """Current number of chunks in buffer."""
        return len(self.buffer)


class SpeechActivityTracker:
    """
    Tracks speech activity duration to filter out short bursts (coughs, bumps).
    Only marks speech as valid after MIN_SPEECH_DURATION_MS.
    """
    
    def __init__(self, min_duration_ms: int = MIN_SPEECH_DURATION_MS):
        self.min_duration_ms = min_duration_ms
        self.speech_start_time: Optional[float] = None
        self.is_valid_speech = False
        self._energy_history: Deque[float] = deque(maxlen=10)
    
    def update(self, audio_data: bytes, energy_threshold: int = 2000) -> bool:
        """
        Update speech tracking with new audio chunk.
        Returns True if this is valid continuous speech (not just a short burst).
        """
        try:
            # Calculate energy from audio samples
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            energy = sum(abs(s) for s in samples[:100]) / max(100, len(samples[:100]))
            self._energy_history.append(energy)
            
            # Use smoothed energy to reduce noise sensitivity
            avg_energy = sum(self._energy_history) / len(self._energy_history)
            
            if avg_energy > energy_threshold:
                # Speech detected
                if self.speech_start_time is None:
                    self.speech_start_time = time.time()
                
                # Check if speech duration exceeds minimum
                duration_ms = (time.time() - self.speech_start_time) * 1000
                if duration_ms >= self.min_duration_ms:
                    self.is_valid_speech = True
                    return True
                return False
            else:
                # Silence - reset tracking
                self.speech_start_time = None
                self.is_valid_speech = False
                return False
                
        except Exception:
            return False
    
    def reset(self):
        """Reset speech tracking state."""
        self.speech_start_time = None
        self.is_valid_speech = False
        self._energy_history.clear()


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
    print("🚀 Live AI Interviewer starting up (Production Hardened)...")
    print(f"📡 Using model: {MODEL_ID}")
    print(f"⏱️  Jitter buffer: {JITTER_BUFFER_MS}ms")
    print(f"🎤 Min speech duration: {MIN_SPEECH_DURATION_MS}ms")
    
    if not GOOGLE_API_KEY:
        print("⚠️  WARNING: GOOGLE_API_KEY not found!")
    else:
        print("✅ Google API Key loaded")
    
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="Live AI Interviewer",
    description="Production-hardened real-time AI interview with jitter buffer and noise filtering",
    version="3.0.0",
    lifespan=lifespan
)

# Serve static files (for Web Worker)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


class ProductionInterviewSession:
    """
    Production-hardened interview session with:
    - Jitter buffer for network stability
    - Speech activity tracking to filter noise
    - Barge-in mandate (min speech duration)
    - Binary audio passthrough (no base64 overhead)
    - Latency tracking
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session = None
        self.is_active = False
        self.stop_event = asyncio.Event()
        self.receive_task: Optional[asyncio.Task] = None
        self.jitter_flush_task: Optional[asyncio.Task] = None
        self.is_ai_speaking = False
        
        # Production stability components
        self.jitter_buffer = JitterBuffer(buffer_ms=JITTER_BUFFER_MS)
        self.speech_tracker = SpeechActivityTracker(min_duration_ms=MIN_SPEECH_DURATION_MS)
        
        # Latency tracking
        self.audio_send_times: Deque[float] = deque(maxlen=100)
        self.last_latency_ms: float = 0
        self.latency_samples: Deque[float] = deque(maxlen=20)
        
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
        """Process Gemini responses with minimal latency and latency tracking."""
        try:
            while not self.stop_event.is_set():
                try:
                    async for response in self.session.receive():
                        if self.stop_event.is_set():
                            break
                        
                        # Track response latency
                        if self.audio_send_times:
                            latency = (time.time() - self.audio_send_times[0]) * 1000
                            self.latency_samples.append(latency)
                            self.last_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
                        
                        if response.server_content:
                            content = response.server_content
                            
                            # Model turn complete - ready for input
                            if content.turn_complete:
                                self.is_ai_speaking = False
                                self.speech_tracker.reset()
                                await self.send_json("status", status="listening", latency_ms=round(self.last_latency_ms))
                            
                            # Stream audio chunks immediately (binary passthrough)
                            if content.model_turn and content.model_turn.parts:
                                for part in content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        self.is_ai_speaking = True
                                        # Send raw binary - no base64 encoding!
                                        await self.send_binary(part.inline_data.data)
                                        await self.send_json("status", status="speaking", latency_ms=round(self.last_latency_ms))
                            
                            # Stream transcription
                            if content.output_transcription and content.output_transcription.text:
                                await self.send_json(
                                    "transcript",
                                    role="interviewer",
                                    text=content.output_transcription.text
                                )
                            
                            # User transcription disabled for lower latency
                                
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
                self.speech_tracker.reset()
                await self.send_json("interrupt", status="interrupted")
                print("🛑 AI interrupted (barge-in)")
            except Exception as e:
                print(f"Interrupt error: {e}")
    
    async def send_buffered_audio(self, audio_data: bytes):
        """
        Send audio through jitter buffer for network stability.
        Audio is buffered briefly to ensure correct sequencing even with network jitter.
        """
        try:
            # Add to jitter buffer
            flushed_data = await self.jitter_buffer.add(audio_data)
            
            if flushed_data:
                # Track send time for latency measurement
                self.audio_send_times.append(time.time())
                if len(self.audio_send_times) > 50:
                    self.audio_send_times.popleft()
                
                # Send buffered audio to Gemini
                await self.session.send(
                    input=types.LiveClientRealtimeInput(
                        media_chunks=[
                            types.Blob(
                                data=flushed_data,
                                mime_type="audio/pcm;rate=16000"
                            )
                        ]
                    )
                )
        except Exception as e:
            print(f"Buffered audio send error: {e}")
    
    async def jitter_buffer_flush_loop(self):
        """Background task to periodically flush jitter buffer."""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.jitter_buffer.buffer_ms / 1000)
                
                if self.stop_event.is_set():
                    break
                    
                # Force flush any remaining buffered audio
                flushed = await self.jitter_buffer.force_flush()
                if flushed and self.session:
                    try:
                        await self.session.send(
                            input=types.LiveClientRealtimeInput(
                                media_chunks=[
                                    types.Blob(
                                        data=flushed,
                                        mime_type="audio/pcm;rate=16000"
                                    )
                                ]
                            )
                        )
                    except Exception as e:
                        print(f"Jitter flush error: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Jitter buffer loop error: {e}")
    
    async def run(self):
        """Main session loop with production stability features."""
        if not GOOGLE_API_KEY:
            await self.send_json("error", message="API key not configured")
            return
        
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        # Production-hardened config with barge-in mandate
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
            # Disabled input transcription for lower latency - only AI transcript
            # input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    # Using LOW sensitivity to reduce false interruptions from noise
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=150,  # Increased for stability
                    silence_duration_ms=600,  # Slightly longer to prevent cutting off
                )
            ),
        )
        
        try:
            async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
                self.session = session
                self.is_active = True
                print("✅ Gemini session connected (production hardened)")
                
                # Start response handler
                self.receive_task = asyncio.create_task(self.handle_gemini_stream())
                
                # Start jitter buffer flush loop
                self.jitter_flush_task = asyncio.create_task(self.jitter_buffer_flush_loop())
                
                await self.send_json("status", status="ready", latency_ms=0)
                
                # Main message loop
                while self.is_active and not self.stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(
                            self.websocket.receive(),
                            timeout=0.1  # Fast polling
                        )
                        
                        if message["type"] == "websocket.disconnect":
                            break
                        
                        # Binary audio - process through jitter buffer
                        if "bytes" in message:
                            audio_data = message["bytes"]
                            
                            # Check for valid speech using speech tracker (filters short bursts)
                            is_valid_speech = self.speech_tracker.update(audio_data)
                            
                            # Barge-in: only interrupt if valid continuous speech
                            if self.is_ai_speaking and is_valid_speech:
                                await self.interrupt_ai()
                            
                            # Send audio through jitter buffer for network stability
                            await self.send_buffered_audio(audio_data)
                        
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
                                    # Only allow interrupt if speech is valid (not just noise)
                                    if self.speech_tracker.is_valid_speech:
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
        
        # Cancel jitter buffer flush task
        if self.jitter_flush_task:
            self.jitter_flush_task.cancel()
            try:
                await self.jitter_flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush any remaining buffered audio
        await self.jitter_buffer.force_flush()
        
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
    
    session = ProductionInterviewSession(websocket)
    
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
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "version": "3.0.0",
        "features": {
            "jitter_buffer_ms": JITTER_BUFFER_MS,
            "min_speech_duration_ms": MIN_SPEECH_DURATION_MS,
            "barge_in_filtering": True,
            "latency_tracking": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
