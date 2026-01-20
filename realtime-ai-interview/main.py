"""
Real-time AI Interviewer Platform
Using FastAPI + Gemini 2.0 Flash Multimodal Live API (WebSockets)

Features:
- Real-time bidirectional audio streaming
- WebSocket proxy to Gemini API
- Barge-in/interruption support
- Senior Technical Interviewer persona
"""

import os
import json
import asyncio
import base64
from pathlib import Path
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

# Load environment variables
env_file = Path(__file__).parent.parent / '.env.dev'
dotenv.load_dotenv(env_file)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables!")

print(f"✅ API Key loaded (ends with: ...{GEMINI_API_KEY[-8:]})")

# Gemini Multimodal Live API Configuration
GEMINI_MODEL = "models/gemini-2.0-flash-exp"
GEMINI_WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

# System prompt for the AI Interviewer
SYSTEM_INSTRUCTION = """You are a Senior Technical Interviewer at a leading technology company. Your role is to conduct professional, engaging technical interviews.

INTERVIEW GUIDELINES:
1. Ask ONE question at a time and wait for the candidate's complete response
2. Start with a warm, professional greeting and introduce yourself
3. Begin with easier questions and gradually increase difficulty
4. Listen actively and ask relevant follow-up questions based on responses
5. Be encouraging but maintain professional standards
6. Provide brief acknowledgments after each answer before moving to the next question

QUESTION FLOW:
1. Introduction and ice-breaker
2. Background and experience questions
3. Technical knowledge questions
4. Problem-solving scenarios
5. Behavioral questions (STAR method)
6. Questions about the candidate's goals and interests

COMMUNICATION STYLE:
- Speak clearly and at a moderate pace
- Be warm, professional, and encouraging
- Give the candidate time to think
- Acknowledge good answers positively
- If an answer is unclear, politely ask for clarification

Remember: You are having a real-time voice conversation. Keep responses concise and conversational. Do not use markdown, bullet points, or any text formatting - speak naturally as in a real interview."""

# Generation config for audio
GENERATION_CONFIG = {
    "response_modalities": ["AUDIO"],
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Aoede"  # Professional sounding voice
            }
        }
    }
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("\n" + "=" * 70)
    print("🎤 REAL-TIME AI INTERVIEWER - Powered by Gemini 2.0 Flash")
    print("=" * 70)
    print("🚀 Server starting...")
    print("🌐 Open http://localhost:8000 in your browser")
    print("⚠️  Allow microphone permissions when prompted!")
    print("=" * 70 + "\n")
    yield
    print("\n👋 Server shutting down...")


app = FastAPI(title="Real-time AI Interviewer", lifespan=lifespan)

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main HTML page"""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return FileResponse(html_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket proxy between frontend and Gemini Multimodal Live API
    
    Flow:
    1. Accept frontend connection
    2. Connect to Gemini WebSocket
    3. Send setup message with system instruction
    4. Proxy audio bidirectionally
    """
    await websocket.accept()
    print("✅ Frontend WebSocket connected")
    
    gemini_ws = None
    receive_task = None
    send_task = None
    
    try:
        # Connect to Gemini WebSocket
        import websockets
        
        print("🔗 Connecting to Gemini Multimodal Live API...")
        gemini_ws = await websockets.connect(
            GEMINI_WS_URL,
            additional_headers={"Content-Type": "application/json"},
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5
        )
        print("✅ Connected to Gemini API")
        
        # Send setup message (BidiGenerateContent handshake)
        setup_message = {
            "setup": {
                "model": GEMINI_MODEL,
                "generation_config": GENERATION_CONFIG,
                "system_instruction": {
                    "parts": [{"text": SYSTEM_INSTRUCTION}]
                }
            }
        }
        
        await gemini_ws.send(json.dumps(setup_message))
        print("📤 Sent setup message to Gemini")
        
        # Wait for setup complete response
        setup_response = await gemini_ws.recv()
        setup_data = json.loads(setup_response)
        
        if "setupComplete" in setup_data:
            print("✅ Gemini setup complete")
            await websocket.send_json({"type": "setup_complete"})
        else:
            print(f"⚠️ Unexpected setup response: {setup_data}")
        
        # Create tasks for bidirectional communication
        async def receive_from_gemini():
            """Receive audio/text from Gemini and forward to frontend"""
            try:
                async for message in gemini_ws:
                    data = json.loads(message)
                    
                    # Handle server content (audio response)
                    if "serverContent" in data:
                        server_content = data["serverContent"]
                        
                        # Check for interruption
                        if server_content.get("interrupted"):
                            print("🛑 Gemini interrupted")
                            await websocket.send_json({"type": "interrupted"})
                            continue
                        
                        # Check for turn complete
                        if server_content.get("turnComplete"):
                            print("✅ Gemini turn complete")
                            await websocket.send_json({"type": "turn_complete"})
                            continue
                        
                        # Process model turn with audio
                        model_turn = server_content.get("modelTurn", {})
                        parts = model_turn.get("parts", [])
                        
                        for part in parts:
                            # Handle audio data
                            if "inlineData" in part:
                                inline_data = part["inlineData"]
                                if inline_data.get("mimeType", "").startswith("audio/"):
                                    audio_b64 = inline_data.get("data", "")
                                    if audio_b64:
                                        await websocket.send_json({
                                            "type": "audio",
                                            "data": audio_b64
                                        })
                            
                            # Handle text (for debugging/display)
                            if "text" in part:
                                text = part["text"]
                                print(f"📝 Gemini text: {text[:100]}...")
                                await websocket.send_json({
                                    "type": "text",
                                    "data": text
                                })
                    
                    # Handle tool calls if any (for future extension)
                    elif "toolCall" in data:
                        print(f"🔧 Tool call received: {data['toolCall']}")
                        
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Gemini WebSocket closed")
            except Exception as e:
                print(f"❌ Error receiving from Gemini: {e}")
        
        async def send_to_gemini():
            """Receive audio from frontend and forward to Gemini"""
            try:
                while True:
                    # Receive from frontend
                    data = await websocket.receive_json()
                    
                    if data.get("type") == "audio":
                        # Forward audio to Gemini
                        audio_b64 = data.get("data", "")
                        
                        realtime_input = {
                            "realtimeInput": {
                                "mediaChunks": [{
                                    "mimeType": "audio/pcm;rate=16000",
                                    "data": audio_b64
                                }]
                            }
                        }
                        
                        await gemini_ws.send(json.dumps(realtime_input))
                    
                    elif data.get("type") == "end_turn":
                        # Signal end of user turn
                        print("📤 User ended turn")
                        # Gemini auto-detects end of speech, but we can send explicit signal
                        
                    elif data.get("type") == "stop":
                        print("🛑 Stop signal received")
                        break
                        
            except WebSocketDisconnect:
                print("🔌 Frontend disconnected")
            except Exception as e:
                print(f"❌ Error sending to Gemini: {e}")
        
        # Run both tasks concurrently
        receive_task = asyncio.create_task(receive_from_gemini())
        send_task = asyncio.create_task(send_to_gemini())
        
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    except WebSocketDisconnect:
        print("🔌 Frontend WebSocket disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if gemini_ws:
            await gemini_ws.close()
            print("🔌 Gemini WebSocket closed")
        
        try:
            await websocket.close()
        except:
            pass
        
        print("👋 Session ended")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "realtime-ai-interviewer",
        "model": GEMINI_MODEL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
