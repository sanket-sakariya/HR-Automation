"""
AI Multilingual Video Interview System
Powered by Google Gemini 2.0 Flash

Features:
- Multi-camera support with auto-detection
- Multilingual: English, Hindi, Gujarati, Hinglish, Gujarati+English
- Smooth auto-conversation flow
- AI-generated questions and responses
- Real-time speech recognition
- Interview summary generation
"""

import os
import time
import speech_recognition as sr
import google.generativeai as genai
from flask import Flask, render_template, jsonify, request
import threading
import webbrowser
import dotenv
from langdetect import detect, LangDetectException

# Configure Gemini API
import sys
from pathlib import Path

# Get current directory
current_dir = Path(__file__).parent
# Look for .env.dev in parent directory (where user has it)
env_file = current_dir.parent / '.env.dev'

print(f"\n🔍 Looking for API key...")
print(f"📁 Current directory: {current_dir}")
print(f"📄 Checking for file: {env_file}")
print(f"✓ File exists: {env_file.exists()}")

# Load environment variables
dotenv.load_dotenv(env_file)

# Try multiple variable names
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")

if GEMINI_API_KEY:
    print(f"✅ API Key found! (ends with: ...{GEMINI_API_KEY[-8:]})")
else:
    print("\n" + "="*70)
    print("❌ ERROR: API Key NOT found in environment variables!")
    print("="*70)
    
    if env_file.exists():
        print(f"\n✓ File {env_file.name} exists")
        print("\n🔍 Checking file content...")
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                print(f"File size: {len(content)} bytes")
                
                if 'GEMINI_API_KEY' in content:
                    print("✓ Found 'GEMINI_API_KEY' in file")
                    # Show the line (without revealing the key)
                    for line in content.split('\n'):
                        if 'GEMINI_API_KEY' in line and '=' in line:
                            key_part = line.split('=', 1)[1].strip()
                            if key_part and len(key_part) > 10:
                                print(f"✓ Key value found (length: {len(key_part)} chars)")
                                print(f"✓ Key preview: {key_part[:10]}...{key_part[-8:]}")
                            else:
                                print("❌ Key value is empty or too short!")
                                print(f"Current line: {line}")
                else:
                    print("❌ 'GEMINI_API_KEY' not found in file")
                    print("\nFile content preview:")
                    print(content[:200])
        except Exception as e:
            print(f"❌ Error reading file: {e}")
    else:
        print(f"\n❌ File does not exist: {env_file}")
        print(f"\nPlease create this file with:")
        print(f"GEMINI_API_KEY=your_actual_api_key_here")
    
    print("\n" + "="*70)
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
print("✅ Gemini API configured successfully!\n")

# Initialize Flask app
app = Flask(__name__)

# Language configuration for speech recognition
SUPPORTED_LANGUAGES = ['en-IN', 'hi-IN', 'gu-IN', 'ta-IN', 'te-IN', 'mr-IN', 'bn-IN']

# Language detection mapping
LANGUAGE_MAP = {
    'en': {'name': 'English', 'code': 'en', 'speech_code': 'en-IN', 'tts_code': 'en'},
    'hi': {'name': 'Hindi', 'code': 'hi', 'speech_code': 'hi-IN', 'tts_code': 'hi'},
    'gu': {'name': 'Gujarati', 'code': 'gu', 'speech_code': 'gu-IN', 'tts_code': 'gu'},
    'mr': {'name': 'Marathi', 'code': 'mr', 'speech_code': 'mr-IN', 'tts_code': 'mr'},
    'ta': {'name': 'Tamil', 'code': 'ta', 'speech_code': 'ta-IN', 'tts_code': 'ta'},
    'te': {'name': 'Telugu', 'code': 'te', 'speech_code': 'te-IN', 'tts_code': 'te'},
    'bn': {'name': 'Bengali', 'code': 'bn', 'speech_code': 'bn-IN', 'tts_code': 'bn'}
}

def detect_language(text):
    """Detect language from text - improved detection"""
    try:
        # Detect language
        lang_code = detect(text)
        print(f"🔍 Raw detection: {lang_code}")
        
        # Map to our supported languages
        if lang_code in LANGUAGE_MAP:
            return lang_code
        
        # Handle language variations
        lang_variations = {
            'ne': 'hi',  # Nepali -> Hindi (similar script)
            'pa': 'hi',  # Punjabi -> Hindi (similar script)
            'ur': 'hi',  # Urdu -> Hindi (similar script)
        }
        
        if lang_code in lang_variations:
            return lang_variations[lang_code]
        
        # Check if text contains Devanagari script (Hindi/Marathi)
        if any('\u0900' <= char <= '\u097F' for char in text):
            return 'hi'
        
        # Check if text contains Gujarati script
        if any('\u0A80' <= char <= '\u0AFF' for char in text):
            return 'gu'
        
        # Check if text contains Tamil script
        if any('\u0B80' <= char <= '\u0BFF' for char in text):
            return 'ta'
        
        # Check if text contains Telugu script
        if any('\u0C00' <= char <= '\u0C7F' for char in text):
            return 'te'
        
        # Check if text contains Bengali script
        if any('\u0980' <= char <= '\u09FF' for char in text):
            return 'bn'
        
        # Default to English
        return 'en'
        
    except LangDetectException as e:
        print(f"⚠️ Language detection failed: {e}")
        # If detection fails, try to infer from script
        if any('\u0900' <= char <= '\u097F' for char in text):
            return 'hi'
        if any('\u0A80' <= char <= '\u0AFF' for char in text):
            return 'gu'
        return 'en'

def get_language_name(lang_code):
    """Get friendly language name"""
    return LANGUAGE_MAP.get(lang_code, LANGUAGE_MAP['en'])['name']

# Interview state
interview_data = {
    'questions': [],
    'answers': [],
    'current_question': '',
    'current_index': 0,
    'interview_active': False,
    'detected_language': 'en',  # Auto-detected language
    'conversation_history': [],  # Track language switches
    'total_questions': 5
}


def generate_interview_question(question_number, detected_lang='en', previous_answer=None):
    """Generate interview question using Gemini - adapts to detected language"""
    
    lang_name = get_language_name(detected_lang)
    
    # Build context-aware prompt
    context = ""
    if previous_answer:
        context = f"\nThe candidate's previous answer was in {lang_name}. Continue the conversation in the same language or naturally mix languages if they did."
    
    prompt = f"""You are a professional, warm, and intelligent AI interviewer conducting a job interview.

{context}

Generate interview question #{question_number}. The question should be:
- Professional yet conversational and warm
- In {lang_name} (or naturally mix languages if candidate uses mixed language)
- Clear and easy to understand
- Appropriate for a general job interview
- Natural and human-like

Question types to rotate:
1. Background and experience
2. Strengths and skills  
3. Problem-solving and challenges
4. Career goals and aspirations
5. Motivation and interest

IMPORTANT: Respond naturally in {lang_name}. If the candidate speaks Hindi, respond in Hindi. If they speak Gujarati, respond in Gujarati. If they mix English with Hindi/Gujarati (Hinglish/Gujenglish), do the same naturally.

Return ONLY the question text, nothing else. Make it warm, natural and conversational."""

    try:
        response = model.generate_content(prompt)
        question = response.text.strip()
        print(f"Generated Question {question_number} in {lang_name}: {question}")
        return question
    except Exception as e:
        print(f"Error generating question: {e}")
        # Fallback questions
        fallback = {
            'en': [
                "Tell me about yourself and your background.",
                "What are your greatest strengths?",
                "Describe a challenging project you've worked on.",
                "Where do you see yourself in 5 years?",
                "Why are you interested in this position?"
            ],
            'hi': [
                "अपने बारे में बताइए।",
                "आपकी सबसे बड़ी ताकत क्या है?",
                "किसी चुनौतीपूर्ण परियोजना के बारे में बताइए।",
                "आप खुद को 5 साल में कहां देखते हैं?",
                "आप इस पद में क्यों रुचि रखते हैं?"
            ],
            'gu': [
                "તમારા વિશે કહો.",
                "તમારી સૌથી મોટી શક્તિ શું છે?",
                "એક પડકારજનક પ્રોજેક્ટ વિશે જણાવો.",
                "તમે તમારી જાતને 5 વર્ષમાં ક્યાં જુઓ છો?",
                "તમે આ પોઝિશનમાં કેમ રસ ધરાવો છો?"
            ]
        }
        questions = fallback.get(detected_lang, fallback['en'])
        return questions[min(question_number - 1, 4)]


def generate_ai_response(candidate_answer, question_asked, detected_lang='en'):
    """Generate AI conversational response - adapts to candidate's language"""
    
    lang_name = get_language_name(detected_lang)
    
    prompt = f"""You are a warm, professional, and intelligent AI interviewer having a natural conversation.

The candidate was asked: "{question_asked}"
The candidate answered in {lang_name}: "{candidate_answer}"

Generate a brief, natural conversational response (1-2 sentences) that:
- Responds in the SAME LANGUAGE the candidate used (detect from their answer)
- Acknowledges their answer warmly and positively  
- Shows you're genuinely listening and engaged
- Sounds natural, human-like, and encouraging
- Flows smoothly like a real conversation

IMPORTANT: Match the candidate's language style exactly:
- If they spoke in English, respond in English
- If they spoke in Hindi, respond in Hindi  
- If they spoke in Gujarati, respond in Gujarati
- If they mixed languages (Hinglish/Gujenglish), do the same naturally

Be warm, encouraging, and conversational. This should feel like talking to a real person, not a robot.

Return ONLY your response, nothing else."""

    try:
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
        print(f"AI Response in {lang_name}: {ai_response}")
        return ai_response
    except Exception as e:
        print(f"Error generating AI response: {e}")
        # Fallback responses
        fallback = {
            'en': "Thank you for sharing! That's really helpful.",
            'hi': "बहुत अच्छा! आपका जवाब बहुत अच्छा था।",
            'gu': "ખૂબ સરસ! તમારો જવાબ સારો હતો.",
            'mr': "धन्यवाद! तुमचे उत्तर चांगले होते.",
            'ta': "நன்றி! உங்கள் பதில் நன்றாக இருந்தது.",
            'te': "ధన్యవాదాలు! మీ సమాధానం బాగుంది.",
            'bn': "ধন্যবাদ! আপনার উত্তর ভাল ছিল."
        }
        return fallback.get(detected_lang, fallback['en'])


# Flask Routes

@app.route('/')
def index():
    """Serve the main interview page"""
    return render_template('index.html')


@app.route('/start_interview', methods=['POST'])
def start_interview():
    """Initialize interview - multilingual, adapts automatically"""
    try:
        interview_data['interview_active'] = True
        interview_data['current_index'] = 0
        interview_data['questions'] = []
        interview_data['answers'] = []
        interview_data['detected_language'] = 'en'  # Will adapt based on user's first response
        interview_data['conversation_history'] = []
        
        # Generate multilingual welcoming greeting
        greeting_prompt = """You are a warm, professional, and intelligent AI interviewer.

Generate a brief, friendly welcome greeting (1-2 sentences) to start the interview that:
- Welcomes the candidate warmly
- Makes them feel comfortable and relaxed
- Mentions you'll have a conversation with them
- IMPORTANT: Use simple, natural English that's easy to understand for multilingual speakers

Keep it warm, natural, and conversational. Sound like a real friendly person, not a robot.

Return ONLY the greeting, nothing else."""

        try:
            greeting_response = model.generate_content(greeting_prompt)
            greeting = greeting_response.text.strip()
        except:
            greeting = "Hello! Welcome to the interview. I'm excited to get to know you better today. Let's have a great conversation!"
        
        # Generate first question - will adapt after detecting user's language
        first_question = generate_interview_question(1, 'en')
        interview_data['current_question'] = first_question
        
        print(f"\n{'='*50}")
        print(f"INTERVIEW STARTED - Adaptive Multilingual Mode")
        print(f"{'='*50}")
        print(f"Greeting: {greeting}")
        print(f"Question 1: {first_question}")
        
        return jsonify({
            'status': 'success',
            'greeting': greeting,
            'question': first_question,
            'detected_language': 'en'
        })
    except Exception as e:
        print(f"Error starting interview: {e}")
        return jsonify({'error': str(e)})


@app.route('/listen_answer', methods=['POST'])
def listen_answer():
    """Listen to candidate's answer - automatically detects language"""
    recognizer = sr.Recognizer()
    answer_text = ""
    detected_lang = 'en'
    
    try:
        print(f"\n🎤 Listening for answer (multilingual mode)...")
        with sr.Microphone() as source:
            # Adjust for ambient noise with better settings
            recognizer.adjust_for_ambient_noise(source, duration=1)
            recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
            recognizer.dynamic_energy_threshold = True  # Auto-adjust to environment
            
            print("🗣️ Speak now in ANY language (English/Hindi/Gujarati/etc.)...")
            # Increased timeout and phrase limit for longer answers
            audio = recognizer.listen(source, timeout=20, phrase_time_limit=90)
            
        print("Processing speech with multi-language support...")
        
        # Strategy: Try each Indian language individually for best accuracy
        # Google's pipe-separated approach doesn't work reliably for Indian languages
        
        recognition_attempts = [
            ('hi-IN', 'Hindi'),       # Try Hindi first (most common)
            ('en-IN', 'English'),     # Then English
            ('gu-IN', 'Gujarati'),
            ('mr-IN', 'Marathi'),
            ('ta-IN', 'Tamil'),
            ('te-IN', 'Telugu'),
            ('bn-IN', 'Bengali'),
            ('kn-IN', 'Kannada'),
            ('ml-IN', 'Malayalam'),
            ('pa-IN', 'Punjabi'),
            ('ur-IN', 'Urdu')
        ]
        
        # Collect all successful recognitions
        successful_recognitions = []
        
        print(f"🌍 Trying recognition in {len(recognition_attempts)} Indian languages...")
        for lang_code, lang_name in recognition_attempts:
            try:
                result = recognizer.recognize_google(audio, language=lang_code)
                if result and len(result.strip()) > 0:
                    successful_recognitions.append((lang_name, result, lang_code))
                    print(f"  ✓ {lang_name}: '{result}'")
            except (sr.UnknownValueError, sr.RequestError):
                pass  # Silently skip failed attempts
        
        if not successful_recognitions:
            raise sr.UnknownValueError("Could not understand audio in any supported language")
        
        # Use the longest/most detailed recognition (usually most accurate)
        answer_text = max(successful_recognitions, key=lambda x: len(x[1]))[1]
        detected_speech_lang = max(successful_recognitions, key=lambda x: len(x[1]))[0]
        
        print(f"\n✅ Best match in {detected_speech_lang}: {answer_text}")
        print(f"📊 Got {len(successful_recognitions)} successful recognition(s)")
        
        if len(successful_recognitions) > 1:
            print(f"🔍 All matches:")
            for lang_name, text, _ in successful_recognitions:
                print(f"   • {lang_name}: {text[:50]}...")
        
        # Detect language from the transcribed text
        detected_lang = detect_language(answer_text)
        lang_name = get_language_name(detected_lang)
        print(f"🌍 Detected language: {lang_name} ({detected_lang})")
        print(f"📝 Full answer: {answer_text}")
        
        # Update interview data
        interview_data['answers'].append(answer_text)
        interview_data['detected_language'] = detected_lang
        interview_data['conversation_history'].append({
            'type': 'answer',
            'text': answer_text,
            'language': detected_lang
        })
        
        current_question = interview_data['current_question']
        interview_data['questions'].append(current_question)
        
        # Generate AI response in the detected language
        ai_response = generate_ai_response(answer_text, current_question, detected_lang)
        
        interview_data['conversation_history'].append({
            'type': 'ai_response',
            'text': ai_response,
            'language': detected_lang
        })
        
        # Move to next question
        interview_data['current_index'] += 1
        
        if interview_data['current_index'] < interview_data['total_questions']:
            # Generate next question in the detected language
            next_question = generate_interview_question(
                interview_data['current_index'] + 1,
                detected_lang,
                answer_text
            )
            interview_data['current_question'] = next_question
            
            print(f"\n{'='*50}")
            print(f"Question {interview_data['current_index'] + 1} in {lang_name}: {next_question}")
            print(f"{'='*50}")
            
            return jsonify({
                'status': 'success',
                'answer': answer_text,
                'question': current_question,
                'ai_response': ai_response,
                'next_question': next_question,
                'detected_language': detected_lang,
                'language_name': lang_name
            })
        else:
            # Interview complete
            print("\n✓ All questions completed!")
            interview_data['interview_active'] = False
            
            # Generate final closing in detected language
            closing_prompt = f"""You are a warm, professional AI interviewer. The interview with the candidate is now complete.

The candidate has been speaking in {lang_name}.

Generate a brief, warm closing statement (2-3 sentences) in {lang_name} that:
- Thanks them sincerely for their time
- Acknowledges their great answers
- Ends on an encouraging, positive note

IMPORTANT: Respond in {lang_name}, matching the language they used throughout.

Return ONLY your closing statement, nothing else. Be warm and genuine."""
            
            try:
                closing_response = model.generate_content(closing_prompt)
                ai_closing = closing_response.text.strip()
            except:
                closing_fallback = {
                    'en': "Thank you so much for your time today! You've shared wonderful insights. We really appreciate it and will be in touch soon!",
                    'hi': "आज अपना समय देने के लिए बहुत-बहुत धन्यवाद! आपने बहुत अच्छी बातें साझा की। हम जल्द ही संपर्क करेंगे!",
                    'gu': "આજે તમારો સમય આપવા બદલ ખૂબ ખૂબ આભાર! તમે ખૂબ સારી વાતો શેર કરી. અમે ટૂંક સમયમાં સંપર્ક કરીશું!",
                    'mr': "आज तुमचा वेळ दिल्याबद्दल खूप धन्यवाद! तुम्ही उत्तम गोष्टी शेअर केल्या. आम्ही लवकरच संपर्क करू!",
                    'ta': "இன்று உங்கள் நேரத்திற்கு மிக்க நன்றி! நீங்கள் சிறந்த விஷயங்களைப் பகிர்ந்துகொண்டீர்கள். விரைவில் தொடர்புகொள்வோம்!",
                    'te': "ఈరోజు మీ సమయం కోసం చాలా ధన్యవాదాలు! మీరు అద్భుతమైన విషయాలు పంచుకున్నారు. త్వరలో సంప్రదిస్తాము!",
                    'bn': "আজ আপনার সময় দেওয়ার জন্য অনেক ধন্যবাদ! আপনি দুর্দান্ত বিষয় শেয়ার করেছেন। শীঘ্রই যোগাযোগ করব!"
                }
                ai_closing = closing_fallback.get(detected_lang, closing_fallback['en'])
            
            return jsonify({
                'status': 'complete',
                'answer': answer_text,
                'question': current_question,
                'ai_response': ai_closing,
                'next_question': None,
                'detected_language': detected_lang,
                'language_name': lang_name
            })
            
    except sr.WaitTimeoutError:
        print("⏱️ Timeout - no speech detected")
        return jsonify({'error': 'No speech detected'})
    except sr.UnknownValueError:
        print("❌ Could not understand audio")
        return jsonify({'error': 'Could not understand'})
    except sr.RequestError as e:
        print(f"❌ Speech recognition error: {e}")
        return jsonify({'error': 'Recognition service error'})
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)})


@app.route('/stop_interview')
def stop_interview():
    """End interview and generate multilingual summary"""
    interview_data['interview_active'] = False
    summary = None
    
    try:
        if len(interview_data['answers']) > 0:
            # Generate summary using Gemini
            qa_pairs = "\n\n".join([
                f"Q{i+1}: {q}\nA{i+1}: {a}" 
                for i, (q, a) in enumerate(zip(interview_data['questions'], interview_data['answers']))
            ])
            
            detected_lang = interview_data.get('detected_language', 'en')
            lang_name = get_language_name(detected_lang)
            
            summary_prompt = f"""You are an expert HR interviewer. Based on this interview, provide a comprehensive professional assessment of the candidate.

Interview Language: {lang_name}
Interview Transcript:
{qa_pairs}

Provide a detailed assessment (5-6 sentences) in {lang_name} covering:
1. Communication skills and clarity
2. Key strengths and capabilities demonstrated
3. Problem-solving abilities
4. Cultural fit and attitude
5. Overall impression
6. Hiring recommendation

IMPORTANT: Write the entire summary in {lang_name}, matching the language the candidate used.

Be professional, constructive, and thorough. This summary should help hiring managers make informed decisions."""
            
            print(f"\n📊 Generating interview summary in {lang_name}...")
            response = model.generate_content(summary_prompt)
            summary = response.text
            
            print(f"\n{'='*60}")
            print(f"INTERVIEW SUMMARY ({lang_name})")
            print(f"{'='*60}")
            print(summary)
            print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        summary = "Could not generate summary due to an error."
    
    return jsonify({
        'status': 'Interview ended',
        'summary': summary,
        'detected_language': interview_data.get('detected_language', 'en')
    })


def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    print(f"\n{'='*75}")
    print("🤖 AI MULTILINGUAL VIDEO INTERVIEW - POWERED BY GEMINI 2.0 FLASH")
    print(f"{'='*75}")
    print("✨ SMART FEATURES:")
    print("   🌍 AUTO-DETECT: Speaks ANY language automatically!")
    print("      ✓ English | Hindi | Gujarati | Marathi | Tamil | Telugu | Bengali")
    print("   🔄 ADAPTIVE: Switches languages if you switch mid-conversation")
    print("   💬 NATURAL: Smooth conversation flow like Gemini Android app")
    print("   🎯 INTELLIGENT: Responds in the exact language you use")
    print("   🗣️ HIGH-QUALITY: Best voice selection for each language")
    print("   📹 CAMERA: Multi-camera support with auto-detection")
    print(f"{'='*75}")
    print("🚀 Starting server...")
    print("🌐 Opening browser at http://127.0.0.1:5000")
    print("⚠️  IMPORTANT: Allow camera and microphone permissions!")
    print("💡 TIP: Just speak naturally - AI will detect your language!")
    print(f"{'='*75}\n")
    
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, port=5000, threaded=True)
