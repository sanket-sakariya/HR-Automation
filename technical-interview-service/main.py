"""
Technical Interview Service - AI-Powered Real-time Interview Platform
Runs on port 8100 and connects to the main interview-management-service

Features:
- Real-time bidirectional audio streaming with Gemini 2.5 Flash
- Dynamic system instruction based on job requirements
- Multilingual support: English, Hindi, Gujarati
- Comprehensive interview evaluation and scoring
"""

import os
import json
import asyncio
import base64
import httpx
import websockets
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Load environment variables
env_file = Path(__file__).parent.parent / '.env.dev'
dotenv.load_dotenv(env_file)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found! Please set it in .env.dev file")

print(f"✅ API Key loaded (ends with: ...{GEMINI_API_KEY[-8:]})")

# Main service URL
MAIN_SERVICE_URL = os.getenv("MAIN_SERVICE_URL", "http://localhost:8888/interview-management-service/api/v1")

# Gemini Multimodal Live API Configuration
# Use gemini-2.5-flash-native-audio-preview for real-time bidirectional audio
GEMINI_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

# Generation config for audio output
GENERATION_CONFIG = {
    "response_modalities": ["AUDIO"],
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Aoede"
            }
        }
    }
}


# Store active interview sessions
active_sessions = {}


class InterviewSession:
    """Stores interview session data and dynamically calculated scores"""
    def __init__(self, session_id: str, technical_interview_id: str, job_details: dict, candidate_info: dict, system_instruction: str):
        self.session_id = session_id
        self.technical_interview_id = technical_interview_id
        self.job_details = job_details
        self.candidate_info = candidate_info
        self.system_instruction = system_instruction
        self.started_at = None
        self.transcript = []
        self.token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "audio_input_seconds": 0.0,
            "audio_output_seconds": 0.0
        }
        
        # Dynamic scoring metrics (updated during interview)
        self.scores = {
            "overall_score": 0.0,
            "overall_rating": "average",
            "technical_knowledge_score": 0.0,
            "domain_expertise_score": 0.0,
            "communication_score": 0.0,
            "language_proficiency_score": 0.0,
            "confidence_score": 0.0,
            "professionalism_score": 0.0,
            "response_relevance_score": 0.0,
            "response_depth_score": 0.0,
            "response_clarity_score": 0.0,
            "engagement_score": 0.0,
        }
        
        # Question tracking
        self.questions_asked = 0
        self.questions_answered = 0
        self.questions_skipped = 0
        self.response_times = []  # List of response times in seconds
        
        # AI analysis results
        self.candidate_strengths = []
        self.candidate_weaknesses = []
        self.improvement_areas = []
        self.skills_assessment = []
        self.ai_recommendation = "neutral"
        self.ai_recommendation_reason = ""
        self.ai_feedback_summary = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("\n" + "=" * 75)
    print("🎤 TECHNICAL INTERVIEW SERVICE - Powered by Gemini 2.5 Flash")
    print("=" * 75)
    print("🌍 LANGUAGES: English | हिंदी (Hindi) | ગુજરાતી (Gujarati)")
    print("🔄 AUTO-DETECT: Just speak in any language - AI will adapt!")
    print("🎯 PERSONA: Senior Technical Recruiter")
    print(f"🔗 Main Service: {MAIN_SERVICE_URL}")
    print("=" * 75)
    print("🚀 Server starting at http://localhost:8100")
    print("⚠️  Allow microphone permissions when prompted!")
    print("=" * 75 + "\n")
    yield
    print("\n👋 Server shutting down...")


app = FastAPI(title="Technical Interview Service", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class CreateInterviewRequest(BaseModel):
    """Request to create a technical interview"""
    job_requirement_id: str
    candidate_id: str


class LoginRequest(BaseModel):
    """Request for candidate login"""
    email: str
    password: str


@app.get("/")
async def get_index():
    """Serve the main HTML page"""
    html_path = templates_dir / "technical_interview.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>Technical Interview Service</h1><p>Template not found</p>")


@app.get("/interview/{session_id}")
async def get_interview_page(session_id: str):
    """Serve the interview page for a specific session"""
    html_path = templates_dir / "technical_interview.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>Interview page not found</h1>")


@app.post("/api/create-interview")
async def create_interview(request: CreateInterviewRequest):
    """
    Create a new technical interview session.
    Fetches job details and candidate info from main service.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get job details
            job_response = await client.get(
                f"{MAIN_SERVICE_URL}/job-requirements/{request.job_requirement_id}"
            )
            if job_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Job requirement not found")
            
            job_data = job_response.json()
            job_details = job_data.get("data", {})
            
            # Get candidate details
            candidate_response = await client.get(
                f"{MAIN_SERVICE_URL}/candidates/{request.candidate_id}"
            )
            if candidate_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Candidate not found")
            
            candidate_data = candidate_response.json()
            candidate_info = candidate_data.get("data", {})
            
            # Generate session ID
            session_id = f"TI-{uuid4().hex[:12]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Generate system instruction
            system_instruction = generate_system_instruction(job_details, candidate_info)
            
            # Create interview record in main service
            create_response = await client.post(
                f"{MAIN_SERVICE_URL}/technical-interview/login",
                json={
                    "job_requirement_id": request.job_requirement_id,
                    "email": candidate_info.get("email"),
                    "password": candidate_info.get("password", "")
                }
            )
            
            interview_data = {}
            if create_response.status_code == 200:
                interview_data = create_response.json().get("data", {})
            
            technical_interview_id = interview_data.get("technical_interview_id", str(uuid4()))
            
            # Store session
            active_sessions[session_id] = InterviewSession(
                session_id=session_id,
                technical_interview_id=technical_interview_id,
                job_details=job_details,
                candidate_info=candidate_info,
                system_instruction=system_instruction
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "technical_interview_id": technical_interview_id,
                "interview_url": f"http://localhost:8100/interview/{session_id}",
                "job_title": job_details.get("title", "Technical Position"),
                "candidate_name": f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}"
            }
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Service connection error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create interview: {str(e)}")


@app.post("/api/login/{job_requirement_id}")
async def candidate_login(job_requirement_id: str, request: LoginRequest):
    """
    Candidate login for technical interview.
    Validates credentials and creates interview session.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Login via main service
            login_response = await client.post(
                f"{MAIN_SERVICE_URL}/technical-interview/login",
                json={
                    "job_requirement_id": job_requirement_id,
                    "email": request.email,
                    "password": request.password
                }
            )
            
            if login_response.status_code != 200:
                error_detail = login_response.json().get("detail", "Login failed")
                raise HTTPException(status_code=401, detail=error_detail)
            
            data = login_response.json().get("data", {})
            
            session_id = data.get("interview_session_id")
            technical_interview_id = data.get("technical_interview_id")
            job_details = data.get("job_details", {})
            candidate_info = data.get("candidate_info", {})
            system_instruction = data.get("system_instruction", "")
            
            # Store session locally
            active_sessions[session_id] = InterviewSession(
                session_id=session_id,
                technical_interview_id=technical_interview_id,
                job_details=job_details,
                candidate_info=candidate_info,
                system_instruction=system_instruction
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "technical_interview_id": technical_interview_id,
                "interview_url": f"http://localhost:8100/interview/{session_id}",
                "job_details": job_details,
                "candidate_info": candidate_info
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information"""
    session = active_sessions.get(session_id)
    if not session:
        # Try to fetch from main service
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{MAIN_SERVICE_URL}/technical-interview/session/{session_id}"
                )
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    # Create local session
                    active_sessions[session_id] = InterviewSession(
                        session_id=session_id,
                        technical_interview_id=data.get("technical_interview_id", ""),
                        job_details=data.get("job_details", {}),
                        candidate_info=data.get("candidate_info", {}),
                        system_instruction=data.get("system_instruction", "")
                    )
                    session = active_sessions[session_id]
                else:
                    raise HTTPException(status_code=404, detail="Session not found")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "session_id": session.session_id,
        "technical_interview_id": session.technical_interview_id,
        "job_details": session.job_details,
        "candidate_info": session.candidate_info
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket proxy between frontend and Gemini Multimodal Live API
    """
    await websocket.accept()
    print(f"✅ Frontend WebSocket connected for session: {session_id}")
    
    # Get session
    session = active_sessions.get(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Invalid session"})
        await websocket.close()
        return
    
    gemini_ws = None
    receive_task = None
    send_task = None
    max_retries = 3
    retry_count = 0
    
    session.started_at = datetime.now(timezone.utc)
    
    async def connect_to_gemini():
        """Connect to Gemini WebSocket with retry logic"""
        nonlocal gemini_ws
        import websockets
        
        print("🔗 Connecting to Gemini 2.5 Flash Multimodal Live API...")
        gemini_ws = await websockets.connect(
            GEMINI_WS_URL,
            additional_headers={"Content-Type": "application/json"},
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
            max_size=10 * 1024 * 1024
        )
        print("✅ Connected to Gemini API")
        
        # Send BidiGenerateContentSetup message with custom system instruction
        setup_message = {
            "setup": {
                "model": GEMINI_MODEL,
                "generation_config": GENERATION_CONFIG,
                "system_instruction": {
                    "parts": [{"text": session.system_instruction}]
                }
            }
        }
        
        await gemini_ws.send(json.dumps(setup_message))
        print("📤 Sent BidiGenerateContentSetup to Gemini")
        
        session.token_usage["input_tokens"] += len(session.system_instruction) // 4
        
        # Wait for setup complete response
        setup_response = await asyncio.wait_for(gemini_ws.recv(), timeout=30)
        setup_data = json.loads(setup_response)
        
        if "setupComplete" not in setup_data:
            raise Exception(f"Setup failed: {setup_data}")
        
        print("✅ Gemini setup complete - Ready for interview!")
        return True
    
    try:
        # Initial connection
        await connect_to_gemini()
        
        await websocket.send_json({
            "type": "setup_complete",
            "message": "Connected! Ready to start the interview."
        })
        
        # Notify main service that interview started
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{MAIN_SERVICE_URL}/technical-interview/start/{session.technical_interview_id}"
                )
        except Exception as e:
            print(f"⚠️ Could not notify main service of interview start: {e}")
        
        # Send initial prompt to trigger AI greeting
        candidate_name = session.candidate_info.get("name", "Candidate")
        initial_prompt = {
            "clientContent": {
                "turns": [{
                    "role": "user",
                    "parts": [{"text": f"The candidate {candidate_name} has joined. Please start the interview with a warm greeting and introduce yourself."}]
                }],
                "turnComplete": True
            }
        }
        await gemini_ws.send(json.dumps(initial_prompt))
        print("📤 Sent initial prompt to trigger AI greeting")
        
        # Create tasks for bidirectional communication
        async def receive_from_gemini():
            """Receive audio/events from Gemini and forward to frontend"""
            nonlocal session, gemini_ws, retry_count
            interview_end_detected = False
            
            while True:
                try:
                    async for message in gemini_ws:
                        data = json.loads(message)
                        
                        # Handle user speech transcription from Gemini
                        if "serverContent" in data:
                            server_content = data["serverContent"]
                            
                            # Check for input (user) audio transcription
                            if "inputTranscript" in server_content:
                                user_text = server_content["inputTranscript"]
                                if user_text and user_text.strip():
                                    session.transcript.append({
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                        "speaker": "candidate",
                                        "text": user_text
                                    })
                                    print(f"📝 User: {user_text[:80]}...")
                                    await websocket.send_json({
                                        "type": "transcript",
                                        "text": user_text,
                                        "speaker": "candidate"
                                    })
                            
                            if server_content.get("interrupted"):
                                print("🛑 Gemini detected interruption")
                                await websocket.send_json({"type": "interrupted"})
                                continue
                            
                            if server_content.get("turnComplete"):
                                print("✅ AI turn complete")
                                await websocket.send_json({"type": "turn_complete"})
                                
                                # Check if interview ended based on last AI message
                                if interview_end_detected:
                                    print("🏁 Interview end detected - sending completion signal")
                                    await asyncio.sleep(2)  # Wait for audio to finish
                                    await websocket.send_json({"type": "interview_complete"})
                                continue
                            
                            model_turn = server_content.get("modelTurn", {})
                            parts = model_turn.get("parts", [])
                        
                        for part in parts:
                            if "inlineData" in part:
                                inline_data = part["inlineData"]
                                mime_type = inline_data.get("mimeType", "")
                                
                                if mime_type.startswith("audio/"):
                                    audio_b64 = inline_data.get("data", "")
                                    if audio_b64:
                                        audio_bytes = len(audio_b64) * 3 // 4
                                        audio_duration = audio_bytes / 48000
                                        session.token_usage["audio_output_seconds"] += audio_duration
                                        session.token_usage["output_tokens"] += int(audio_duration * 25)
                                        
                                        await websocket.send_json({
                                            "type": "audio",
                                            "data": audio_b64,
                                            "mimeType": mime_type
                                        })
                            
                            if "text" in part:
                                text = part["text"]
                                text_lower = text.lower()
                                session.token_usage["output_tokens"] += len(text) // 4
                                session.transcript.append({
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "speaker": "ai",
                                    "text": text
                                })
                                print(f"📝 AI: {text[:80]}...")
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": text,
                                    "speaker": "ai"
                                })
                                
                                # Detect interview end phrases
                                end_phrases = [
                                    "thank you for your time",
                                    "thanks for your time",
                                    "interview is complete",
                                    "that concludes",
                                    "we'll get back to you",
                                    "we will get back to you",
                                    "all the best",
                                    "good luck",
                                    "wish you all the best",
                                    "results soon",
                                    "have a great day",
                                    "interview has ended",
                                    "end of interview"
                                ]
                                for phrase in end_phrases:
                                    if phrase in text_lower:
                                        print(f"🏁 Detected interview end phrase: '{phrase}'")
                                        interview_end_detected = True
                                        break
                    
                    # Connection closed normally, exit loop
                    break
                                
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"🔌 Gemini connection closed: {e}")
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        print(f"❌ Max retries ({max_retries}) reached. Ending interview.")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Connection lost. Please try again."
                        })
                        break
                    
                    # Try to reconnect
                    print(f"🔄 Attempting reconnection ({retry_count}/{max_retries})...")
                    await websocket.send_json({
                        "type": "status",
                        "message": "Reconnecting..."
                    })
                    
                    try:
                        await asyncio.sleep(2)  # Wait before reconnecting
                        await connect_to_gemini()
                        print("✅ Reconnected to Gemini!")
                        await websocket.send_json({
                            "type": "status",
                            "message": "Reconnected! Please continue."
                        })
                        # Continue the while loop to resume receiving
                        continue
                    except Exception as reconnect_error:
                        print(f"❌ Reconnection failed: {reconnect_error}")
                        continue  # Try again
                        
                except Exception as e:
                    print(f"❌ Error receiving from Gemini: {e}")
                    break
        
        async def send_to_gemini():
            """Receive audio/commands from frontend and forward to Gemini"""
            nonlocal gemini_ws
            try:
                while True:
                    data = await websocket.receive_json()
                    msg_type = data.get("type")
                    
                    if msg_type == "audio":
                        audio_b64 = data.get("data", "")
                        
                        if audio_b64:
                            audio_bytes = len(audio_b64) * 3 // 4
                            audio_duration = audio_bytes / 32000
                            session.token_usage["audio_input_seconds"] += audio_duration
                            session.token_usage["input_tokens"] += int(audio_duration * 25)
                        
                        realtime_input = {
                            "realtimeInput": {
                                "mediaChunks": [{
                                    "mimeType": "audio/pcm;rate=16000",
                                    "data": audio_b64
                                }]
                            }
                        }
                        
                        try:
                            await gemini_ws.send(json.dumps(realtime_input))
                        except Exception as send_error:
                            # Connection may be closed, just skip this audio chunk
                            pass
                    
                    elif msg_type == "transcript":
                        # User transcript from browser speech recognition
                        text = data.get("text", "")
                        if text:
                            session.transcript.append({
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "speaker": "candidate",
                                "text": text
                            })
                            print(f"📝 User: {text[:80]}...")
                    
                    elif msg_type == "stop":
                        print("🛑 Stop signal received from frontend")
                        break
                        
            except WebSocketDisconnect:
                print("🔌 Frontend disconnected")
            except Exception as e:
                print(f"❌ Error sending to Gemini: {e}")
        
        async def heartbeat():
            """Send periodic heartbeat to keep connection alive"""
            nonlocal gemini_ws
            try:
                while True:
                    await asyncio.sleep(15)  # Every 15 seconds
                    try:
                        keepalive = {
                            "realtimeInput": {
                                "mediaChunks": []
                            }
                        }
                        await gemini_ws.send(json.dumps(keepalive))
                        print("💓 Heartbeat sent")
                    except Exception:
                        # Connection closed, heartbeat will stop when task is cancelled
                        pass
            except asyncio.CancelledError:
                pass
        
        receive_task = asyncio.create_task(receive_from_gemini())
        send_task = asyncio.create_task(send_to_gemini())
        heartbeat_task = asyncio.create_task(heartbeat())
        
        done, pending = await asyncio.wait(
            [receive_task, send_task, heartbeat_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
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
        # Calculate interview duration
        interview_duration = 0
        if session.started_at:
            interview_duration = int((datetime.now(timezone.utc) - session.started_at).total_seconds())
        
        # Save interview results to main service
        try:
            await save_interview_results(session, interview_duration)
        except Exception as e:
            print(f"❌ Failed to save interview results: {e}")
        
        if gemini_ws:
            await gemini_ws.close()
            print("🔌 Gemini WebSocket closed")
        
        try:
            await websocket.close()
        except:
            pass
        
        # Print token usage summary
        print("\n" + "=" * 60)
        print("📊 INTERVIEW SESSION TOKEN USAGE SUMMARY")
        print("=" * 60)
        print(f"📥 Input Tokens:  {session.token_usage['input_tokens']:,}")
        print(f"📤 Output Tokens: {session.token_usage['output_tokens']:,}")
        print(f"🔢 Total Tokens:  {session.token_usage['input_tokens'] + session.token_usage['output_tokens']:,}")
        print("-" * 60)
        print(f"🎤 Audio Input:   {session.token_usage['audio_input_seconds']:.2f} seconds")
        print(f"🔊 Audio Output:  {session.token_usage['audio_output_seconds']:.2f} seconds")
        print(f"⏱️  Duration:     {interview_duration} seconds")
        print("=" * 60 + "\n")
        
        print("👋 Session ended")


async def save_interview_results(session: InterviewSession, duration: int):
    """Save interview results to main service after AI evaluation"""
    try:
        # First, evaluate the interview using AI
        print("🤖 Evaluating interview with AI...")
        await evaluate_interview_with_ai(session, duration)
        print("✅ AI evaluation complete")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Calculate average response time
            avg_response_time = (
                sum(session.response_times) / len(session.response_times) 
                if session.response_times else 0.0
            )
            
            # Determine overall rating based on score
            overall_score = session.scores["overall_score"]
            if overall_score >= 85:
                overall_rating = "excellent"
            elif overall_score >= 70:
                overall_rating = "good"
            elif overall_score >= 55:
                overall_rating = "average"
            elif overall_score >= 40:
                overall_rating = "below_average"
            else:
                overall_rating = "poor"
            
            # Determine result
            result = "pass" if overall_score >= 50 else "fail"
            
            # Prepare comprehensive completion data
            completion_data = {
                # Duration
                "interview_duration_seconds": duration,
                
                # Overall Scores
                "overall_score": session.scores["overall_score"],
                "overall_rating": overall_rating,
                
                # Technical Knowledge Scores
                "technical_knowledge_score": session.scores["technical_knowledge_score"],
                "domain_expertise_score": session.scores["domain_expertise_score"],
                
                # Communication Scores
                "communication_score": session.scores["communication_score"],
                "language_proficiency_score": session.scores["language_proficiency_score"],
                
                # Behavioral Scores
                "confidence_score": session.scores["confidence_score"],
                "professionalism_score": session.scores["professionalism_score"],
                
                # Response Quality Scores
                "response_relevance_score": session.scores["response_relevance_score"],
                "response_depth_score": session.scores["response_depth_score"],
                "response_clarity_score": session.scores["response_clarity_score"],
                
                # Engagement Metrics
                "engagement_score": session.scores["engagement_score"],
                
                # Question Statistics
                "total_questions_asked": session.questions_asked,
                "questions_answered": session.questions_answered,
                "questions_skipped": session.questions_skipped,
                
                # Time Metrics
                "average_response_time_seconds": avg_response_time,
                "total_speaking_time_seconds": session.token_usage["audio_input_seconds"],
                
                # Detailed JSON Data
                "interview_transcript": session.transcript,
                "skills_assessment": session.skills_assessment,
                "candidate_strengths": session.candidate_strengths,
                "candidate_weaknesses": session.candidate_weaknesses,
                
                # AI Recommendations
                "ai_recommendation": session.ai_recommendation,
                "ai_recommendation_reason": session.ai_recommendation_reason,
                "ai_feedback_summary": session.ai_feedback_summary,
                "improvement_areas": session.improvement_areas,
                
                # Interview Metadata
                "interview_language": "English",
                "languages_used": ["English"],
                "ai_model_used": GEMINI_MODEL,
                
                # Token Usage
                "input_tokens_used": session.token_usage["input_tokens"],
                "output_tokens_used": session.token_usage["output_tokens"],
                "audio_input_seconds": session.token_usage["audio_input_seconds"],
                "audio_output_seconds": session.token_usage["audio_output_seconds"],
                
                # Final Result
                "result": result,
                "passed_threshold": 50.0
            }
            
            response = await client.post(
                f"{MAIN_SERVICE_URL}/technical-interview/complete/{session.technical_interview_id}",
                json=completion_data
            )
            
            if response.status_code == 200:
                print("✅ Interview results saved successfully")
                print(f"   📊 Overall Score: {overall_score:.1f}/100 ({overall_rating})")
                print(f"   🎯 Result: {result.upper()}")
                print(f"   💡 Recommendation: {session.ai_recommendation}")
            else:
                print(f"⚠️ Failed to save results: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"❌ Error saving interview results: {e}")
        import traceback
        traceback.print_exc()


async def evaluate_interview_with_ai(session: InterviewSession, duration: int):
    """
    Use Gemini API to evaluate the interview transcript and generate scores.
    This analyzes the conversation and provides comprehensive evaluation.
    """
    import google.generativeai as genai
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Prepare transcript for analysis
    transcript_text = "\n".join([
        f"[{entry['speaker'].upper()}]: {entry['text']}"
        for entry in session.transcript
    ])
    
    # Get job context
    job_title = session.job_details.get("title", "Technical Position")
    required_skills = []
    for req in session.job_details.get("requirements", []):
        if isinstance(req, dict):
            skill = req.get("skill", "")
            if skill:
                required_skills.append(skill)
    
    skills_str = ", ".join(required_skills[:10]) if required_skills else "general technical skills"
    
    evaluation_prompt = f"""You are an expert interview evaluator. Analyze this technical interview transcript and provide a comprehensive evaluation.

JOB CONTEXT:
- Position: {job_title}
- Required Skills: {skills_str}
- Interview Duration: {duration} seconds

INTERVIEW TRANSCRIPT:
{transcript_text}

Provide your evaluation in the following JSON format ONLY (no other text):
{{
    "scores": {{
        "overall_score": <0-100>,
        "technical_knowledge_score": <0-100>,
        "domain_expertise_score": <0-100>,
        "communication_score": <0-100>,
        "language_proficiency_score": <0-100>,
        "confidence_score": <0-100>,
        "professionalism_score": <0-100>,
        "response_relevance_score": <0-100>,
        "response_depth_score": <0-100>,
        "response_clarity_score": <0-100>,
        "engagement_score": <0-100>
    }},
    "questions_asked": <number>,
    "questions_answered": <number>,
    "questions_skipped": <number>,
    "candidate_strengths": ["strength1", "strength2", ...],
    "candidate_weaknesses": ["weakness1", "weakness2", ...],
    "improvement_areas": ["area1", "area2", ...],
    "skills_assessment": [
        {{"skill_name": "skill", "proficiency_level": "beginner/intermediate/advanced", "score": <0-100>, "evidence": "observation"}}
    ],
    "ai_recommendation": "strongly_recommend/recommend/neutral/not_recommend",
    "ai_recommendation_reason": "detailed reason for recommendation",
    "ai_feedback_summary": "2-3 sentence summary of candidate performance"
}}

EVALUATION CRITERIA:
- Technical Knowledge: Depth of technical understanding demonstrated
- Domain Expertise: Specific knowledge related to job requirements
- Communication: Clarity and effectiveness of communication
- Language Proficiency: Grammar, vocabulary, fluency
- Confidence: Self-assurance in responses
- Professionalism: Professional demeanor throughout
- Response Relevance: How relevant answers were to questions
- Response Depth: Thoroughness of answers
- Response Clarity: Clarity of responses
- Engagement: Active participation in the interview

Be fair but critical. Base all scores on actual evidence from the transcript."""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(evaluation_prompt)
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Extract JSON if wrapped in code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        evaluation = json.loads(response_text)
        
        # Update session with evaluation results
        if "scores" in evaluation:
            for key, value in evaluation["scores"].items():
                if key in session.scores:
                    session.scores[key] = float(value)
        
        session.questions_asked = evaluation.get("questions_asked", 0)
        session.questions_answered = evaluation.get("questions_answered", 0)
        session.questions_skipped = evaluation.get("questions_skipped", 0)
        session.candidate_strengths = evaluation.get("candidate_strengths", [])
        session.candidate_weaknesses = evaluation.get("candidate_weaknesses", [])
        session.improvement_areas = evaluation.get("improvement_areas", [])
        session.skills_assessment = evaluation.get("skills_assessment", [])
        session.ai_recommendation = evaluation.get("ai_recommendation", "neutral")
        session.ai_recommendation_reason = evaluation.get("ai_recommendation_reason", "")
        session.ai_feedback_summary = evaluation.get("ai_feedback_summary", "")
        
        print(f"📊 AI Evaluation Results:")
        print(f"   Overall Score: {session.scores['overall_score']:.1f}/100")
        print(f"   Technical: {session.scores['technical_knowledge_score']:.1f}")
        print(f"   Communication: {session.scores['communication_score']:.1f}")
        print(f"   Recommendation: {session.ai_recommendation}")
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse AI evaluation JSON: {e}")
        print(f"   Response was: {response_text[:500]}...")
        # Set default scores if parsing fails
        _set_default_scores(session, duration)
    except Exception as e:
        print(f"⚠️ AI evaluation failed: {e}")
        # Set default scores based on basic metrics
        _set_default_scores(session, duration)


def _set_default_scores(session: InterviewSession, duration: int):
    """Set default scores based on basic metrics when AI evaluation fails"""
    # Calculate basic scores from transcript length and duration
    transcript_length = len(session.transcript)
    candidate_responses = [t for t in session.transcript if t["speaker"] == "candidate"]
    
    # More responses = more engagement
    base_score = min(70, 40 + (len(candidate_responses) * 3))
    
    # Longer responses = better depth
    total_response_length = sum(len(t["text"]) for t in candidate_responses)
    depth_bonus = min(15, total_response_length // 200)
    
    default_score = base_score + depth_bonus
    
    session.scores["overall_score"] = default_score
    session.scores["technical_knowledge_score"] = default_score
    session.scores["communication_score"] = default_score + 5
    session.scores["confidence_score"] = default_score
    session.scores["engagement_score"] = min(85, default_score + 10)
    session.scores["response_clarity_score"] = default_score
    
    # Copy default to other scores
    for key in session.scores:
        if session.scores[key] == 0.0:
            session.scores[key] = default_score
    
    session.questions_asked = transcript_length // 2
    session.questions_answered = len(candidate_responses)
    session.ai_feedback_summary = "Interview completed. Automatic scoring applied due to evaluation service unavailability."
    session.ai_recommendation = "neutral"


def generate_system_instruction(job_details: dict, candidate_info: dict) -> str:
    """Generate customized system instruction based on job and candidate"""
    title = job_details.get("title", "Technical Position")
    department = job_details.get("department", "Technology")
    description = job_details.get("description", "")
    requirements = job_details.get("requirements", [])
    experience = job_details.get("experience", {})
    
    candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip() or "Candidate"
    candidate_skills = candidate_info.get("skills", [])
    candidate_resume = candidate_info.get("resume_text", "")
    
    # Extract skills from requirements
    skills = []
    for req in requirements:
        if isinstance(req, dict):
            skill = req.get("skill", "")
            if skill:
                skills.append(skill)
    
    skills_str = ", ".join(skills[:10]) if skills else "general technical skills"
    candidate_skills_str = ", ".join(candidate_skills[:10]) if candidate_skills else "various skills"
    
    exp_min = experience.get("minYears", 0) if experience else 0
    exp_max = experience.get("maxYears", 5) if experience else 5
    
    # Resume section
    resume_section = ""
    if candidate_resume:
        resume_section = f"Resume highlights: {candidate_resume[:1000]}"
    
    # System prompt with clear rules
    return f"""You are a Senior Technical Recruiter conducting a voice interview for "{title}" position.

CANDIDATE: {candidate_name}
SKILLS REQUIRED: {skills_str}
EXPERIENCE: {exp_min}-{exp_max} years
{resume_section}

INTERVIEW STRUCTURE (MUST ASK MINIMUM 10 QUESTIONS):
- Questions 1-2: Self introduction, background
- Questions 3-5: Technical skills from resume ({skills_str})
- Questions 6-8: Core concepts, problem-solving
- Questions 9-10: Behavioral, situational
- Questions 11+: Follow-ups based on answers

LANGUAGE RULES (CRITICAL):
- If candidate speaks Hindi: Reply in Hindi immediately
- If candidate speaks Gujarati: Reply in Gujarati immediately  
- If candidate mixes languages: Match their language
- Example: Candidate says "मैंने Python में काम किया है" → You reply in Hindi
- Example: Candidate says "મેં Flask માં API બનાવ્યું છે" → You reply in Gujarati

INTERVIEW RULES:
1. Ask ONE question, wait for complete answer
2. After each answer, acknowledge briefly then ask next question
3. If answer unclear: "Could you please repeat or explain that?"
4. If wrong answer: Briefly note correct approach, move on
5. If off-topic: "Let's continue with the interview questions"
6. Keep your responses SHORT (1-2 sentences max)
7. Do NOT use markdown or special formatting
8. Speak naturally like a real interviewer

START: Greet {candidate_name.split()[0] if candidate_name else 'the candidate'} warmly, introduce yourself briefly, ask them to introduce themselves.

END: After 10+ questions or 10+ mins, say "Thank you for your time, we'll get back to you soon" and stop."""


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "technical-interview-service",
        "port": 8100,
        "model": GEMINI_MODEL,
        "active_sessions": len(active_sessions)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
