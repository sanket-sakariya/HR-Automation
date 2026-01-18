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

# Configure Gemini API
dotenv.load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Initialize Flask app
app = Flask(__name__)

# Language configuration
LANGUAGE_CONFIG = {
    'english': {
        'name': 'English',
        'speech_code': 'en-IN',
        'voice_lang': 'en-IN',
        'prompt_instruction': 'Ask interview questions in English.'
    },
    'hindi': {
        'name': 'Hindi (हिंदी)',
        'speech_code': 'hi-IN',
        'voice_lang': 'hi-IN',
        'prompt_instruction': 'Ask interview questions in Hindi language only. Use Devanagari script.'
    },
    'gujarati': {
        'name': 'Gujarati (ગુજરાતી)',
        'speech_code': 'gu-IN',
        'voice_lang': 'gu-IN',
        'prompt_instruction': 'Ask interview questions in Gujarati language only. Use Gujarati script.'
    },
    'hinglish': {
        'name': 'Hindi + English (Hinglish)',
        'speech_code': 'hi-IN',
        'voice_lang': 'hi-IN',
        'prompt_instruction': 'Ask interview questions in a natural mix of Hindi and English (Hinglish). Use both languages fluidly.'
    },
    'gujenglish': {
        'name': 'Gujarati + English',
        'speech_code': 'gu-IN',
        'voice_lang': 'en-IN',
        'prompt_instruction': 'Ask interview questions in a natural mix of Gujarati and English. Use both languages fluidly.'
    }
}

# Interview state
interview_data = {
    'questions': [],
    'answers': [],
    'current_question': '',
    'current_index': 0,
    'interview_active': False,
    'selected_language': 'english',
    'total_questions': 5
}


def generate_interview_question(question_number, language_key):
    """Generate interview question using Gemini based on language preference"""
    lang_config = LANGUAGE_CONFIG[language_key]
    
    prompt = f"""You are conducting a professional job interview. {lang_config['prompt_instruction']}

Generate interview question #{question_number} for a candidate. The question should be:
- Professional and respectful
- Clear and conversational
- Appropriate for a general job interview

Question types to rotate through:
1. Background and experience
2. Strengths and skills
3. Problem-solving and challenges
4. Career goals and aspirations
5. Motivation and interest

Return ONLY the question text, nothing else. Make it sound natural and conversational."""

    try:
        response = model.generate_content(prompt)
        question = response.text.strip()
        print(f"Generated Question {question_number}: {question}")
        return question
    except Exception as e:
        print(f"Error generating question: {e}")
        # Fallback questions in English
        fallback = [
            "Tell me about yourself and your background.",
            "What are your greatest strengths?",
            "Describe a challenging project you have worked on.",
            "Where do you see yourself in 5 years?",
            "Why are you interested in this position?"
        ]
        return fallback[min(question_number - 1, 4)]


def generate_ai_response(candidate_answer, question_asked, language_key):
    """Generate AI conversational response after candidate answers"""
    lang_config = LANGUAGE_CONFIG[language_key]
    
    prompt = f"""You are a professional and friendly AI interviewer. {lang_config['prompt_instruction']}

The candidate was asked: "{question_asked}"
The candidate answered: "{candidate_answer}"

Generate a brief, natural conversational response (1-2 sentences) that:
- Acknowledges their answer positively
- Shows you're listening and engaged
- Sounds warm and encouraging
- Transitions smoothly to the next part of the interview

Examples of good responses:
- "That's great to hear! Your experience sounds really valuable."
- "Thank you for sharing that. I appreciate your detailed answer."
- "Interesting perspective! That shows good problem-solving skills."
- "I can see you have strong experience in that area."

Return ONLY the response text in {lang_config['name']}, nothing else. Keep it brief and natural."""

    try:
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
        print(f"AI Response: {ai_response}")
        return ai_response
    except Exception as e:
        print(f"Error generating AI response: {e}")
        # Fallback responses
        fallback_responses = {
            'english': "Thank you for sharing that. Let's continue.",
            'hindi': "धन्यवाद। चलिए आगे बढ़ते हैं।",
            'gujarati': "આભાર. ચાલો આગળ વધીએ.",
            'hinglish': "Thank you. Chalo next question par chalte hain.",
            'gujenglish': "Thank you. Chalo continue kariye."
        }
        return fallback_responses.get(language_key, "Thank you. Let's continue.")


# Flask Routes

@app.route('/')
def index():
    """Serve the main interview page"""
    return render_template('index.html')


@app.route('/start_interview', methods=['POST'])
def start_interview():
    """Initialize interview with selected language"""
    try:
        data = request.get_json()
        language = data.get('language', 'english')
        
        interview_data['interview_active'] = True
        interview_data['current_index'] = 0
        interview_data['questions'] = []
        interview_data['answers'] = []
        interview_data['selected_language'] = language
        
        lang_config = LANGUAGE_CONFIG[language]
        
        # Generate welcoming greeting
        greeting_prompt = f"""You are a professional and friendly AI interviewer. {lang_config['prompt_instruction']}

Generate a brief, warm welcome greeting (1-2 sentences) to start the interview that:
- Welcomes the candidate
- Makes them feel comfortable
- Briefly mentions you'll ask them some questions

Return ONLY the greeting in {lang_config['name']}, nothing else. Keep it natural and warm."""

        try:
            greeting_response = model.generate_content(greeting_prompt)
            greeting = greeting_response.text.strip()
        except:
            greeting_map = {
                'english': "Welcome! Thank you for joining today. Let's get started with a few questions.",
                'hindi': "स्वागत है! आज आने के लिए धन्यवाद। चलिए कुछ सवालों के साथ शुरू करते हैं।",
                'gujarati': "સ્વાગત છે! આજે જોડાવા બદલ આભાર. ચાલો કેટલાક પ્રશ્નો સાથે શરૂઆત કરીએ.",
                'hinglish': "Welcome! Aane ke liye thank you. Let's start with some questions.",
                'gujenglish': "Welcome! Aavva badal thank you. Chalo start kariye with some questions."
            }
            greeting = greeting_map.get(language, "Welcome! Let's begin the interview.")
        
        # Generate first question using Gemini
        first_question = generate_interview_question(1, language)
        interview_data['current_question'] = first_question
        
        print(f"\n{'='*50}")
        print(f"INTERVIEW STARTED - Language: {LANGUAGE_CONFIG[language]['name']}")
        print(f"{'='*50}")
        print(f"Greeting: {greeting}")
        print(f"Question 1: {first_question}")
        
        return jsonify({
            'status': 'success',
            'greeting': greeting,
            'question': first_question
        })
    except Exception as e:
        print(f"Error starting interview: {e}")
        return jsonify({'error': str(e)})


@app.route('/listen_answer', methods=['POST'])
def listen_answer():
    """Listen to candidate's answer via microphone"""
    recognizer = sr.Recognizer()
    answer_text = ""
    
    try:
        data = request.get_json()
        language = data.get('language', 'english')
        lang_config = LANGUAGE_CONFIG[language]
        
        print(f"\nListening for answer in {lang_config['name']}...")
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Speak now...")
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=60)
            
        print("Processing speech...")
        # Use appropriate language code for speech recognition
        answer_text = recognizer.recognize_google(audio, language=lang_config['speech_code'])
        print(f"Transcribed answer: {answer_text}")
        
        interview_data['answers'].append(answer_text)
        current_question = interview_data['current_question']
        interview_data['questions'].append(current_question)
        
        # Generate AI conversational response to the answer
        ai_response = generate_ai_response(answer_text, current_question, language)
        
        # Move to next question
        interview_data['current_index'] += 1
        
        if interview_data['current_index'] < interview_data['total_questions']:
            # Generate next question using Gemini
            next_question = generate_interview_question(
                interview_data['current_index'] + 1,
                language
            )
            interview_data['current_question'] = next_question
            
            print(f"\nQuestion {interview_data['current_index'] + 1}: {next_question}")
            
            return jsonify({
                'status': 'success',
                'answer': answer_text,
                'question': current_question,
                'ai_response': ai_response,
                'next_question': next_question
            })
        else:
            # Interview complete
            print("\nAll questions completed!")
            interview_data['interview_active'] = False
            
            # Generate final closing response
            closing_prompt = f"""You are a professional interviewer. {LANGUAGE_CONFIG[language]['prompt_instruction']}

The interview is now complete. Generate a brief, warm closing statement (2-3 sentences) that:
- Thanks the candidate for their time
- Acknowledges their effort
- Ends on a positive note

Return ONLY the closing statement in {LANGUAGE_CONFIG[language]['name']}, nothing else."""
            
            try:
                closing_response = model.generate_content(closing_prompt)
                ai_closing = closing_response.text.strip()
            except:
                closing_map = {
                    'english': "Thank you so much for your time today. You've shared great insights. We'll be in touch soon!",
                    'hindi': "आज अपना समय देने के लिए बहुत-बहुत धन्यवाद। आपने बहुत अच्छी जानकारी साझा की। हम जल्द ही संपर्क करेंगे!",
                    'gujarati': "આજે તમારો સમય આપવા બદલ ખૂબ ખૂબ આભાર. તમે સારી માહિતી શેર કરી. અમે ટૂંક સમયમાં સંપર્ક કરીશું!",
                    'hinglish': "Thank you bahut bahut aaj ke liye. Aapne bahut acchi information share ki. We'll be in touch soon!",
                    'gujenglish': "Thank you khub khub for your time. Tame saru share karyu. We'll contact you soon!"
                }
                ai_closing = closing_map.get(language, "Thank you for your time today!")
            
            return jsonify({
                'status': 'complete',
                'answer': answer_text,
                'question': current_question,
                'ai_response': ai_closing,
                'next_question': None
            })
            
    except sr.WaitTimeoutError:
        print("Timeout - no speech detected")
        return jsonify({'error': 'No speech detected'})
    except sr.UnknownValueError:
        print("Could not understand audio")
        return jsonify({'error': 'Could not understand'})
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
        return jsonify({'error': 'Recognition service error'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)})


@app.route('/stop_interview')
def stop_interview():
    """End interview and generate summary"""
    interview_data['interview_active'] = False
    summary = None
    
    try:
        if len(interview_data['answers']) > 0:
            # Generate summary using Gemini
            qa_pairs = "\n\n".join([
                f"Q{i+1}: {q}\nA{i+1}: {a}" 
                for i, (q, a) in enumerate(zip(interview_data['questions'], interview_data['answers']))
            ])
            
            language = interview_data['selected_language']
            lang_config = LANGUAGE_CONFIG[language]
            
            summary_prompt = f"""You are an expert interviewer. Based on this interview, provide a brief professional assessment of the candidate.

Interview Language: {lang_config['name']}
Interview Transcript:
{qa_pairs}

Provide a concise 4-5 sentence assessment in {lang_config['name']} covering:
1. Communication skills
2. Key strengths demonstrated
3. Overall impression
4. Recommendation

Be professional and constructive. {lang_config['prompt_instruction']}"""
            
            print("\nGenerating interview summary...")
            response = model.generate_content(summary_prompt)
            summary = response.text
            
            print(f"\n{'='*50}")
            print("INTERVIEW SUMMARY")
            print(f"{'='*50}")
            print(summary)
            print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        summary = "Could not generate summary."
    
    return jsonify({
        'status': 'Interview ended',
        'summary': summary
    })


def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    print(f"\n{'='*70}")
    print("AI MULTILINGUAL VIDEO INTERVIEW - POWERED BY GEMINI 2.0 FLASH")
    print(f"{'='*70}")
    print("🌍 Languages: English | Hindi | Gujarati | Hinglish | Gujarati+English")
    print("🤖 AI Features: ")
    print("   - AI speaks and responds in your selected language")
    print("   - Smooth auto-conversation flow (no manual buttons)")
    print("   - Dynamic AI-generated questions & responses")
    print("   - Natural two-way conversation")
    print("📹 Camera: Auto-detection with selection support")
    print(f"{'='*70}")
    print("🚀 Starting Flask server...")
    print("🌐 Opening browser automatically...")
    print("⚠️  Please ALLOW camera and microphone access!")
    print(f"{'='*70}\n")
    
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, port=5000, threaded=True)
