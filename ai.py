from dotenv import load_dotenv
import os

load_dotenv()

print("Current Folder:", os.getcwd())
print("Gemini Key:", os.getenv("GEMINI_API_KEY"))


from dotenv import load_dotenv
load_dotenv()

from google import genai
import os
import json


def analyze_resume(resume_text, user_goal):

    if not os.getenv("GEMINI_API_KEY"):
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": "GEMINI_API_KEY is not set."
        }

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
You are a senior software engineer and hiring manager.

Analyze the following resume and provide feedback.

User Goal:
"{user_goal}"

Strict Rules:
- Extract only relevant information from the resume or goal
- Remove irrelevant tools
- Identify real gaps
- Generate roadmap only for missing skills
- Make outputs different based on goal

Return ONLY valid JSON:

{{
  "skills": [],
  "missing_skills": [],
  "roadmap": [],
  "interview_questions": []
}}

Resume:
{resume_text}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        content = response.text.strip()

        start = content.find("{")
        end = content.rfind("}") + 1

        json_text = content[start:end]

        return json.loads(json_text)

    except Exception as e:
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": f"Failed to analyze resume: {str(e)}"
        }