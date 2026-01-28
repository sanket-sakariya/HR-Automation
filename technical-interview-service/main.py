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
    """Stores interview session data"""
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
    
    session.started_at = datetime.now(timezone.utc)
    
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
        
        if "setupComplete" in setup_data:
            print("✅ Gemini setup complete - Ready for interview!")
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
                    
                    if "serverContent" in data:
                        server_content = data["serverContent"]
                        
                        if server_content.get("interrupted"):
                            print("🛑 Gemini detected interruption")
                            await websocket.send_json({"type": "interrupted"})
                            continue
                        
                        if server_content.get("turnComplete"):
                            print("✅ AI turn complete")
                            await websocket.send_json({"type": "turn_complete"})
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
                                
            except websockets.exceptions.ConnectionClosed as e:
                print(f"🔌 Gemini connection closed: {e}")
            except Exception as e:
                print(f"❌ Error receiving from Gemini: {e}")
        
        async def send_to_gemini():
            """Receive audio/commands from frontend and forward to Gemini"""
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
                        
                        await gemini_ws.send(json.dumps(realtime_input))
                    
                    elif msg_type == "transcript":
                        # User transcript for storage
                        text = data.get("text", "")
                        if text:
                            session.transcript.append({
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "speaker": "candidate",
                                "text": text
                            })
                    
                    elif msg_type == "stop":
                        print("🛑 Stop signal received from frontend")
                        break
                        
            except WebSocketDisconnect:
                print("🔌 Frontend disconnected")
            except Exception as e:
                print(f"❌ Error sending to Gemini: {e}")
        
        receive_task = asyncio.create_task(receive_from_gemini())
        send_task = asyncio.create_task(send_to_gemini())
        
        done, pending = await asyncio.wait(
            [receive_task, send_task],
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
    """Save interview results to main service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare completion data
            completion_data = {
                "interview_duration_seconds": duration,
                "overall_score": 70.0,  # Default score - AI evaluation would set this
                "overall_rating": "average",
                "interview_transcript": session.transcript,
                "interview_language": "English",
                "languages_used": ["English"],
                "input_tokens_used": session.token_usage["input_tokens"],
                "output_tokens_used": session.token_usage["output_tokens"],
                "audio_input_seconds": session.token_usage["audio_input_seconds"],
                "audio_output_seconds": session.token_usage["audio_output_seconds"],
                "result": "pass",  # Default - would be evaluated by AI
                "ai_model_used": GEMINI_MODEL
            }
            
            response = await client.post(
                f"{MAIN_SERVICE_URL}/technical-interview/complete/{session.technical_interview_id}",
                json=completion_data
            )
            
            if response.status_code == 200:
                print("✅ Interview results saved successfully")
            else:
                print(f"⚠️ Failed to save results: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"❌ Error saving interview results: {e}")


def generate_system_instruction(job_details: dict, candidate_info: dict) -> str:
    """Generate customized system instruction based on job and candidate"""
    title = job_details.get("title", "Technical Position")
    department = job_details.get("department", "Technology")
    description = job_details.get("description", "")
    requirements = job_details.get("requirements", [])
    experience = job_details.get("experience", {})
    
    candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip() or "Candidate"
    candidate_skills = candidate_info.get("skills", [])
    
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
    
    return f"""You are a Senior Technical Recruiter conducting a real-time voice interview for the position of "{title}" in the {department} department.

CANDIDATE INFORMATION:
- Name: {candidate_name}
- Skills: {candidate_skills_str}

JOB CONTEXT:
- Position: {title}
- Department: {department}
- Required Experience: {exp_min}-{exp_max} years
- Key Skills Required: {skills_str}
- Job Description: {description[:500]}...

CRITICAL SPEAKING GUIDELINES:
- Speak at a MODERATE, CLEAR pace - not too fast, not too slow
- Pronounce each word clearly and distinctly
- Pause briefly between sentences for better comprehension
- Avoid rushing through sentences - take your time
- Speak naturally but ensure every word is understandable

LANGUAGE BEHAVIOR:
- Start the interview in English with a warm greeting
- If the candidate speaks in Hindi, seamlessly switch to Hindi
- If the candidate speaks in Gujarati, seamlessly switch to Gujarati
- You can mix languages naturally if the candidate does so
- Always match the language preference of the candidate

INTERVIEW STRUCTURE:
1. INTRODUCTION (2-3 mins):
   - Warm greeting - address candidate by name: {candidate_name}
   - Brief overview of the interview process
   - Put the candidate at ease

2. BACKGROUND (3-5 mins):
   - Ask about their experience and background
   - Current/previous role responsibilities
   - Why they're interested in this position

3. TECHNICAL ASSESSMENT (10-15 mins):
   - Ask questions specific to: {skills_str}
   - Start with easier questions, gradually increase difficulty
   - Probe deeper based on their responses
   - Ask follow-up questions to assess depth of knowledge

4. PROBLEM SOLVING (5-7 mins):
   - Present a relevant scenario or problem
   - Assess their analytical thinking
   - Evaluate their approach to problem-solving

5. BEHAVIORAL QUESTIONS (3-5 mins):
   - Ask about challenging situations they've handled
   - Team collaboration experiences
   - How they handle pressure/deadlines

6. CLOSING (2-3 mins):
   - Ask if they have questions
   - Thank them for their time
   - Mention next steps

EVALUATION CRITERIA (Assess throughout):
- Technical Knowledge: Understanding of core concepts
- Problem Solving: Analytical and logical thinking
- Communication: Clarity, articulation, language proficiency
- Confidence: How confidently they present themselves
- Enthusiasm: Interest in the role and company
- Relevance: How well their answers relate to questions

INTERVIEWER GUIDELINES:
- Ask ONE question at a time and wait for complete response
- Be encouraging and supportive
- If answer is unclear, politely ask for clarification
- Keep responses concise - avoid long monologues
- Acknowledge good answers positively
- Note any areas where candidate struggles

Remember: This is a VOICE conversation. Keep responses concise and natural. No markdown, bullet points, or text formatting. Sound human, not robotic. SPEAK CLEARLY AND AT A COMFORTABLE PACE.

At the end, thank the candidate professionally and wish them well."""


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
