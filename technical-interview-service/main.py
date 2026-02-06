"""
Technical Interview Service - AI-Powered Real-time Interview Platform
Based on Google ADK architecture with Gemini 2.5 Flash Native Audio

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
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Deque, List, Dict, Any
from dataclasses import dataclass, field
from uuid import uuid4
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Load environment variables
env_file = Path(__file__).parent.parent / '.env.dev'
load_dotenv(env_file)
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-flash-preview-native-audio-dialog")
MAIN_SERVICE_URL = os.getenv("MAIN_SERVICE_URL", "http://localhost:8888/interview-management-service/api/v1")

# Jitter Buffer Configuration
JITTER_BUFFER_MS = 50  # Reduced from 150ms for faster response
JITTER_BUFFER_MAX_CHUNKS = 5  # Reduced for lower latency
MIN_SPEECH_DURATION_MS = 150  # Reduced from 200ms for faster barge-in

if not GOOGLE_API_KEY:
    print("⚠️  WARNING: GOOGLE_API_KEY not found!")


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
        """Add audio chunk to buffer. Returns flushed audio if buffer is ready."""
        async with self._lock:
            self.sequence_counter += 1
            chunk = AudioChunk(data=data, sequence=self.sequence_counter)
            self.buffer.append(chunk)
            
            now = time.time()
            buffer_age_ms = (now - self._last_flush_time) * 1000
            
            should_flush = buffer_age_ms >= self.buffer_ms or len(self.buffer) >= self.max_chunks
            
            if should_flush and self.buffer:
                return await self._flush()
            
            return None
    
    async def _flush(self) -> bytes:
        """Flush all buffered chunks in sequence order."""
        sorted_chunks = sorted(self.buffer, key=lambda c: c.sequence)
        combined = b''.join(chunk.data for chunk in sorted_chunks)
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
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            energy = sum(abs(s) for s in samples[:100]) / max(100, len(samples[:100]))
            self._energy_history.append(energy)
            
            avg_energy = sum(self._energy_history) / len(self._energy_history)
            
            if avg_energy > energy_threshold:
                if self.speech_start_time is None:
                    self.speech_start_time = time.time()
                
                duration_ms = (time.time() - self.speech_start_time) * 1000
                if duration_ms >= self.min_duration_ms:
                    self.is_valid_speech = True
                    return True
                return False
            else:
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


def generate_system_instruction(job_details: dict, candidate_info: dict) -> str:
    """Generate dynamic system instruction based on job and candidate information."""
    job_title = job_details.get("title", "Technical Position")
    company_name = job_details.get("company_name", "the company")
    job_description = job_details.get("description", "")
    required_skills = job_details.get("required_skills", [])
    
    candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip()
    skills_str = ", ".join(required_skills) if isinstance(required_skills, list) else str(required_skills)
    
    return f"""
You are a professional technical recruiter conducting an interview for **{job_title}** at **{company_name}**.

## Candidate: {candidate_name or 'Candidate'}

## Job Details
- Position: {job_title}
- Description: {job_description or 'Technical role'}
- Required Skills: {skills_str or 'Technical skills'}

## Your Identity & Demeanor
- You are "Alex", a Senior Technical Recruiter with 10+ years of experience
- Maintain a professional yet approachable tone
- Be slightly rigorous but fair - you want to assess skills accurately
- Show genuine interest in the candidate's responses
- Provide brief acknowledgments before moving to the next question

## Interview Structure
1. **Opening (First interaction)**:
   - Greet {candidate_name or 'the candidate'} warmly
   - Introduce yourself briefly
   - Ask a warm-up question about their background

2. **Technical Assessment**:
   - Ask questions based on required skills: {skills_str}
   - Progress from basic to advanced concepts
   - Adapt difficulty based on responses

3. **Behavioral Questions**:
   - Problem-solving approach
   - Learning from mistakes
   - Team collaboration

## Important Behaviors
- **Language Adaptation**: START the interview in ENGLISH. Then DETECT the language the candidate uses to respond. If the candidate responds in Hindi, Gujarati, Spanish, French, German, or any other language, IMMEDIATELY switch to that language for ALL subsequent conversation. ALWAYS match the candidate's language choice. If they mix languages, you can do the same.

- **Barge-in Handling**: If the candidate starts speaking while you're talking, immediately stop and listen attentively. Acknowledge what they said before continuing.

- **Time Awareness**: Keep responses concise (20-40 seconds of speech). Don't monologue.

- **Encouragement**: Provide positive reinforcement for good answers.

## Response Format
- Speak naturally as in a real conversation
- Ask one question at a time
- Keep responses SHORT and conversational

## Interview Closure (VERY IMPORTANT)
When you have completed the interview (after asking sufficient questions, typically 8-12 questions or 10-15 minutes):
1. Thank the candidate for their time and responses
2. Summarize that you've gathered enough information
3. **IMPORTANT**: Say clearly "Thank you for completing this interview. Please click the 'End Session' button on your screen to submit your interview for evaluation. We will get back to you with the results soon."
4. Do NOT continue asking questions after this closing statement

Remember: You are conducting a VOICE interview. Keep responses brief and natural.
"""


# Store active sessions
active_sessions = {}


class InterviewSession:
    """Stores interview session data."""
    def __init__(
        self, 
        session_id: str, 
        job_details: dict, 
        candidate_info: dict, 
        system_instruction: str,
        technical_interview_id: str = None
    ):
        self.session_id = session_id
        self.job_details = job_details
        self.candidate_info = candidate_info
        self.system_instruction = system_instruction
        self.technical_interview_id = technical_interview_id
        self.transcript: List[Dict[str, Any]] = []  # Store conversation transcript
        self.started_at: datetime = None
        self.ended_at: datetime = None
        self.generated_scores: Dict[str, Any] = {}  # Store AI-generated scores
        self.interview_duration_seconds: int = 0


class RegisterSessionRequest(BaseModel):
    """Request to register an interview session."""
    session_id: str
    job_details: dict
    candidate_info: dict
    system_instruction: str
    technical_interview_id: Optional[str] = None


class StartInterviewRequest(BaseModel):
    """Request to start a technical interview."""
    job_requirement_id: str
    email: str
    password: str


class CompleteInterviewRequest(BaseModel):
    """Request to complete a technical interview with AI-generated scores."""
    interview_session_id: str
    interview_duration_seconds: int = Field(..., description="Total interview duration in seconds")
    
    # Overall Scores (AI will generate these)
    overall_score: float = Field(..., ge=0, le=100)
    overall_rating: str = Field(..., description="excellent, good, average, below_average, poor")
    
    # Technical Knowledge Scores
    technical_knowledge_score: Optional[float] = Field(None, ge=0, le=100)
    domain_expertise_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Communication Scores
    communication_score: Optional[float] = Field(None, ge=0, le=100)
    language_proficiency_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Behavioral Scores
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    professionalism_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Response Quality Scores
    response_relevance_score: Optional[float] = Field(None, ge=0, le=100)
    response_depth_score: Optional[float] = Field(None, ge=0, le=100)
    response_clarity_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Question Statistics
    total_questions_asked: Optional[int] = None
    questions_answered: Optional[int] = None
    questions_skipped: Optional[int] = None
    follow_up_questions_asked: Optional[int] = None
    
    # Time Metrics
    average_response_time_seconds: Optional[float] = None
    total_speaking_time_seconds: Optional[float] = None
    
    # Engagement Metrics
    engagement_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Detailed JSON Data
    question_analysis: Optional[List[Dict[str, Any]]] = None
    skills_assessment: Optional[List[Dict[str, Any]]] = None
    candidate_strengths: Optional[List[str]] = None
    candidate_weaknesses: Optional[List[str]] = None
    
    # AI Recommendations
    ai_recommendation: Optional[str] = Field(None, description="strongly_recommend, recommend, neutral, not_recommend")
    ai_recommendation_reason: Optional[str] = None
    ai_feedback_summary: Optional[str] = None
    candidate_answer_summary: Optional[str] = Field(None, description="Summary of candidate's answers during interview")
    improvement_areas: Optional[List[str]] = None
    
    # Interview Metadata
    interview_language: Optional[str] = Field(None, description="Primary language: english, hindi, gujarati, mixed")
    languages_used: Optional[List[str]] = Field(None, description="List of languages used in interview")
    
    # Token Usage
    input_tokens: Optional[int] = Field(None, description="Total input tokens used")
    output_tokens: Optional[int] = Field(None, description="Total output tokens used")
    total_tokens: Optional[int] = Field(None, description="Total tokens used (input + output)")
    
    # Audio Duration
    audio_input_seconds: Optional[float] = Field(None, description="Estimated audio input duration in seconds")
    audio_output_seconds: Optional[float] = Field(None, description="Estimated audio output duration in seconds")
    
    # Transcript (interviewer speech only)
    interviewer_transcript: Optional[str] = Field(None, description="Full transcript of interviewer speech")
    
    # Final Result
    result: str = Field(..., description="'pass' or 'fail'")
    passed_threshold: Optional[float] = Field(None, description="Threshold score used for pass/fail")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("\n" + "=" * 75)
    print("🎤 TECHNICAL INTERVIEW SERVICE - Production Hardened")
    print("=" * 75)
    print(f"📡 Model: {MODEL_ID}")
    print(f"🔗 Main Service: {MAIN_SERVICE_URL}")
    print(f"⏱️  Jitter buffer: {JITTER_BUFFER_MS}ms")
    print(f"🎤 Min speech duration: {MIN_SPEECH_DURATION_MS}ms")
    if GOOGLE_API_KEY:
        print(f"✅ API Key loaded (ends with: ...{GOOGLE_API_KEY[-8:]})")
    else:
        print("⚠️  WARNING: GOOGLE_API_KEY not found!")
    print("=" * 75 + "\n")
    yield
    print("\n👋 Server shutting down...")


app = FastAPI(
    title="Technical Interview Service",
    description="Production-hardened real-time AI interview with jitter buffer and noise filtering",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class ProductionInterviewSession:
    """
    Production-hardened interview session with:
    - Jitter buffer for network stability
    - Speech activity tracking to filter noise
    - Barge-in mandate (min speech duration)
    - Binary audio passthrough (no base64 overhead)
    - Latency tracking
    - Transcript storage for score generation
    """
    
    def __init__(self, websocket: WebSocket, system_instruction: str, job_details: dict, candidate_info: dict, parent_session: InterviewSession = None):
        self.websocket = websocket
        self.system_instruction = system_instruction
        self.job_details = job_details
        self.candidate_info = candidate_info
        self.parent_session = parent_session  # Reference to InterviewSession for storing transcript
        self.session = None
        self.is_active = False
        self.stop_event = asyncio.Event()
        self.receive_task: Optional[asyncio.Task] = None
        self.jitter_flush_task: Optional[asyncio.Task] = None
        self.is_ai_speaking = False
        self.ws_closed = False
        
        # Production stability components
        self.jitter_buffer = JitterBuffer(buffer_ms=JITTER_BUFFER_MS)
        self.speech_tracker = SpeechActivityTracker(min_duration_ms=MIN_SPEECH_DURATION_MS)
        
        # Latency tracking
        self.audio_send_times: Deque[float] = deque(maxlen=100)
        self.last_latency_ms: float = 0
        self.latency_samples: Deque[float] = deque(maxlen=20)
        
        # Simplified transcript storage - only interviewer output transcription
        self.interviewer_transcript: str = ""  # Full interviewer speech
        self.interview_start_time: float = None
        
        # Token tracking
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        
        # Buffer for accumulating streaming transcription
        self.current_interviewer_text: str = ""
    
    def finalize_transcript(self):
        """Finalize any remaining buffered transcript text."""
        if self.current_interviewer_text.strip():
            self.interviewer_transcript += self.current_interviewer_text.strip() + "\n\n"
            self.current_interviewer_text = ""
        
        # Sync to parent session
        if self.parent_session:
            self.parent_session.transcript = [{"speaker": "full_conversation", "text": self.interviewer_transcript}]
        
    async def send_json(self, msg_type: str, **kwargs):
        """Send JSON message to client."""
        if self.ws_closed:
            return
        try:
            await self.websocket.send_json({"type": msg_type, **kwargs})
        except Exception as e:
            self.ws_closed = True
    
    async def send_binary(self, data: bytes):
        """Send raw binary audio to client (zero-copy)."""
        if self.ws_closed:
            return
        try:
            await self.websocket.send_bytes(data)
        except Exception as e:
            self.ws_closed = True
    
    async def handle_gemini_stream(self):
        """Process Gemini responses with minimal latency and latency tracking."""
        try:
            while not self.stop_event.is_set() and not self.ws_closed:
                try:
                    async for response in self.session.receive():
                        if self.stop_event.is_set() or self.ws_closed:
                            break
                        
                        # Track response latency
                        if self.audio_send_times:
                            latency = (time.time() - self.audio_send_times[0]) * 1000
                            self.latency_samples.append(latency)
                            self.last_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
                        
                        if response.server_content:
                            content = response.server_content
                            
                            # Model turn complete - finalize interviewer transcript for this turn
                            if content.turn_complete:
                                # Save the interviewer's completed turn
                                if self.current_interviewer_text.strip():
                                    self.interviewer_transcript += self.current_interviewer_text.strip() + "\n\n"
                                    self.current_interviewer_text = ""
                                
                                self.is_ai_speaking = False
                                self.speech_tracker.reset()
                                await self.send_json("status", status="listening", latency_ms=round(self.last_latency_ms))
                            
                            # Stream audio chunks immediately (binary passthrough)
                            if content.model_turn and content.model_turn.parts:
                                for part in content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        self.is_ai_speaking = True
                                        await self.send_binary(part.inline_data.data)
                                        await self.send_json("status", status="speaking", latency_ms=round(self.last_latency_ms))
                            
                            # Stream transcription - accumulate for complete sentences
                            if content.output_transcription and content.output_transcription.text:
                                text = content.output_transcription.text
                                await self.send_json(
                                    "transcript",
                                    role="interviewer",
                                    text=text
                                )
                                # Accumulate transcription (will be saved on turn_complete)
                                self.current_interviewer_text += text
                                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if not self.stop_event.is_set() and not self.ws_closed:
                        print(f"Gemini stream error: {e}")
                        await self.send_json("error", message=str(e))
                    break
                    
        except Exception as e:
            print(f"Stream handler error: {e}")
        finally:
            print("📡 Gemini stream ended")
    
    async def generate_and_store_scores(self):
        """Generate AI-based evaluation scores using full conversation context."""
        try:
            # Finalize any remaining transcript
            self.finalize_transcript()
            
            if not self.interviewer_transcript.strip():
                print("⚠️ No transcript available for scoring")
                return
            
            print("🧠 Generating AI evaluation scores...")
            print(f"📝 Interviewer transcript length: {len(self.interviewer_transcript)} characters")
            
            # Get interview duration
            interview_duration = self.parent_session.interview_duration_seconds if self.parent_session else 0
            
            # Generate evaluation prompt - AI will extract Q&A from the full context
            evaluation_prompt = f"""
You are an expert technical interview evaluator. Analyze this interview and provide a comprehensive evaluation.

## Interview Context
- Position: {self.job_details.get('title', 'Technical Position')}
- Department: {self.job_details.get('department', 'Technology')}
- Required Skills: {self.job_details.get('requirements', [])}
- Candidate Name: {self.candidate_info.get('name', 'Candidate')}
- Interview Duration: {interview_duration} seconds

## INTERVIEWER'S SPEECH (What the AI interviewer said during the interview)
{self.interviewer_transcript}

## YOUR TASK
Based on the interviewer's questions and statements above, you can infer what the candidate answered based on:
1. The interviewer's acknowledgments and follow-up questions
2. The flow of conversation (interviewer thanking for answers, asking follow-ups)
3. Any paraphrasing the interviewer did of candidate responses

## EXTRACT QUESTION-ANSWER PAIRS
From the interviewer transcript, identify:
1. Each question the interviewer asked
2. Whether the candidate likely answered well (based on interviewer's positive responses) or poorly (based on interviewer asking for clarification or moving on quickly)

## Required JSON Response

{{
    "overall_score": <50-100>,
    "overall_rating": "<excellent if score>=85 | good if score>=70 | average if score>=55 | below_average if score>=40 | poor if score<40>",
    
    "technical_knowledge_score": <0-100>,
    "domain_expertise_score": <0-100>,
    "communication_score": <0-100>,
    "language_proficiency_score": <0-100>,
    "confidence_score": <0-100>,
    "professionalism_score": <0-100>,
    "response_relevance_score": <0-100>,
    "response_depth_score": <0-100>,
    "response_clarity_score": <0-100>,
    "engagement_score": <0-100>,
    
    "candidate_strengths": ["List 3-5 strengths inferred from the interview flow"],
    "candidate_weaknesses": ["List 1-3 areas for improvement"],
    
    "candidate_answer_summary": "<3-4 sentence summary of what the candidate likely discussed based on the interviewer's responses>",
    
    "ai_recommendation": "<strongly_recommend|recommend|neutral|not_recommend>",
    "ai_recommendation_reason": "<2-3 sentences explaining the recommendation>",
    "ai_feedback_summary": "<4-5 sentence feedback for the candidate>",
    
    "improvement_areas": ["List 2-3 specific areas to improve"],
    
    "skills_assessment": [
        {{"skill_name": "<skill>", "proficiency_level": "<advanced|intermediate|beginner>", "score": <0-100>, "evidence": "<brief note>"}}
    ],
    
    "question_analysis": [
        {{"question": "<question asked by interviewer>", "inferred_answer_quality": "<good|average|poor>", "score": <0-100>, "reasoning": "<why you inferred this quality>"}}
    ],
    
    "total_questions_asked": <count of questions in transcript>,
    "questions_answered": <count of questions that got answers (good or average quality)>,
    "questions_skipped": <count of questions with poor/no answer>,
    "follow_up_questions_asked": <count of follow-up questions>,
    
    "interview_language": "<primary language used: english|hindi|gujarati|mixed>",
    "languages_used": ["list of languages detected in the interview"],
    
    "result": "<pass if overall_score>=55 | fail if overall_score<55>",
    "passed_threshold": 55
}}

Be FAIR in evaluation. If the interviewer seemed satisfied with responses, give good scores.
"""
            
            # Call Gemini API for evaluation with retry logic
            client = genai.Client(api_key=GOOGLE_API_KEY)
            
            evaluation_model = "gemini-2.5-flash"
            max_retries = 5
            response = None
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    print(f"🔄 Attempting evaluation with {evaluation_model} (attempt {attempt + 1}/{max_retries})...")
                    response = await client.aio.models.generate_content(
                        model=evaluation_model,
                        contents=evaluation_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    print(f"✅ Evaluation successful with {evaluation_model}")
                    break
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        wait_time = (2 ** attempt) * 5
                        print(f"⏳ Rate limited, waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"❌ Error with {evaluation_model}: {e}")
                        await asyncio.sleep(2)
            
            if not response:
                raise last_error or Exception("Evaluation failed after all retries")
            
            # Parse the response and extract token usage
            scores = json.loads(response.text)
            
            # Extract token counts from response metadata
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            
            # Add token counts and additional data
            scores["input_tokens"] = input_tokens + self.input_tokens
            scores["output_tokens"] = output_tokens + self.output_tokens
            scores["total_tokens"] = scores["input_tokens"] + scores["output_tokens"]
            scores["interview_duration_seconds"] = interview_duration
            scores["interviewer_transcript"] = self.interviewer_transcript
            
            # Calculate time metrics
            total_questions = scores.get("total_questions_asked", 0) or 0
            if total_questions > 0 and interview_duration > 0:
                scores["average_response_time_seconds"] = round(interview_duration / total_questions, 2)
            else:
                scores["average_response_time_seconds"] = 0
            
            # Estimate speaking time (roughly 70% of interview duration for active conversation)
            scores["total_speaking_time_seconds"] = round(interview_duration * 0.7, 2)
            
            # Estimate audio input/output seconds (audio is roughly same as speaking time split)
            scores["audio_input_seconds"] = round(interview_duration * 0.35, 2)  # Candidate speaking ~35% of time
            scores["audio_output_seconds"] = round(interview_duration * 0.35, 2)  # AI speaking ~35% of time
            
            # Ensure all required fields are present
            scores.setdefault("questions_answered", scores.get("total_questions_asked", 0) - scores.get("questions_skipped", 0))
            scores.setdefault("questions_skipped", 0)
            scores.setdefault("follow_up_questions_asked", 0)
            scores.setdefault("interview_language", "english")
            scores.setdefault("languages_used", ["english"])
            
            print(f"📊 Token Usage - Input: {scores['input_tokens']}, Output: {scores['output_tokens']}, Total: {scores['total_tokens']}")
            
            # Store in parent session
            if self.parent_session:
                self.parent_session.generated_scores = scores
                self.parent_session.started_at = datetime.fromtimestamp(self.interview_start_time, tz=timezone.utc) if self.interview_start_time else None
                print(f"✅ Scores generated - Overall: {scores.get('overall_score', 'N/A')}, Result: {scores.get('result', 'N/A')}")
                print(f"   Recommendation: {scores.get('ai_recommendation', 'N/A')}")
            
            # Send scores to client
            await self.send_json("scores_generated", scores=scores)
            
        except Exception as e:
            print(f"❌ Score generation error: {e}")
            import traceback
            traceback.print_exc()
            # Store default scores on error
            default_scores = {
                "overall_score": 50,
                "overall_rating": "average",
                "result": "fail",
                "error": str(e),
                "interview_duration_seconds": self.parent_session.interview_duration_seconds if self.parent_session else 0,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.input_tokens + self.output_tokens,
                "interviewer_transcript": self.interviewer_transcript
            }
            if self.parent_session:
                self.parent_session.generated_scores = default_scores
            await self.send_json("scores_generated", scores=default_scores, error=str(e))
    
    async def interrupt_ai(self):
        """Send interrupt signal to stop AI generation (barge-in)."""
        if self.session and self.is_ai_speaking:
            try:
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
        """Send audio through jitter buffer for network stability."""
        try:
            flushed_data = await self.jitter_buffer.add(audio_data)
            
            if flushed_data:
                self.audio_send_times.append(time.time())
                if len(self.audio_send_times) > 50:
                    self.audio_send_times.popleft()
                
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
            while not self.stop_event.is_set() and not self.ws_closed:
                await asyncio.sleep(self.jitter_buffer.buffer_ms / 1000)
                
                if self.stop_event.is_set() or self.ws_closed:
                    break
                    
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
        
        # Production-hardened config with barge-in mandate and input transcription
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
                parts=[types.Part(text=self.system_instruction)]
            ),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),  # Enable candidate speech transcription
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=150,
                    silence_duration_ms=600,
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
                while self.is_active and not self.stop_event.is_set() and not self.ws_closed:
                    try:
                        message = await asyncio.wait_for(
                            self.websocket.receive(),
                            timeout=0.1
                        )
                        
                        if message["type"] == "websocket.disconnect":
                            break
                        
                        # Binary audio - process through jitter buffer
                        if "bytes" in message:
                            audio_data = message["bytes"]
                            
                            # Check for valid speech using speech tracker
                            is_valid_speech = self.speech_tracker.update(audio_data)
                            
                            # Barge-in: only interrupt if valid continuous speech
                            if self.is_ai_speaking and is_valid_speech:
                                await self.interrupt_ai()
                            
                            # Send audio through jitter buffer
                            await self.send_buffered_audio(audio_data)
                        
                        # JSON commands
                        elif "text" in message:
                            try:
                                data = json.loads(message["text"])
                                
                                if data.get("type") == "start_interview":
                                    print("🎤 Starting interview...")
                                    self.interview_start_time = time.time()
                                    
                                    # Record start time in parent session
                                    if self.parent_session:
                                        self.parent_session.started_at = datetime.now(timezone.utc)
                                    
                                    candidate_name = self.candidate_info.get('first_name', 'the candidate')
                                    job_title = self.job_details.get('title', 'this position')
                                    
                                    await session.send(
                                        input=types.LiveClientContent(
                                            turns=[
                                                types.Content(
                                                    role="user",
                                                    parts=[types.Part(text=f"Begin the interview. Greet {candidate_name} warmly, introduce yourself as Alex the recruiter, mention you're interviewing them for {job_title}, and ask your first question.")]
                                                )
                                            ],
                                            turn_complete=True
                                        )
                                    )
                                
                                elif data.get("type") == "interrupt":
                                    if self.speech_tracker.is_valid_speech:
                                        await self.interrupt_ai()
                                
                                elif data.get("type") == "end_session":
                                    # Calculate interview duration and generate scores
                                    if self.interview_start_time:
                                        duration = int(time.time() - self.interview_start_time)
                                        if self.parent_session:
                                            self.parent_session.interview_duration_seconds = duration
                                            self.parent_session.ended_at = datetime.now(timezone.utc)
                                    
                                    # Generate and store scores before ending
                                    await self.generate_and_store_scores()
                                    
                                    # Wait a moment to ensure scores message is sent to client
                                    await asyncio.sleep(0.5)
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
            if not self.ws_closed:
                await self.send_json("error", message=str(e))
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources but keep session data accessible."""
        self.is_active = False
        self.stop_event.set()
        self.ws_closed = True
        
        # Cancel jitter buffer flush task
        if self.jitter_flush_task:
            self.jitter_flush_task.cancel()
            try:
                await self.jitter_flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining buffer
        await self.jitter_buffer.force_flush()
        
        # NOTE: Don't remove session from active_sessions here
        # Keep it accessible for API fallback to fetch scores
        # Session will be cleaned up after complete endpoint is called
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        print("🔌 Session cleaned up")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("technical_interview.html", {"request": request})


@app.post("/register-session")
async def register_session(request: RegisterSessionRequest):
    """Register an interview session from main service."""
    try:
        session_id = request.session_id
        
        if session_id in active_sessions:
            return {"success": True, "session_id": session_id, "message": "Session already registered"}
        
        active_sessions[session_id] = InterviewSession(
            session_id=session_id,
            job_details=request.job_details,
            candidate_info=request.candidate_info,
            system_instruction=request.system_instruction,
            technical_interview_id=request.technical_interview_id
        )
        
        print(f"✅ Session registered: {session_id}")
        return {"success": True, "session_id": session_id, "interview_url": f"/interview/{session_id}"}
        
    except Exception as e:
        print(f"Register session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start/{candidate_id}")
async def start_interview(candidate_id: str, request: StartInterviewRequest):
    """
    Start Technical Interview for a Candidate.
    
    Flow:
    1. Call main service API to validate candidate and get interview session
    2. Main service checks:
       - Candidate exists and credentials match
       - Candidate passed aptitude test (aptitude_test_result == 'pass')
       - Technical test not already taken (technical_test == False)
       - Extracts resume text and generates dynamic prompt
    3. Register session locally with system instruction
    4. Return interview URL
    """
    try:
        # Call the main service to start the interview
        # This handles all validation: aptitude test pass, technical_test check, resume extraction
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MAIN_SERVICE_URL}/technical-interview/start/{candidate_id}",
                json={
                    "job_requirement_id": request.job_requirement_id,
                    "email": request.email,
                    "password": request.password
                }
            )
            
            if response.status_code != 200:
                error_detail = response.json().get("detail", "Failed to start interview")
                raise HTTPException(status_code=response.status_code, detail=error_detail)
            
            result = response.json()
            
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("message", "Failed to start interview"))
            
            data = result.get("data", {})
            
            session_id = data.get("interview_session_id")
            job_details = data.get("job_details", {})
            candidate_info = data.get("candidate_info", {})
            system_instruction = data.get("system_instruction", "")
            
            # If system instruction not provided by main service, generate locally
            if not system_instruction:
                system_instruction = generate_system_instruction(job_details, candidate_info)
            
            technical_interview_id = data.get("technical_interview_id")
            
            # Register session locally
            active_sessions[session_id] = InterviewSession(
                session_id=session_id,
                job_details=job_details,
                candidate_info=candidate_info,
                system_instruction=system_instruction,
                technical_interview_id=technical_interview_id
            )
            
            print(f"✅ Interview session started: {session_id}")
            print(f"   Technical Interview ID: {technical_interview_id}")
            print(f"   Candidate: {candidate_info.get('name', 'Unknown')}")
            print(f"   Job: {job_details.get('title', 'Unknown')}")
            
            return {
                "success": True,
                "technical_interview_id": technical_interview_id,
                "session_id": session_id,
                "interview_url": f"/interview/{session_id}",
                "websocket_url": f"ws://localhost:8100/ws/interview/{session_id}",
                "job_details": job_details,
                "candidate_info": candidate_info,
                "interview_config": data.get("interview_config", {
                    "min_duration_minutes": 5,
                    "max_duration_minutes": 15
                }),
                "instructions": data.get("instructions", {})
            }
            
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to main interview service. Please ensure it's running."
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Start interview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/thank-you", response_class=HTMLResponse)
async def thank_you_page(request: Request):
    """Serve the thank you page after interview completion."""
    return templates.TemplateResponse("thank_you.html", {"request": request})


@app.get("/interview/{session_id}", response_class=HTMLResponse)
async def interview_page(request: Request, session_id: str):
    """Serve the interview page."""
    session_data = {
        "request": request,
        "session_id": session_id,
        "job_title": "Technical Interview",
        "candidate_name": ""
    }
    
    if session_id in active_sessions:
        session = active_sessions[session_id]
        session_data["job_title"] = session.job_details.get("title", "Technical Interview")
        session_data["candidate_name"] = f"{session.candidate_info.get('first_name', '')} {session.candidate_info.get('last_name', '')}".strip()
    
    return templates.TemplateResponse("technical_interview.html", session_data)


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    return {
        "success": True,
        "session_id": session_id,
        "technical_interview_id": session.technical_interview_id,
        "job_details": session.job_details,
        "candidate_info": session.candidate_info
    }


@app.get("/api/session/{session_id}/scores")
async def get_session_scores(session_id: str):
    """Get generated scores for a session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    if not session.generated_scores:
        raise HTTPException(status_code=404, detail="Scores not yet generated. Please end the interview first.")
    
    return {
        "success": True,
        "session_id": session_id,
        "technical_interview_id": session.technical_interview_id,
        "scores": session.generated_scores,
        "interview_duration_seconds": session.interview_duration_seconds,
        "transcript": session.transcript
    }


@app.websocket("/ws/interview/{session_id}")
async def websocket_interview(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for interview audio streaming."""
    if session_id not in active_sessions:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    stored_session = active_sessions[session_id]
    
    await websocket.accept()
    print(f"🔗 WebSocket connected: {session_id}")
    
    session = ProductionInterviewSession(
        websocket=websocket,
        system_instruction=stored_session.system_instruction,
        job_details=stored_session.job_details,
        candidate_info=stored_session.candidate_info,
        parent_session=stored_session  # Pass parent session for transcript/score storage
    )
    
    try:
        await session.run()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
        print(f"👋 WebSocket closed: {session_id}")


@app.post("/complete/{technical_interview_id}")
async def complete_interview(technical_interview_id: str, request: CompleteInterviewRequest):
    """
    Complete the technical interview with AI-generated scores.
    
    This endpoint is called when the interview ends (either naturally or by user action).
    It:
    1. Validates the session exists
    2. Forwards the completion data to the main service
    3. Main service stores all scores and updates candidate's technical_test fields
    4. Cleans up the local session
    
    The AI generates scores based on the interview conversation for:
    - Technical knowledge
    - Communication skills
    - Confidence level
    - Response quality
    - Overall assessment
    """
    try:
        session_id = request.interview_session_id
        
        # Verify session exists locally
        if session_id not in active_sessions:
            print(f"⚠️ Session {session_id} not found locally, but proceeding with completion")
        
        # Prepare completion data for main service
        completion_data = request.model_dump(exclude_none=True)
        completion_data.pop("interview_session_id", None)  # Remove session_id, not needed in main service
        
        # Map field names to match database model
        if "input_tokens" in completion_data:
            completion_data["input_tokens_used"] = completion_data.pop("input_tokens")
        if "output_tokens" in completion_data:
            completion_data["output_tokens_used"] = completion_data.pop("output_tokens")
        if "total_tokens" in completion_data:
            completion_data.pop("total_tokens")  # Not in DB, remove it
        
        # Add interview_started_at from session if available
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if session.started_at:
                completion_data["interview_started_at"] = session.started_at.isoformat()
        
        # Store interviewer transcript as interview_transcript for DB
        if "interviewer_transcript" in completion_data:
            # Convert string transcript to list format for DB
            transcript_text = completion_data.pop("interviewer_transcript")
            if transcript_text:
                completion_data["interview_transcript"] = [
                    {"speaker": "interviewer", "text": transcript_text}
                ]
        
        # Call main service to complete the interview and store in DB
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MAIN_SERVICE_URL}/technical-interview/complete/{technical_interview_id}",
                json=completion_data
            )
            
            if response.status_code != 200:
                error_detail = response.json().get("detail", "Failed to complete interview")
                raise HTTPException(status_code=response.status_code, detail=error_detail)
            
            result = response.json()
            
            # Clean up local session
            if session_id in active_sessions:
                del active_sessions[session_id]
                print(f"🧹 Session cleaned up: {session_id}")
            
            print(f"✅ Interview completed: {technical_interview_id}")
            print(f"   Overall Score: {request.overall_score}")
            print(f"   Result: {request.result}")
            print(f"   AI Recommendation: {request.ai_recommendation}")
            
            return {
                "success": True,
                "message": "Technical interview completed successfully",
                "technical_interview_id": technical_interview_id,
                "overall_score": request.overall_score,
                "overall_rating": request.overall_rating,
                "result": request.result,
                "ai_recommendation": request.ai_recommendation,
                "ai_feedback_summary": request.ai_feedback_summary,
                "stored_in_db": True
            }
            
    except httpx.ConnectError:
        # Even if main service is down, try to store locally and return success
        print(f"⚠️ Could not connect to main service, interview completion not persisted")
        
        # Clean up local session
        if request.interview_session_id in active_sessions:
            del active_sessions[request.interview_session_id]
        
        return {
            "success": True,
            "message": "Interview completed locally (main service unavailable)",
            "technical_interview_id": technical_interview_id,
            "overall_score": request.overall_score,
            "result": request.result,
            "stored_in_db": False,
            "warning": "Results not persisted to database - main service unavailable"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Complete interview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-scores/{session_id}")
async def generate_ai_scores(session_id: str, transcript: List[Dict[str, Any]]):
    """
    Generate AI-based evaluation scores from interview transcript.
    
    This endpoint can be called by the frontend to get AI-generated scores
    before completing the interview. It uses the Gemini API to analyze
    the transcript and generate scores for various parameters.
    
    Args:
        session_id: The interview session ID
        transcript: List of conversation turns with speaker and text
    
    Returns:
        Dictionary with all evaluation scores and recommendations
    """
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        stored_session = active_sessions[session_id]
        job_details = stored_session.job_details
        candidate_info = stored_session.candidate_info
        
        # Build the transcript text
        transcript_text = "\n".join([
            f"{turn.get('speaker', 'Unknown')}: {turn.get('text', '')}"
            for turn in transcript
        ])
        
        # Generate evaluation prompt
        evaluation_prompt = f"""
You are an expert technical interview evaluator. Analyze the following interview transcript and provide a comprehensive evaluation.

## Interview Context
- Position: {job_details.get('title', 'Technical Position')}
- Department: {job_details.get('department', 'Technology')}
- Required Skills: {job_details.get('requirements', [])}
- Candidate: {candidate_info.get('name', 'Candidate')}

## Interview Transcript
{transcript_text}

## Evaluation Required
Provide a JSON response with the following scores (0-100) and assessments:

{{
    "overall_score": <0-100>,
    "overall_rating": "<excellent|good|average|below_average|poor>",
    "technical_knowledge_score": <0-100>,
    "domain_expertise_score": <0-100>,
    "communication_score": <0-100>,
    "language_proficiency_score": <0-100>,
    "confidence_score": <0-100>,
    "professionalism_score": <0-100>,
    "response_relevance_score": <0-100>,
    "response_depth_score": <0-100>,
    "response_clarity_score": <0-100>,
    "engagement_score": <0-100>,
    "candidate_strengths": ["strength1", "strength2", ...],
    "candidate_weaknesses": ["weakness1", "weakness2", ...],
    "ai_recommendation": "<strongly_recommend|recommend|neutral|not_recommend>",
    "ai_recommendation_reason": "<detailed reason>",
    "ai_feedback_summary": "<comprehensive feedback summary>",
    "improvement_areas": ["area1", "area2", ...],
    "skills_assessment": [
        {{"skill_name": "<skill>", "proficiency_level": "<advanced|intermediate|beginner>", "score": <0-100>}}
    ],
    "result": "<pass|fail>",
    "passed_threshold": 60
}}

Be objective and fair in your evaluation. Consider the job requirements when scoring.
"""
        
        # Call Gemini API for evaluation
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=evaluation_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Parse the response
        import json as json_module
        scores = json_module.loads(response.text)
        
        return {
            "success": True,
            "session_id": session_id,
            "evaluation": scores
        }
        
    except Exception as e:
        print(f"Generate scores error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "version": "3.0.0",
        "api_key_configured": bool(GOOGLE_API_KEY),
        "active_sessions": len(active_sessions),
        "features": {
            "jitter_buffer_ms": JITTER_BUFFER_MS,
            "min_speech_duration_ms": MIN_SPEECH_DURATION_MS,
            "barge_in_filtering": True,
            "latency_tracking": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True)
