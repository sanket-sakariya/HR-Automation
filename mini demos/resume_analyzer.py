import os
import json
import time
from pathlib import Path
import google.generativeai as genai
from pypdf import PdfReader

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyDHNd6W382fBzwf_HbPxf70sxG13XE9xgA"
genai.configure(api_key=GEMINI_API_KEY)

# Default resume folder path
DEFAULT_RESUME_FOLDER = "resume"

def scan_resume_folder(folder_path):
    """
    Scan folder for PDF files
    """
    try:
        if not os.path.exists(folder_path):
            print(f"Error: Folder not found at {folder_path}")
            return []
        
        pdf_files = []
        for file in os.listdir(folder_path):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(folder_path, file))
        
        return sorted(pdf_files)
    
    except Exception as e:
        print(f"Error scanning folder: {e}")
        return []

def display_pdf_list(pdf_files):
    """
    Display list of PDFs for selection
    """
    print("\n" + "="*70)
    print("AVAILABLE RESUMES")
    print("="*70)
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_path)
        file_size = os.path.getsize(pdf_path) / 1024  # KB
        print(f"{idx}. {filename} ({file_size:.2f} KB)")
    
    print("="*70)

def select_resume(pdf_files):
    """
    Let user select which resume to analyze
    """
    while True:
        try:
            choice = input("\nEnter the rank number to analyze (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice = int(choice)
            
            if 1 <= choice <= len(pdf_files):
                return pdf_files[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(pdf_files)}")
        
        except ValueError:
            print("Invalid input. Please enter a number.")

def pdf_to_html(pdf_path):
    """
    Convert PDF resume to HTML format
    """
    try:
        reader = PdfReader(pdf_path)
        text_content = ""
        
        # Extract text from all pages
        for page in reader.pages:
            text_content += page.extract_text() + "\n\n"
        
        # Create simple HTML structure
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Resume</title>
        </head>
        <body>
            <div class="resume-content">
                {text_content.replace(chr(10), '<br>')}
            </div>
        </body>
        </html>
        """
        
        return html_content, text_content
    
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return None, None

def analyze_resume_with_gemini(resume_text):
    """
    Send resume to Gemini 2.5 Flash and get analysis with token usage
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create prompt for structured output
        prompt = f"""
        Analyze the following resume and provide a comprehensive evaluation.
        
        Resume Content:
        {resume_text}
        
        Please provide your response in the following JSON format:
        {{
            "summary": "3-line summary of the candidate",
            "skills_score": score out of 10,
            "experience_score": score out of 10,
            "education_score": score out of 10,
            "projects_activities_score": score out of 10,
            "details": {{
                "skills_feedback": "brief feedback on skills",
                "experience_feedback": "brief feedback on experience",
                "education_feedback": "brief feedback on education",
                "projects_feedback": "brief feedback on projects/activities"
            }}
        }}
        
        Scoring criteria:
        - Skills: Relevance, diversity, and depth of technical/professional skills
        - Experience: Years of experience, relevance, and impact
        - Education: Degree level, institution reputation, and relevance
        - Projects/Activities: Quality, relevance, and demonstrated impact
        
        Return ONLY the JSON object, no additional text.
        """
        
        # Track time
        start_time = time.time()
        
        # Generate response
        response = model.generate_content(prompt)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Get token usage
        token_usage = {
            'input_tokens': response.usage_metadata.prompt_token_count,
            'output_tokens': response.usage_metadata.candidates_token_count,
            'total_tokens': response.usage_metadata.total_token_count
        }
        
        # Parse JSON from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        
        return result, token_usage, processing_time
    
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None, None, None

def display_results(analysis, token_usage, processing_time, filename):
    """
    Display the analysis results with token usage and time
    """
    if not analysis:
        print("No analysis results to display")
        return
    
    print("\n" + "="*70)
    print("RESUME ANALYSIS RESULTS")
    print("="*70)
    print(f"📄 File: {filename}")
    print(f"⏱️  Processing Time: {processing_time:.2f} seconds")
    print(f"🔢 Input Tokens: {token_usage['input_tokens']:,}")
    print(f"🔢 Output Tokens: {token_usage['output_tokens']:,}")
    print(f"🔢 Total Tokens: {token_usage['total_tokens']:,}")
    print("="*70)
    
    print("\n📝 SUMMARY:")
    summary_lines = analysis.get('summary', 'N/A').split('\n')
    for line in summary_lines:
        if line.strip():
            print(f"   {line.strip()}")
    
    print("\n📊 SCORES:")
    print(f"  • Skills:              {analysis.get('skills_score', 0)}/10")
    print(f"  • Experience:          {analysis.get('experience_score', 0)}/10")
    print(f"  • Education:           {analysis.get('education_score', 0)}/10")
    print(f"  • Projects/Activities: {analysis.get('projects_activities_score', 0)}/10")
    
    total_score = (
        analysis.get('skills_score', 0) + 
        analysis.get('experience_score', 0) + 
        analysis.get('education_score', 0) + 
        analysis.get('projects_activities_score', 0)
    )
    print(f"\n  🎯 TOTAL SCORE: {total_score}/40 ({(total_score/40)*100:.1f}%)")
    
    if 'details' in analysis:
        print("\n💡 DETAILED FEEDBACK:")
        details = analysis['details']
        print(f"\n  Skills:\n    {details.get('skills_feedback', 'N/A')}")
        print(f"\n  Experience:\n    {details.get('experience_feedback', 'N/A')}")
        print(f"\n  Education:\n    {details.get('education_feedback', 'N/A')}")
        print(f"\n  Projects:\n    {details.get('projects_feedback', 'N/A')}")
    
    print("\n" + "="*70)

def main():
    """
    Main function to run the resume analysis
    """
    print("\n🚀 RESUME ANALYSIS SYSTEM")
    print("Powered by Gemini 2.5 Flash\n")
    
    # Scan folder for PDFs
    print(f"📂 Scanning folder: {DEFAULT_RESUME_FOLDER}")
    pdf_files = scan_resume_folder(DEFAULT_RESUME_FOLDER)
    
    if not pdf_files:
        print("\n❌ No PDF files found in the folder.")
        
        # Ask for manual path
        manual_path = input("\nEnter a different folder path (or press Enter to exit): ").strip()
        if manual_path:
            pdf_files = scan_resume_folder(manual_path)
            if not pdf_files:
                print("No PDF files found. Exiting.")
                return
        else:
            return
    
    print(f"\n✅ Found {len(pdf_files)} resume(s)")
    
    # Display and select resume
    display_pdf_list(pdf_files)
    selected_pdf = select_resume(pdf_files)
    
    if not selected_pdf:
        print("\n👋 Exiting...")
        return
    
    filename = os.path.basename(selected_pdf)
    print(f"\n✅ Selected: {filename}")
    
    # Start processing
    print("\n" + "="*70)
    print("PROCESSING STARTED")
    print("="*70)
    
    # Parse PDF to HTML
    print("\n[1/3] 🔄 Parsing PDF to HTML...")
    parse_start = time.time()
    html_content, text_content = pdf_to_html(selected_pdf)
    parse_time = time.time() - parse_start
    
    if not text_content:
        print("❌ Failed to parse PDF")
        return
    
    print(f"✅ PDF parsed successfully in {parse_time:.2f} seconds")
    print(f"📊 Extracted {len(text_content)} characters")
    
    # Analyze with Gemini
    print("\n[2/3] 🤖 Analyzing resume with Gemini 2.5 Flash...")
    print("⏳ Please wait...")
    
    analysis, token_usage, processing_time = analyze_resume_with_gemini(text_content)
    
    if not analysis or not token_usage:
        print("❌ Failed to analyze resume")
        return
    
    print(f"✅ Analysis completed in {processing_time:.2f} seconds")
    
    # Display results
    print("\n[3/3] 📊 Generating results...")
    display_results(analysis, token_usage, processing_time, filename)
    
    # Save options
    print("\n💾 SAVE OPTIONS:")
    save_choice = input("Save results? (1=JSON only, 2=HTML only, 3=Both, 0=None): ").strip()
    
    base_name = Path(selected_pdf).stem
    
    if save_choice in ['1', '3']:
        # Save analysis to JSON
        json_data = {
            'filename': filename,
            'processing_time': processing_time,
            'token_usage': token_usage,
            'analysis': analysis,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        json_filename = f"{base_name}_analysis.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        print(f"✅ Analysis saved to: {json_filename}")
    
    if save_choice in ['2', '3']:
        # Save HTML
        html_filename = f"{base_name}_resume.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML saved to: {html_filename}")
    
    print("\n✨ Process completed successfully!")
    
    # Ask if user wants to analyze another resume
    another = input("\nAnalyze another resume? (y/n): ").lower()
    if another == 'y':
        main()

if __name__ == "__main__":
    main()