from dotenv import load_dotenv
from google import genai
import json
import os
import re


load_dotenv()

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)


# =========================================================
# DEFAULT ANALYSIS RESULT
# =========================================================

def _empty_result(error=None):

    result = {

        "ats_score": 0,

        "section_scores": {
            "skills": 0,
            "experience": 0,
            "projects": 0,
            "education": 0,
            "keywords": 0,
            "formatting": 0,
        },

        "resume_summary": "",

        "skills": [],

        "matched_skills": [],

        "missing_skills": [],

        "keyword_suggestions": [],

        "strengths": [],

        "weaknesses": [],

        "improvement_suggestions": [],

        "rewritten_bullets": [],

        "job_recommendations": [],

        "project_analysis": [],

        "roadmap": [],

        "interview_questions": [],

        "jd_match_score": 0,
    }

    if error:
        result["error"] = error

    return result


# =========================================================
# GEMINI JSON EXTRACTOR
# =========================================================

def _extract_json(text):

    if not text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:

        raise ValueError(
            "Gemini response did not contain valid JSON."
        )

    return json.loads(
        text[start:end + 1]
    )


# =========================================================
# MERGE MISSING RESULT FIELDS
# =========================================================

def _merge_defaults(data):

    defaults = _empty_result()

    if not isinstance(data, dict):
        return defaults

    defaults.update(data)

    if not isinstance(
        defaults.get("section_scores"),
        dict
    ):

        defaults["section_scores"] = (
            _empty_result()["section_scores"]
        )

    else:

        section_defaults = (
            _empty_result()["section_scores"]
        )

        section_defaults.update(
            defaults["section_scores"]
        )

        defaults["section_scores"] = (
            section_defaults
        )

    return defaults


# =========================================================
# BASIC RESUME STRUCTURE CHECK
# =========================================================

def _basic_resume_structure_check(text):

    cleaned = re.sub(
        r"\s+",
        " ",
        (text or "")
    ).strip()

    if len(cleaned) < 250:

        return (
            False,
            "The document contains too little "
            "readable information to be a Resume/CV."
        )

    if len(cleaned.split()) < 45:

        return (
            False,
            "The document does not contain enough "
            "Resume/CV content."
        )

    lower = cleaned.lower()

    section_terms = [

        "education",
        "qualification",
        "academic",

        "skills",
        "technical skills",

        "experience",
        "work experience",
        "employment",

        "internship",
        "internships",

        "projects",
        "project",

        "certification",
        "certifications",

        "achievement",
        "achievements",

        "objective",
        "summary",
        "profile"
    ]

    identity_signals = 0


    # Email
    if re.search(
        r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        cleaned
    ):

        identity_signals += 1


    # Phone
    if re.search(
        r"(?:\+?\d[\d\s().-]{8,}\d)",
        cleaned
    ):

        identity_signals += 1


    # Professional links
    if (
        "linkedin" in lower
        or "github" in lower
        or "portfolio" in lower
    ):

        identity_signals += 1


    section_hits = sum(

        1

        for term in section_terms

        if term in lower

    )


    if section_hits < 2 and identity_signals == 0:

        return (
            False,
            "The document does not appear to "
            "contain a candidate profile or "
            "Resume/CV structure."
        )


    return (
        True,
        "Local structure check passed."
    )


# =========================================================
# STRICT RESUME / CV VALIDATOR
# =========================================================

def validate_resume_document(resume_text):

    cleaned_text = (
        resume_text or ""
    ).strip()


    basic_ok, basic_reason = (
        _basic_resume_structure_check(
            cleaned_text
        )
    )


    if not basic_ok:

        return {

            "is_resume": False,

            "confidence": 0,

            "reason": basic_reason,

            "verification_error": False,
        }


    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    if not api_key:

        return {

            "is_resume": False,

            "confidence": 0,

            "reason":
                "Resume verification service "
                "is not configured.",

            "verification_error": True,
        }


    client = genai.Client(
        api_key=api_key
    )


    prompt = f"""
You are a strict document classifier for an AI Resume Analyzer.

Your ONLY task is to decide whether the supplied text is genuinely
a person's Resume or CV.

ACCEPT when the document clearly represents one person's
professional or academic profile.

Typical Resume/CV information may include:

- candidate identity/contact/profile information
- education
- qualifications
- skills
- work experience
- internships
- projects
- certifications
- achievements
- professional summary
- objective

A fresher/student Resume is valid even when the candidate
does not have full-time work experience.

REJECT:

- study notes
- books
- articles
- assignments
- question papers
- certificates by themselves
- invoices
- bills
- receipts
- forms
- letters
- job descriptions
- company profiles
- brochures
- advertisements
- reports
- research papers
- random text
- copied web content
- simple skill lists with no candidate identity
- image/photo converted to PDF without meaningful resume content
- unrelated documents containing words such as skills,
  education or experience

Be conservative.

If uncertain, reject the document.

Return ONLY valid JSON:

{{
    "is_resume": false,
    "confidence": 0,
    "reason": ""
}}

Rules:

- confidence must be an integer between 0 and 100
- is_resume can be true only when confidence >= 70
- reason must be one short sentence

DOCUMENT TEXT:

{cleaned_text[:14000]}
"""


    try:

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt
        )


        parsed = _extract_json(
            response.text
        )


        is_resume = bool(
            parsed.get(
                "is_resume",
                False
            )
        )


        try:

            confidence = int(
                parsed.get(
                    "confidence",
                    0
                )
            )

        except (TypeError, ValueError):

            confidence = 0


        confidence = max(
            0,
            min(
                100,
                confidence
            )
        )


        reason = str(

            parsed.get(
                "reason",
                "Unable to verify document type."
            )

        ).strip()


        accepted = (
            is_resume
            and confidence >= 70
        )


        return {

            "is_resume": accepted,

            "confidence": confidence,

            "reason": reason,

            "verification_error": False,
        }


    except Exception as exc:

        return {

            "is_resume": False,

            "confidence": 0,

            "reason":
                f"Resume verification failed: {exc}",

            "verification_error": True,
        }


# =========================================================
# MAIN RESUME ANALYZER
# =========================================================

def analyze_resume(
    resume_text,
    user_goal,
    job_description=""
):


    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    if not api_key:

        return _empty_result(
            "GEMINI_API_KEY is not set."
        )


    if not resume_text or not resume_text.strip():

        return _empty_result(
            "Resume text is empty."
        )


    client = genai.Client(
        api_key=api_key
    )


    jd = (

        job_description.strip()

        if job_description

        else "Not provided"

    )


    prompt = f"""
You are a senior ATS specialist, technical recruiter,
career coach and hiring manager.

Analyze the validated Resume/CV for the target role.

If a Job Description is supplied, compare the resume
against that Job Description.

TARGET ROLE:

{user_goal}


JOB DESCRIPTION:

{jd}


RESUME:

{resume_text}


IMPORTANT RULES:

- Base candidate facts ONLY on information available in the resume.
- Never invent work experience.
- Never invent education.
- Never invent projects.
- Never invent certifications.
- Never invent technologies.
- Never invent achievements.
- Never invent numbers or metrics.

- Missing skills may come from the target role or Job Description.

- ATS Score must be between 0 and 100.

- JD Match Score must be between 0 and 100.

- If no Job Description is supplied,
  JD Match Score must be 0.

- Every section score must be between 0 and 100.

- Resume rewriting must improve language only.
  Do not invent achievements or metrics.

- Interview questions must be personalized
  according to the candidate resume.

- Roadmap must focus on genuine missing skills.

- Recommendations should be practical,
  concise and interview/job oriented.


Return ONLY valid JSON:

{{
    "ats_score": 0,

    "jd_match_score": 0,

    "section_scores": {{
        "skills": 0,
        "experience": 0,
        "projects": 0,
        "education": 0,
        "keywords": 0,
        "formatting": 0
    }},

    "resume_summary": "",

    "skills": [],

    "matched_skills": [],

    "missing_skills": [],

    "keyword_suggestions": [],

    "strengths": [],

    "weaknesses": [],

    "improvement_suggestions": [],

    "rewritten_bullets": [
        {{
            "original": "",
            "improved": ""
        }}
    ],

    "job_recommendations": [
        {{
            "role": "",
            "fit_score": 0,
            "reason": ""
        }}
    ],

    "project_analysis": [
        {{
            "project": "",
            "score": 0,
            "strengths": [],
            "improvements": []
        }}
    ],

    "roadmap": [
        {{
            "step": 1,
            "skill": "",
            "why": "",
            "action": ""
        }}
    ],

    "interview_questions": [
        {{
            "question": "",
            "type": "technical",
            "focus": ""
        }}
    ]
}}
"""


    try:

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt
        )


        parsed = _extract_json(
            response.text
        )


        return _merge_defaults(
            parsed
        )


    except Exception as exc:

        return _empty_result(

            f"Failed to analyze resume: {exc}"

        )


# =========================================================
# MULTIPLE RESUME RECRUITER RANKING
# =========================================================

def rank_candidates(
    candidates,
    target_role,
    job_description=""
):


    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    if not api_key:

        return {

            "error":
                "GEMINI_API_KEY is not set.",

            "ranking": []
        }


    if not candidates:

        return {

            "error":
                "No valid resumes were provided.",

            "ranking": []
        }


    client = genai.Client(
        api_key=api_key
    )


    payload = []


    for item in candidates:

        payload.append({

            "candidate_id":
                item["candidate_id"],

            "filename":
                item["filename"],

            "resume_text":
                (
                    item.get(
                        "resume_text"
                    )
                    or ""
                )[:9000]
        })


    prompt = f"""
You are a senior technical recruiter and ATS ranking system.

Rank ONLY the provided VALIDATED candidate resumes
for the given target role.


TARGET ROLE:

{target_role}


JOB DESCRIPTION:

{
    job_description.strip()
    if job_description
    else "Not provided"
}


CANDIDATES:

{json.dumps(payload, ensure_ascii=False)}


RULES:

- Use ONLY facts contained in candidate resumes.
- Never invent skills.
- Never invent experience.
- Never invent education.
- Never invent projects.
- Never invent achievements.
- Never invent certifications.

- If a Job Description is supplied,
  JD alignment should have strong weighting.

- If no Job Description is supplied,
  rank candidates according to:

  skills,
  relevant experience,
  internships,
  projects,
  education,
  resume quality,
  target role relevance.

- final_score must be 0-100.
- ats_score must be 0-100.
- jd_match_score must be 0-100.

- jd_match_score must be 0 when no JD is supplied.

- Every candidate must appear exactly once.

- Rank 1 means best candidate.


Return ONLY valid JSON:

{{
    "ranking": [

        {{
            "rank": 1,

            "candidate_id": "C1",

            "filename": "resume.pdf",

            "final_score": 0,

            "ats_score": 0,

            "jd_match_score": 0,

            "top_skills": [],

            "missing_skills": [],

            "strengths": [],

            "risks": [],

            "recommendation":
                "Strong Yes|Yes|Maybe|No",

            "reason": ""
        }}

    ]
}}
"""


    try:

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt
        )


        data = _extract_json(
            response.text
        )


        ranking = (

            data.get("ranking")

            if isinstance(
                data,
                dict
            )

            else []
        )


        if not isinstance(
            ranking,
            list
        ):

            ranking = []


        ranking.sort(

            key=lambda x:
                int(
                    x.get(
                        "rank",
                        999
                    )
                )

        )


        return {
            "ranking": ranking
        }


    except Exception as exc:

        return {

            "error":
                f"Failed to rank candidates: {exc}",

            "ranking": []
        }


# =========================================================
# MOCK INTERVIEW QUESTION GENERATOR
# =========================================================

def generate_mock_interview(
    resume_text,
    target_role,
    count=8
):


    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    if not api_key:

        return {

            "error":
                "GEMINI_API_KEY is not set.",

            "questions": []
        }


    client = genai.Client(
        api_key=api_key
    )


    prompt = f"""
You are an interviewer hiring for:

{target_role}


Create {count} personalized interview questions
using this candidate's resume.

Question types should include:

- technical
- project based
- behavioral
- role fit

Do not assume facts not present in the resume.


RESUME:

{(resume_text or "")[:14000]}


Return ONLY valid JSON:

{{
    "questions": [

        {{
            "id": 1,

            "type": "technical",

            "question": "",

            "what_good_answer_should_cover": ""
        }}

    ]
}}
"""


    try:

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt
        )


        data = _extract_json(
            response.text
        )


        questions = (

            data.get(
                "questions"
            )

            if isinstance(
                data,
                dict
            )

            else []
        )


        return {

            "questions":

                questions

                if isinstance(
                    questions,
                    list
                )

                else []
        }


    except Exception as exc:

        return {

            "error":
                f"Failed to generate interview: {exc}",

            "questions": []
        }


# =========================================================
# MOCK INTERVIEW ANSWER EVALUATOR
# =========================================================

def evaluate_mock_interview(
    resume_text,
    target_role,
    answers
):


    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    if not api_key:

        return {
            "error":
                "GEMINI_API_KEY is not set."
        }


    client = genai.Client(
        api_key=api_key
    )


    prompt = f"""
You are a fair technical interviewer.

TARGET ROLE:

{target_role}


Evaluate the candidate's answers using:

- interview questions
- candidate responses
- resume context
- target role knowledge

Do not penalize the candidate for resume facts
they never claimed unless the question is testing
general knowledge required for the role.

Give practical feedback in clear English.


RESUME:

{(resume_text or "")[:12000]}


QUESTION AND ANSWER DATA:

{json.dumps(
    answers,
    ensure_ascii=False
)}


Return ONLY valid JSON:

{{
    "overall_score": 0,

    "hire_signal":
        "Strong Yes|Yes|Maybe|No",

    "strengths": [],

    "improvements": [],

    "answer_feedback": [

        {{
            "id": 1,

            "score": 0,

            "feedback": "",

            "better_answer_tip": ""
        }}

    ]
}}
"""


    try:

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt
        )


        return _extract_json(
            response.text
        )


    except Exception as exc:

        return {

            "error":
                f"Failed to evaluate interview: {exc}"
        }


# =========================================================
# ATS RESUME BUILDER
# =========================================================

def build_ats_resume(profile):


    api_key = os.getenv(
        "GEMINI_API_KEY"
    )


    if not api_key:

        return {

            "error":
                "GEMINI_API_KEY is not set."
        }


    client = genai.Client(
        api_key=api_key
    )


    prompt = f"""
You are an ATS professional resume writer.

Create a concise professional and
one-page-friendly Resume using ONLY
the facts supplied by the user.

Never invent:

- employers
- dates
- metrics
- technologies
- degrees
- certifications
- achievements
- project details

Improve only:

- wording
- structure
- clarity
- ATS readability


USER DATA:

{json.dumps(
    profile,
    ensure_ascii=False
)}


Return ONLY valid JSON:

{{
    "headline": "",

    "professional_summary": "",

    "skills": [],

    "experience": [

        {{
            "title": "",

            "organization": "",

            "details": [""]
        }}

    ],

    "projects": [

        {{
            "name": "",

            "details": [""]
        }}

    ],

    "education": [""],

    "certifications": [""],

    "ats_keywords": []
}}
"""


    try:

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt
        )


        return _extract_json(
            response.text
        )


    except Exception as exc:

        return {

            "error":
                f"Failed to build resume: {exc}"
        }

# =========================================================
# AUTO IMPROVE RESUME
# =========================================================

def improve_resume(resume_text, analysis_result, target_role, job_description=""):
    """Improve a validated resume without inventing candidate facts."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY is not set."}

    resume_text = (resume_text or "").strip()
    if not resume_text:
        return {"error": "Resume text is empty."}

    analysis_result = analysis_result if isinstance(analysis_result, dict) else {}
    jd = (job_description or "").strip() or "Not provided"

    client = genai.Client(api_key=api_key)

    prompt = f'''You are a senior ATS resume editor.

Improve the candidate's resume for the target role using ONLY facts explicitly present in the ORIGINAL RESUME.
Use the analysis only as editing guidance.

TARGET ROLE:
{target_role}

JOB DESCRIPTION:
{jd}

ANALYSIS:
{json.dumps(analysis_result, ensure_ascii=False)}

ORIGINAL RESUME:
{resume_text[:18000]}

STRICT RULES:
- Never invent skills, experience, employers, titles, dates, education, certifications, projects, achievements, responsibilities, technologies, metrics, percentages, links, or contact details.
- Missing skills and suggested keywords must NOT be added as candidate skills unless the original resume supports them.
- You may improve wording, ordering, clarity, action verbs, structure, and ATS readability.
- You may use target-role/JD terminology only when supported by the original resume.
- Unsupported recommendations must be listed separately in not_added_recommendations.
- Preserve the candidate's original factual meaning.

Return ONLY valid JSON:
{{
  "name": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "headline": "",
  "professional_summary": "",
  "skills": [],
  "experience": [{{"title":"", "organization":"", "details":[]}}],
  "projects": [{{"name":"", "details":[]}}],
  "education": [],
  "certifications": [],
  "ats_keywords": [],
  "changes_made": [],
  "not_added_recommendations": []
}}
'''

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        data = _extract_json(response.text)
        if not isinstance(data, dict):
            return {"error": "AI returned an invalid improved resume."}

        defaults = {
            "name": "", "email": "", "phone": "", "linkedin": "",
            "headline": "", "professional_summary": "", "skills": [],
            "experience": [], "projects": [], "education": [],
            "certifications": [], "ats_keywords": [], "changes_made": [],
            "not_added_recommendations": []
        }
        defaults.update(data)

        for key in ("skills", "experience", "projects", "education", "certifications",
                    "ats_keywords", "changes_made", "not_added_recommendations"):
            if not isinstance(defaults.get(key), list):
                defaults[key] = []

        return defaults

    except Exception as exc:
        return {"error": f"Failed to improve resume: {exc}"}
