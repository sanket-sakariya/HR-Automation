"""
Real-time Multilingual AI Interviewer Platform
Using FastAPI + Gemini 2.5 Flash Multimodal Live API (WebSockets)

Features:
- Real-time bidirectional audio streaming
- Multilingual support: English, Hindi, Gujarati (auto-detect & switch)
- WebSocket proxy to Gemini API
- Barge-in/interruption support
- Senior Technical Recruiter persona
- AudioWorklet-based smooth playback (16kHz input / 24kHz output)
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
    raise ValueError("GEMINI_API_KEY not found! Please set it in .env.dev file")

print(f"✅ API Key loaded (ends with: ...{GEMINI_API_KEY[-8:]})")

# Gemini Multimodal Live API Configuration
GEMINI_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

# Multilingual System Instruction for Senior Technical Recruiter
SYSTEM_INSTRUCTION = """You are a Senior Technical Recruiter conducting a real-time voice interview. You are based in India and are fluent in English, Hindi, and Gujarati.

CRITICAL SPEAKING GUIDELINES:
- Speak at a MODERATE, CLEAR pace - not too fast, not too slow
- Pronounce each word clearly and distinctly
- Pause briefly between sentences for better comprehension
- Avoid rushing through sentences - take your time
- Speak naturally but ensure every word is understandable

LANGUAGE BEHAVIOR:
- Start the interview in English with a warm greeting
- If the candidate speaks in Hindi, seamlessly switch to Hindi and continue in Hindi
- If the candidate speaks in Gujarati, seamlessly switch to Gujarati and continue in Gujarati
- You can mix languages naturally (Hinglish or Gujarati-English) if the candidate does so
- If the candidate says "please speak in Hindi" or "Hindi mein bolo" or "Gujarati ma bolo", switch immediately
- Always match the language preference of the candidate

GUJARATI RESPONSES:
- When speaking Gujarati, use natural Rajkot/Saurashtra dialect if appropriate
- Be warm and encouraging: "ઘણું સરસ!" (Very nice!), "બહુ સારું!" (Very good!)
- Ask questions clearly: "તમે તમારા અનુભવ વિશે જણાવો" (Tell me about your experience)

HINDI RESPONSES:
- Use conversational Hindi, not formal/literary Hindi
- Be encouraging: "बहुत अच्छा!", "बिल्कुल सही!"
- Ask questions naturally: "अपने experience के बारे में बताइए"

INTERVIEW GUIDELINES:
1. Ask ONE question at a time and wait for complete response
2. Start with a warm, professional greeting
3. If candidate seems nervous or struggles with English, gently offer to switch to Hindi or Gujarati
4. Begin with easier questions, gradually increase difficulty
5. Listen actively and ask relevant follow-ups
6. Be encouraging and supportive, especially with regional language speakers

QUESTION FLOW:
1. Introduction - "Tell me about yourself" / "અમને તમારા વિશે જણાવો" / "अपने बारे में बताइए"
2. Experience and background
3. Technical skills relevant to the role
4. Problem-solving scenarios
5. Career goals and motivation

COMMUNICATION STYLE:
- Speak CLEARLY at MODERATE pace - this is very important
- Be warm, professional, and culturally sensitive
- Give candidate time to think
- Acknowledge answers positively in the same language
- If answer is unclear, politely ask for clarification in their preferred language
- Keep responses concise - avoid long monologues

Remember: This is a VOICE conversation. Keep responses concise and natural. No markdown, bullet points, or text formatting - speak as you would in a real interview. Sound human, not robotic. Most importantly, SPEAK CLEARLY AND AT A COMFORTABLE PACE."""

# Generation config for audio output
# Available voices: Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr
GENERATION_CONFIG = {
    "response_modalities": ["AUDIO"],
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Aoede"  # Soft, warm voice - change to any: Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr
            }
        }
    }
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("\n" + "=" * 75)
    print("🎤 MULTILINGUAL AI INTERVIEWER - Powered by Gemini 2.5 Flash")
    print("=" * 75)
    print("🌍 LANGUAGES: English | हिंदी (Hindi) | ગુજરાતી (Gujarati)")
    print("🔄 AUTO-DETECT: Just speak in any language - AI will adapt!")
    print("🎯 PERSONA: Senior Technical Recruiter")
    print("=" * 75)
    print("🚀 Server starting at http://localhost:8000")
    print("⚠️  Allow microphone permissions when prompted!")
    print("💡 TIP: Say 'Gujarati ma bolo' or 'Hindi mein bolo' to switch languages")
    print("=" * 75 + "\n")
    yield
    print("\n👋 Server shutting down...")


app = FastAPI(title="Multilingual AI Interviewer", lifespan=lifespan)

# Ensure directories exist
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def get_index():
    """Serve the main HTML page"""
    html_path = templates_dir / "index.html"
    return FileResponse(html_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket proxy between frontend and Gemini Multimodal Live API
    
    Flow:
    1. Accept frontend connection
    2. Connect to Gemini WebSocket
    3. Send BidiGenerateContentSetup with multilingual system instruction
    4. Proxy audio bidirectionally with interrupt support
    """
    await websocket.accept()
    print("✅ Frontend WebSocket connected")
    
    gemini_ws = None
    receive_task = None
    send_task = None
    
    try:
        # Connect to Gemini WebSocket
        import websockets
        
        print("🔗 Connecting to Gemini 2.5 Flash Multimodal Live API...")
        gemini_ws = await websockets.connect(
            GEMINI_WS_URL,
            additional_headers={"Content-Type": "application/json"},
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5,
            max_size=10 * 1024 * 1024  # 10MB max message size
        )
        print("✅ Connected to Gemini API")
        
        # Send BidiGenerateContentSetup message
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
        print("📤 Sent BidiGenerateContentSetup to Gemini")
        
        # Wait for setup complete response
        setup_response = await asyncio.wait_for(gemini_ws.recv(), timeout=30)
        setup_data = json.loads(setup_response)
        
        if "setupComplete" in setup_data:
            print("✅ Gemini setup complete - Ready for multilingual interview!")
            await websocket.send_json({
                "type": "setup_complete",
                "message": "Connected! Start speaking in English, Hindi, or Gujarati."
            })
            
            # Send initial prompt to trigger AI greeting
            initial_prompt = {
                "clientContent": {
                    "turns": [{
                        "role": "user",
                        "parts": [{"text": "Please start the interview with a warm greeting and introduce yourself."}]
                    }],
                    "turnComplete": True
                }
            }
            await gemini_ws.send(json.dumps(initial_prompt))
            print("📤 Sent initial prompt to trigger AI greeting")
            
        else:
            print(f"⚠️ Unexpected setup response: {setup_data}")
            await websocket.send_json({"type": "error", "message": "Setup failed"})
            return
        
        # Create tasks for bidirectional communication
        async def receive_from_gemini():
            """Receive audio/events from Gemini and forward to frontend"""
            try:
                async for message in gemini_ws:
                    data = json.loads(message)
                    
                    # Log all message types for debugging
                    msg_keys = list(data.keys())
                    print(f"📥 Gemini message keys: {msg_keys}")
                    
                    # Handle server content (audio response)
                    if "serverContent" in data:
                        server_content = data["serverContent"]
                        
                        # Handle interruption (barge-in detected by Gemini)
                        if server_content.get("interrupted"):
                            print("🛑 Gemini detected interruption")
                            await websocket.send_json({"type": "interrupted"})
                            continue
                        
                        # Check for turn complete
                        if server_content.get("turnComplete"):
                            print("✅ AI turn complete - waiting for user")
                            await websocket.send_json({"type": "turn_complete"})
                            continue
                        
                        # Process model turn with audio
                        model_turn = server_content.get("modelTurn", {})
                        parts = model_turn.get("parts", [])
                        
                        for part in parts:
                            # Handle audio data
                            if "inlineData" in part:
                                inline_data = part["inlineData"]
                                mime_type = inline_data.get("mimeType", "")
                                
                                if mime_type.startswith("audio/"):
                                    audio_b64 = inline_data.get("data", "")
                                    if audio_b64:
                                        audio_bytes = len(audio_b64) * 3 // 4  # Approximate decoded size
                                        print(f"🔊 Audio chunk: {audio_bytes} bytes, mime: {mime_type}")
                                        # Send audio chunk to frontend
                                        await websocket.send_json({
                                            "type": "audio",
                                            "data": audio_b64,
                                            "mimeType": mime_type
                                        })
                            
                            # Handle text (for transcript display)
                            if "text" in part:
                                text = part["text"]
                                print(f"📝 AI: {text[:80]}...")
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": text,
                                    "speaker": "ai"
                                })
                    
                    # Handle tool calls (future extension)
                    elif "toolCall" in data:
                        print(f"🔧 Tool call: {data['toolCall']}")
                        
            except websockets.exceptions.ConnectionClosed as e:
                print(f"🔌 Gemini connection closed: {e}")
            except Exception as e:
                print(f"❌ Error receiving from Gemini: {e}")
        
        async def send_to_gemini():
            """Receive audio/commands from frontend and forward to Gemini"""
            try:
                while True:
                    # Receive from frontend
                    data = await websocket.receive_json()
                    msg_type = data.get("type")
                    
                    if msg_type == "audio":
                        # Forward audio chunk to Gemini
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
                    
                    elif msg_type == "interrupt":
                        # User wants to interrupt AI (barge-in)
                        print("🛑 User requested interrupt")
                        # Gemini handles this automatically via voice activity detection
                        
                    elif msg_type == "language_switch":
                        # User explicitly requested language switch
                        lang = data.get("language", "english")
                        print(f"🌍 User requested language switch to: {lang}")
                        
                    elif msg_type == "stop":
                        print("🛑 Stop signal received from frontend")
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
        "model": GEMINI_MODEL,
        "features": {
            "languages": ["English", "Hindi (हिंदी)", "Gujarati (ગુજરાતી)"],
            "audio_input": "16kHz PCM mono",
            "audio_output": "24kHz PCM mono",
            "barge_in": True,
            "auto_language_detection": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
