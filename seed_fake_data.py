"""
Seed fake data into the HR Automation database.

Creates:
- 1 company + 1 job requirement
- 1 aptitude test (with 10 questions)
- 8 candidates distributed across pipeline stages:
    * 2 candidates: Resume only (stage 1)
    * 2 candidates: Resume + Aptitude (1 pass / 1 fail) (stage 2)
    * 1 candidate: Resume + Aptitude(pass) + Technical(pass) (stage 3)
    * 3 candidates: ALL completed (Resume + Aptitude + Technical + HR) (stage 4)
        -> Only these get the full AI comprehensive report

Resumes are copied from /home/sanket777/Downloads/resumes/ into ./resume/<candidate_id>.pdf
"""

import asyncio
import json
import os
import random
import shutil
import string
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# ---------- Config ----------
DATABASE_URL = "postgresql+asyncpg://sanket:root@localhost:5432/interview_management_service"
RESUME_SOURCE = Path("/home/sanket777/Downloads/resumes")
RESUME_DEST = Path(__file__).parent / "resume"
RESUME_DEST.mkdir(exist_ok=True)

SYS_USER = uuid.UUID("00000000-0000-0000-0000-000000000001")  # synthetic system user
WORKSPACE_ID = uuid.uuid4()

# Pin to an existing job so all seeded candidates appear under it
TARGET_JOB_ID = uuid.UUID("6a76ec92-6777-4d39-a08d-abf002bd44cb")

# ---------- Resume pool ----------
RESUME_FILES = sorted([p for p in RESUME_SOURCE.glob("*.pdf")])
assert RESUME_FILES, f"No resumes found in {RESUME_SOURCE}"
print(f"Found {len(RESUME_FILES)} resume PDFs")

# ---------- Fake candidates ----------
FAKE_CANDIDATES = [
    # (first, last, email, phone, location, stage, aptitude_pass, technical_pass, hr_pass)
    ("Aarav",   "Sharma",   "aarav.sharma@example.com",   "+919876543210", "Bengaluru", 1, None,  None,  None),
    ("Priya",   "Iyer",     "priya.iyer@example.com",     "+919812345678", "Mumbai",    1, None,  None,  None),
    ("Rohan",   "Patel",    "rohan.patel@example.com",    "+919811112233", "Ahmedabad", 2, True,  None,  None),
    ("Sneha",   "Verma",    "sneha.verma@example.com",    "+919844455566", "Pune",      2, False, None,  None),
    ("Karan",   "Mehta",    "karan.mehta@example.com",    "+919833344455", "Hyderabad", 3, True,  True,  None),
    ("Ananya",  "Reddy",    "ananya.reddy@example.com",   "+919822233344", "Chennai",   4, True,  True,  True),
    ("Vikram",  "Singh",    "vikram.singh@example.com",   "+919811122233", "Delhi",     4, True,  True,  True),
    ("Neha",    "Kapoor",   "neha.kapoor@example.com",    "+919800011122", "Gurugram",  4, True,  True,  False),
]


def rand_password(n=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def assign_resume(idx: int) -> Path:
    return RESUME_FILES[idx % len(RESUME_FILES)]


# ---------- Aptitude question bank (10 questions) ----------
QUESTIONS = [
    {
        "question_number": 1, "difficulty": "simple", "category": "core_logic",
        "question_text": "If a train travels 60 km in 1 hour, how far will it travel in 2.5 hours at the same speed?",
        "options": {"A": "120 km", "B": "150 km", "C": "180 km", "D": "100 km"},
        "correct_answer": "B",
        "explanation": "60 * 2.5 = 150 km",
    },
    {
        "question_number": 2, "difficulty": "simple", "category": "core_logic",
        "question_text": "What comes next in the sequence: 2, 4, 8, 16, ___ ?",
        "options": {"A": "20", "B": "24", "C": "32", "D": "30"},
        "correct_answer": "C",
        "explanation": "Each term is doubled.",
    },
    {
        "question_number": 3, "difficulty": "medium", "category": "critical_thinking",
        "question_text": "All roses are flowers. Some flowers fade quickly. Therefore:",
        "options": {
            "A": "All roses fade quickly",
            "B": "Some roses fade quickly",
            "C": "No roses fade quickly",
            "D": "None of the above can be concluded",
        },
        "correct_answer": "D",
        "explanation": "We cannot definitively conclude any of the first three statements.",
    },
    {
        "question_number": 4, "difficulty": "medium", "category": "core_logic",
        "question_text": "What is 15% of 240?",
        "options": {"A": "36", "B": "30", "C": "32", "D": "40"},
        "correct_answer": "A",
        "explanation": "240 * 0.15 = 36",
    },
    {
        "question_number": 5, "difficulty": "medium", "category": "domain_specific",
        "question_text": "Which data structure uses LIFO (Last In First Out) principle?",
        "options": {"A": "Queue", "B": "Stack", "C": "Linked List", "D": "Tree"},
        "correct_answer": "B",
        "explanation": "Stack is LIFO.",
    },
    {
        "question_number": 6, "difficulty": "hard", "category": "critical_thinking",
        "question_text": "If P implies Q, and Q implies R, which is necessarily true?",
        "options": {"A": "R implies P", "B": "P implies R", "C": "Not Q implies Not P only", "D": "P and R are equivalent"},
        "correct_answer": "B",
        "explanation": "Transitive property of implication.",
    },
    {
        "question_number": 7, "difficulty": "medium", "category": "domain_specific",
        "question_text": "What is the time complexity of binary search?",
        "options": {"A": "O(n)", "B": "O(n log n)", "C": "O(log n)", "D": "O(1)"},
        "correct_answer": "C",
        "explanation": "Binary search halves the search space each step.",
    },
    {
        "question_number": 8, "difficulty": "simple", "category": "core_logic",
        "question_text": "A shop offers a 20% discount on a 500 INR item. Final price?",
        "options": {"A": "400", "B": "450", "C": "380", "D": "420"},
        "correct_answer": "A",
        "explanation": "500 - (500*0.20) = 400",
    },
    {
        "question_number": 9, "difficulty": "hard", "category": "domain_specific",
        "question_text": "Which HTTP status code indicates 'Unauthorized'?",
        "options": {"A": "400", "B": "401", "C": "403", "D": "404"},
        "correct_answer": "B",
        "explanation": "401 = Unauthorized, 403 = Forbidden.",
    },
    {
        "question_number": 10, "difficulty": "medium", "category": "critical_thinking",
        "question_text": "If today is Wednesday, what day will it be 100 days from now?",
        "options": {"A": "Thursday", "B": "Friday", "C": "Saturday", "D": "Sunday"},
        "correct_answer": "B",
        "explanation": "100 mod 7 = 2; Wed + 2 = Friday",
    },
]


# ---------- Interview transcript builder ----------
def technical_transcript(cand_first):
    return [
        {"timestamp": "00:00:05", "speaker": "ai", "text": f"Hello {cand_first}, welcome to the technical interview. Let's start — can you briefly introduce yourself?", "sentiment": "neutral"},
        {"timestamp": "00:00:12", "speaker": "candidate", "text": f"Hi! I'm {cand_first}, a software engineer with three years of experience working primarily in Python and React.", "sentiment": "positive"},
        {"timestamp": "00:00:35", "speaker": "ai", "text": "Great. Can you explain the difference between SQL and NoSQL databases and when you would choose each?", "sentiment": "neutral"},
        {"timestamp": "00:00:50", "speaker": "candidate", "text": "SQL databases are relational and use a fixed schema with ACID transactions — good for structured data like financial records. NoSQL is schema-flexible and scales horizontally, great for unstructured or high-throughput workloads like product catalogs or analytics.", "sentiment": "positive"},
        {"timestamp": "00:01:20", "speaker": "ai", "text": "Good. Walk me through how you would design a URL shortener.", "sentiment": "neutral"},
        {"timestamp": "00:01:30", "speaker": "candidate", "text": "I'd start with a hashing approach — base62 encode an auto-increment id, store the mapping in a key-value store like Redis fronted by a relational DB. For scale I'd add a CDN cache and rate limiting at the edge.", "sentiment": "positive"},
        {"timestamp": "00:02:15", "speaker": "ai", "text": "What is the difference between processes and threads?", "sentiment": "neutral"},
        {"timestamp": "00:02:25", "speaker": "candidate", "text": "Processes have their own memory space, threads share memory within a process. Threads are cheaper to create but require synchronization. In Python, the GIL means CPU-bound work benefits more from multiprocessing.", "sentiment": "positive"},
        {"timestamp": "00:03:00", "speaker": "ai", "text": "Finally, what's the time complexity of inserting into a balanced BST?", "sentiment": "neutral"},
        {"timestamp": "00:03:08", "speaker": "candidate", "text": "O(log n) on average and in the worst case for a balanced tree like an AVL or red-black tree.", "sentiment": "positive"},
        {"timestamp": "00:03:30", "speaker": "ai", "text": "Excellent. That concludes the technical round. Thank you!", "sentiment": "positive"},
    ]


def hr_transcript(cand_first):
    return [
        {"timestamp": "00:00:05", "speaker": "ai", "text": f"Hi {cand_first}, welcome to the HR conversation. To start — tell me about a time you faced a conflict in a team and how you handled it.", "sentiment": "neutral"},
        {"timestamp": "00:00:18", "speaker": "candidate", "text": "Sure. In my last project two engineers disagreed on architecture. I scheduled a 30-minute whiteboarding session, let each present their case, and we agreed on a hybrid approach. The feature shipped a week later than planned but with full buy-in.", "sentiment": "positive"},
        {"timestamp": "00:00:55", "speaker": "ai", "text": "Where do you see yourself in five years?", "sentiment": "neutral"},
        {"timestamp": "00:01:05", "speaker": "candidate", "text": "Leading a small platform team, ideally still close to the code, mentoring junior engineers, and owning architectural decisions for a major product surface.", "sentiment": "positive"},
        {"timestamp": "00:01:35", "speaker": "ai", "text": "What motivates you to come to work each day?", "sentiment": "neutral"},
        {"timestamp": "00:01:43", "speaker": "candidate", "text": "Solving customer problems with clean technical solutions, and seeing teammates grow. I find autonomy and trust energising.", "sentiment": "positive"},
        {"timestamp": "00:02:10", "speaker": "ai", "text": "Tell me about a failure and what you learned.", "sentiment": "neutral"},
        {"timestamp": "00:02:20", "speaker": "candidate", "text": "I once pushed a migration without a rollback plan; it caused 30 minutes of partial downtime. I learned to always design for reversibility and added a runbook template to our repo so the team would never repeat it.", "sentiment": "neutral"},
        {"timestamp": "00:02:55", "speaker": "ai", "text": "Why do you want to join us?", "sentiment": "neutral"},
        {"timestamp": "00:03:02", "speaker": "candidate", "text": "Your engineering blog showed me a culture that values craft. The product solves a problem I care about and the role gives me space to grow into a tech-lead trajectory.", "sentiment": "positive"},
        {"timestamp": "00:03:35", "speaker": "ai", "text": "Thank you, that concludes the HR round.", "sentiment": "positive"},
    ]


# ---------- Main seeder ----------
async def main():
    engine = create_async_engine(DATABASE_URL, future=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        now = datetime.now(timezone.utc)

        # === Company ===
        company_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO companies (company_id, company_name, email, industry, size, website,
                                   subscription_plan, is_active, workspace_id, created_at, updated_at,
                                   created_by, updated_by, status)
            VALUES (:cid, :name, :email, :ind, :sz, :web, :plan, true, :ws, :now, :now, :sys, :sys, 'active')
        """), {
            "cid": company_id, "name": "Acme Innovations", "email": "hr@acmeinnov.test",
            "ind": "Technology", "sz": "51-200", "web": "https://acmeinnov.test",
            "plan": "professional", "ws": WORKSPACE_ID, "now": now, "sys": SYS_USER,
        })
        print(f"✓ Company created: {company_id}")

        # === Job Requirement (reuse target) ===
        job_id = TARGET_JOB_ID
        existing = await db.execute(text("SELECT 1 FROM job_requirements WHERE job_requirement_id = :j"), {"j": job_id})
        if existing.first():
            print(f"✓ Reusing existing job: {job_id}")
        else:
            requirements = [
                {"skill": "Python", "level": "advanced", "required": True},
                {"skill": "FastAPI", "level": "intermediate", "required": True},
                {"skill": "PostgreSQL", "level": "intermediate", "required": True},
                {"skill": "React", "level": "intermediate", "required": False},
                {"skill": "AWS", "level": "intermediate", "required": False},
            ]
            await db.execute(text("""
                INSERT INTO job_requirements (job_requirement_id, company_id, title, department, description,
                                              requirements, experience, location, job_type, salary_range,
                                              benefits, status, workspace_id, created_at, updated_at,
                                              created_by, updated_by, is_active)
                VALUES (:jid, :cid, :title, :dept, :desc, :req, :exp, :loc, :jt, :sal, :ben,
                        'active', :ws, :now, :now, :sys, :sys, true)
            """), {
                "jid": job_id, "cid": company_id,
                "title": "Full stack Developer",
                "dept": "Engineering",
                "desc": "Full stack developer role.",
                "req": json.dumps(requirements),
                "exp": json.dumps({"minYears": 3, "maxYears": 7, "preferred": 5}),
                "loc": "Bengaluru, India (Hybrid)",
                "jt": "full-time",
                "sal": json.dumps({"min": 1800000, "max": 3000000, "currency": "INR"}),
                "ben": json.dumps(["Health insurance", "Stock options"]),
                "ws": WORKSPACE_ID, "now": now, "sys": SYS_USER,
            })
            print(f"✓ Job created: {job_id}")

        # === Aptitude Test ===
        test_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO aptitude_tests (aptitude_test_id, job_requirement_id, test_title,
                                        total_questions, total_time_minutes, passing_score_percentage,
                                        test_metadata, is_active, workspace_id, created_at, updated_at,
                                        created_by, updated_by, status)
            VALUES (:tid, :jid, :title, :tq, 30, 60, :meta, true, :ws, :now, :now, :sys, :sys, 'active')
        """), {
            "tid": test_id, "jid": job_id,
            "title": "Senior Backend Engineer — Aptitude Assessment",
            "tq": len(QUESTIONS),
            "meta": json.dumps({"source": "seed_fake_data"}),
            "ws": WORKSPACE_ID, "now": now, "sys": SYS_USER,
        })

        # Questions
        for q in QUESTIONS:
            await db.execute(text("""
                INSERT INTO aptitude_questions (question_id, job_requirement_id, aptitude_test_id,
                                                question_number, difficulty, category, question_text,
                                                options, correct_answer, explanation,
                                                time_allocated_seconds, tags, workspace_id,
                                                created_at, updated_at, status, is_active)
                VALUES (:qid, :jid, :tid, :qn, :diff, :cat, :qtext, :opts, :ans, :expl,
                        90, :tags, :ws, :now, :now, 'active', true)
            """), {
                "qid": uuid.uuid4(), "jid": job_id, "tid": test_id,
                "qn": q["question_number"], "diff": q["difficulty"], "cat": q["category"],
                "qtext": q["question_text"], "opts": json.dumps(q["options"]),
                "ans": q["correct_answer"], "expl": q["explanation"],
                "tags": json.dumps([q["category"]]), "ws": WORKSPACE_ID, "now": now,
            })
        print(f"✓ Aptitude test + {len(QUESTIONS)} questions created: {test_id}")

        # === Candidates ===
        for idx, (first, last, email, phone, loc, stage, apt_pass, tech_pass, hr_pass) in enumerate(FAKE_CANDIDATES):
            cand_id = uuid.uuid4()
            password = rand_password()

            # Copy resume
            src = assign_resume(idx)
            dst = RESUME_DEST / f"{cand_id}.pdf"
            shutil.copyfile(src, dst)
            resume_url = f"resume/{cand_id}.pdf"

            created_at = now - timedelta(days=10 - idx)
            resume_score = round(random.uniform(72, 92), 2)

            # Stage flags
            apt_taken = stage >= 2
            tech_taken = stage >= 3
            hr_taken = stage >= 4

            apt_score = None
            tech_score = None
            hr_score = None
            apt_result_str = None
            tech_result_str = None
            hr_result_str = None
            if apt_taken:
                apt_score = round(random.uniform(72, 92) if apt_pass else random.uniform(35, 55), 2)
                apt_result_str = "pass" if apt_pass else "fail"
            if tech_taken:
                tech_score = round(random.uniform(75, 90) if tech_pass else random.uniform(40, 55), 2)
                tech_result_str = "pass" if tech_pass else "fail"
            if hr_taken:
                hr_score = round(random.uniform(78, 92) if hr_pass else random.uniform(40, 55), 2)
                hr_result_str = "pass" if hr_pass else "fail"

            await db.execute(text("""
                INSERT INTO candidates (candidate_id, job_requirement_id, first_name, last_name, email,
                                        password, phone, linkedin_url, current_location,
                                        willing_to_relocate, skills, expected_salary, notice_period,
                                        resume_url, candidate_resume_score, status,
                                        aptitude_test, technical_test, hr_test,
                                        aptitude_test_result, technical_test_result, hr_test_result,
                                        aptitude_test_score, technical_test_score, hr_test_score,
                                        resume_selected, workspace_id, created_at, updated_at,
                                        created_by, updated_by, is_active)
                VALUES (:cid, :jid, :fn, :ln, :em, :pw, :ph, :li, :loc, true, :skills, :sal, :np,
                        :ru, :rs, 'active', :at, :tt, :ht, :ar, :tr, :hr_r, :as_, :ts, :hs,
                        true, :ws, :ca, :ca, :sys, :sys, true)
            """), {
                "cid": cand_id, "jid": job_id,
                "fn": first, "ln": last, "em": email, "pw": password, "ph": phone,
                "li": f"https://linkedin.com/in/{first.lower()}{last.lower()}",
                "loc": loc, "skills": json.dumps(["Python", "FastAPI", "PostgreSQL", "React"]),
                "sal": float(random.choice([1800000, 2000000, 2200000, 2400000, 2700000])),
                "np": random.choice(["Immediate", "15 days", "30 days", "60 days"]),
                "ru": resume_url, "rs": resume_score,
                "at": apt_taken, "tt": tech_taken, "ht": hr_taken,
                "ar": apt_result_str, "tr": tech_result_str, "hr_r": hr_result_str,
                "as_": apt_score, "ts": tech_score, "hs": hr_score,
                "ws": WORKSPACE_ID, "ca": created_at, "sys": SYS_USER,
            })
            print(f"✓ Candidate {first} {last} — stage {stage}  apt={apt_result_str} tech={tech_result_str} hr={hr_result_str}")

            # === Aptitude attempt ===
            if apt_taken:
                # Build answer map (50% correct if fail, 90% correct if pass approx based on score)
                answers = {}
                correct_count = 0
                for q in QUESTIONS:
                    # Probability of correct = apt_score/100, capped
                    p_correct = (apt_score or 50) / 100
                    if random.random() < p_correct:
                        answers[str(q["question_number"] - 1)] = q["correct_answer"]
                        correct_count += 1
                    else:
                        wrong_options = [k for k in q["options"].keys() if k != q["correct_answer"]]
                        answers[str(q["question_number"] - 1)] = random.choice(wrong_options)

                started = created_at + timedelta(days=1)
                submitted = started + timedelta(minutes=random.randint(20, 40))
                await db.execute(text("""
                    INSERT INTO aptitude_test_attempts (attempt_id, aptitude_test_id, job_requirement_id,
                                                       candidate_email, candidate_name, user_attempt,
                                                       started_at, submitted_at, time_taken_seconds,
                                                       answers, score, correct_answers_count,
                                                       total_questions_attempted, passed, tab_switches,
                                                       status, workspace_id, created_at, updated_at,
                                                       is_active)
                    VALUES (:aid, :tid, :jid, :em, :name, 1, :st, :sb, :tk, :ans, :sc, :cc, :tq,
                            :passed, 0, 'completed', :ws, :now, :now, true)
                """), {
                    "aid": uuid.uuid4(), "tid": test_id, "jid": job_id,
                    "em": email, "name": f"{first} {last}",
                    "st": started.isoformat(), "sb": submitted.isoformat(),
                    "tk": int((submitted - started).total_seconds()),
                    "ans": json.dumps(answers),
                    "sc": apt_score, "cc": correct_count, "tq": len(QUESTIONS),
                    "passed": apt_pass, "ws": WORKSPACE_ID, "now": now,
                })

            # === Technical interview ===
            if tech_taken:
                started = created_at + timedelta(days=3)
                ended = started + timedelta(minutes=random.randint(8, 14))
                duration = int((ended - started).total_seconds())
                transcript = technical_transcript(first)
                rating = "good" if tech_pass else "below_average"
                await db.execute(text("""
                    INSERT INTO technical_interviews (
                        technical_interview_id, job_requirement_id, candidate_id,
                        interview_session_id, interview_started_at, interview_ended_at,
                        interview_duration_seconds, interview_status,
                        overall_score, overall_rating,
                        technical_knowledge_score, domain_expertise_score,
                        communication_score, language_proficiency_score,
                        confidence_score, professionalism_score,
                        response_relevance_score, response_depth_score, response_clarity_score,
                        total_questions_asked, questions_answered, questions_skipped,
                        average_response_time_seconds, total_speaking_time_seconds,
                        engagement_score, interview_transcript, question_analysis,
                        skills_assessment, candidate_strengths, candidate_weaknesses,
                        ai_recommendation, ai_recommendation_reason, ai_feedback_summary,
                        improvement_areas, interview_language, languages_used, ai_model_used,
                        result, passed_threshold, workspace_id,
                        created_at, updated_at, created_by, updated_by, status, is_active
                    ) VALUES (
                        :iid, :jid, :cid, :sess, :st, :en, :dur, 'completed',
                        :os, :rating, :ts1, :ts2, :cs, :lps, :conf, :prof, :rrs, :rds, :rcs,
                        5, 5, 0, 6.5, 180.0, :eng, :tr, :qa, :sa, :strn, :weak,
                        :rec, :reason, :feedback, :improve, 'English', :langs, 'gemini-2.5-flash-native-audio',
                        :res, 60.0, :ws, :now, :now, :sys, :sys, 'active', true
                    )
                """), {
                    "iid": uuid.uuid4(), "jid": job_id, "cid": cand_id,
                    "sess": f"sess_{cand_id.hex[:12]}",
                    "st": started, "en": ended, "dur": duration,
                    "os": tech_score, "rating": rating,
                    "ts1": tech_score, "ts2": round(tech_score - 3, 2),
                    "cs": round(tech_score + 2, 2), "lps": round(tech_score + 1, 2),
                    "conf": round(tech_score - 1, 2), "prof": round(tech_score + 3, 2),
                    "rrs": round(tech_score + 1, 2), "rds": round(tech_score - 2, 2),
                    "rcs": round(tech_score + 2, 2),
                    "eng": round(tech_score, 2),
                    "tr": json.dumps(transcript),
                    "qa": json.dumps([
                        {"question_number": 1, "question_text": "Introduce yourself", "question_category": "behavioral", "difficulty": "easy", "response_score": 80, "feedback": "Clear, concise intro."},
                        {"question_number": 2, "question_text": "SQL vs NoSQL", "question_category": "technical", "difficulty": "medium", "response_score": 85, "feedback": "Good real-world examples."},
                        {"question_number": 3, "question_text": "Design URL shortener", "question_category": "technical", "difficulty": "hard", "response_score": 78, "feedback": "Solid sketch, missed cache eviction strategy."},
                        {"question_number": 4, "question_text": "Processes vs threads", "question_category": "technical", "difficulty": "medium", "response_score": 82, "feedback": "Mentioned GIL — good."},
                        {"question_number": 5, "question_text": "Binary search complexity", "question_category": "technical", "difficulty": "easy", "response_score": 90, "feedback": "Correct and precise."},
                    ]),
                    "sa": json.dumps([
                        {"skill_name": "Python", "skill_category": "programming", "proficiency_level": "advanced", "score": 85, "evidence": "Discussed GIL and multiprocessing tradeoffs."},
                        {"skill_name": "System Design", "skill_category": "architecture", "proficiency_level": "intermediate", "score": 78, "evidence": "Sketched URL shortener but light on cache details."},
                        {"skill_name": "Databases", "skill_category": "data", "proficiency_level": "intermediate", "score": 80, "evidence": "Clear SQL/NoSQL trade-off explanation."},
                    ]),
                    "strn": json.dumps(["Clear technical communication", "Solid CS fundamentals", "Practical real-world examples"] if tech_pass else ["Friendly demeanor"]),
                    "weak": json.dumps(["Light on advanced system design", "Could elaborate on testing strategy"] if tech_pass else ["Struggled with system design", "Shallow database knowledge"]),
                    "rec": "recommend" if tech_pass else "not_recommend",
                    "reason": "Candidate showed strong fundamentals and good communication; ready for next round." if tech_pass else "Candidate lacks the depth required for a senior role at this time.",
                    "feedback": f"{first} demonstrated good technical fluency in core areas. " + ("Recommended to proceed to HR round." if tech_pass else "Would benefit from more system-design practice."),
                    "improve": json.dumps(["System design depth", "Distributed systems patterns"]),
                    "langs": json.dumps(["English"]),
                    "res": tech_result_str,
                    "ws": WORKSPACE_ID, "now": now, "sys": SYS_USER,
                })

            # === HR interview ===
            if hr_taken:
                started = created_at + timedelta(days=5)
                ended = started + timedelta(minutes=random.randint(7, 12))
                duration = int((ended - started).total_seconds())
                transcript = hr_transcript(first)
                rating = "good" if hr_pass else "below_average"
                await db.execute(text("""
                    INSERT INTO hr_interviews (
                        hr_interview_id, job_requirement_id, candidate_id,
                        interview_session_id, interview_started_at, interview_ended_at,
                        interview_duration_seconds, interview_status,
                        overall_score, overall_rating,
                        communication_score, language_proficiency_score, articulation_score,
                        confidence_score, professionalism_score, attitude_score,
                        teamwork_score, leadership_score, problem_solving_score, adaptability_score,
                        cultural_fit_score, motivation_score,
                        response_relevance_score, response_depth_score, response_clarity_score,
                        total_questions_asked, questions_answered, questions_skipped,
                        average_response_time_seconds, total_speaking_time_seconds,
                        engagement_score, interview_transcript, question_analysis,
                        soft_skills_assessment, candidate_strengths, candidate_weaknesses,
                        ai_recommendation, ai_recommendation_reason, ai_feedback_summary,
                        improvement_areas, interview_language, languages_used, ai_model_used,
                        result, passed_threshold, workspace_id,
                        created_at, updated_at, created_by, updated_by, status, is_active
                    ) VALUES (
                        :iid, :jid, :cid, :sess, :st, :en, :dur, 'completed',
                        :os, :rating,
                        :cs, :lps, :art, :conf, :prof, :att,
                        :tw, :ld, :ps, :ad, :cf, :mv,
                        :rrs, :rds, :rcs, 5, 5, 0, 7.0, 200.0, :eng,
                        :tr, :qa, :ssa, :strn, :weak,
                        :rec, :reason, :feedback, :improve, 'English', :langs, 'gemini-2.5-flash-native-audio',
                        :res, 60.0, :ws, :now, :now, :sys, :sys, 'active', true
                    )
                """), {
                    "iid": uuid.uuid4(), "jid": job_id, "cid": cand_id,
                    "sess": f"hrsess_{cand_id.hex[:12]}",
                    "st": started, "en": ended, "dur": duration,
                    "os": hr_score, "rating": rating,
                    "cs": round(hr_score + 1, 2), "lps": round(hr_score, 2), "art": round(hr_score + 2, 2),
                    "conf": round(hr_score - 1, 2), "prof": round(hr_score + 2, 2), "att": round(hr_score + 3, 2),
                    "tw": round(hr_score + 1, 2), "ld": round(hr_score - 4, 2),
                    "ps": round(hr_score, 2), "ad": round(hr_score + 1, 2),
                    "cf": round(hr_score + 2, 2), "mv": round(hr_score + 3, 2),
                    "rrs": round(hr_score + 1, 2), "rds": round(hr_score - 2, 2), "rcs": round(hr_score + 2, 2),
                    "eng": round(hr_score, 2),
                    "tr": json.dumps(transcript),
                    "qa": json.dumps([
                        {"question_number": 1, "question_text": "Tell me about a team conflict", "question_category": "behavioral", "difficulty": "medium", "response_score": 82, "feedback": "Good STAR structure."},
                        {"question_number": 2, "question_text": "Where do you see yourself in 5 years?", "question_category": "career", "difficulty": "easy", "response_score": 80, "feedback": "Clear ambitions aligned to role."},
                        {"question_number": 3, "question_text": "What motivates you?", "question_category": "cultural", "difficulty": "easy", "response_score": 85, "feedback": "Authentic answer."},
                        {"question_number": 4, "question_text": "Tell me about a failure", "question_category": "behavioral", "difficulty": "medium", "response_score": 78, "feedback": "Took responsibility, identified learning."},
                        {"question_number": 5, "question_text": "Why join us?", "question_category": "cultural", "difficulty": "easy", "response_score": 84, "feedback": "Researched the company well."},
                    ]),
                    "ssa": json.dumps([
                        {"skill_name": "Communication", "skill_category": "interpersonal", "proficiency_level": "advanced", "score": 85, "evidence": "Clear articulation throughout."},
                        {"skill_name": "Teamwork", "skill_category": "interpersonal", "proficiency_level": "advanced", "score": 84, "evidence": "Conflict-resolution example."},
                        {"skill_name": "Cultural Fit", "skill_category": "values", "proficiency_level": "advanced", "score": 86, "evidence": "Values align with engineering culture."},
                    ]),
                    "strn": json.dumps(["Strong communication", "Self-aware", "Team-oriented"] if hr_pass else ["Polite and respectful"]),
                    "weak": json.dumps(["Could give more concrete leadership examples"] if hr_pass else ["Vague answers", "Limited examples", "Low energy"]),
                    "rec": "recommend" if hr_pass else "not_recommend",
                    "reason": "Cultural fit and communication are strong; proceed to offer." if hr_pass else "Concerns around fit and engagement at this stage.",
                    "feedback": f"{first} demonstrated " + ("strong soft skills and clear motivation." if hr_pass else "limited depth in behavioral responses."),
                    "improve": json.dumps(["More concrete leadership stories", "Larger-scale conflict examples"]),
                    "langs": json.dumps(["English"]),
                    "res": hr_result_str,
                    "ws": WORKSPACE_ID, "now": now, "sys": SYS_USER,
                })

        await db.commit()
        print("\n✅ Seed complete. Summary:")
        print(f"   Company:     Acme Innovations")
        print(f"   Job:         Senior Backend Engineer ({job_id})")
        print(f"   Candidates:  {len(FAKE_CANDIDATES)}")
        print("   Pipeline distribution:")
        print("     Stage 1 (resume only):                 2")
        print("     Stage 2 (resume + aptitude):           2  (1 pass / 1 fail)")
        print("     Stage 3 (resume + aptitude + tech):    1  (passed)")
        print("     Stage 4 (ALL completed):               3  (eligible for AI report)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
