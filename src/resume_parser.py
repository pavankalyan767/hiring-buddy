"""
Simple resume parser for HiringBuddy.

- Extracts skills
- Returns a dictionary suitable for scoring
"""

import re
from typing import Dict, Any, List

# Optional: You can expand this skill list or fetch from a dynamic DB
COMMON_SKILLS = [
    "Python", "Django", "Flask", "FastAPI", "JavaScript", "React", "Node.js",
    "Golang", "C++", "Java", "SQL", "PostgreSQL", "MySQL", "MongoDB",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "Linux",
    "Git", "CI/CD", "Selenium", "PyTest"
]

def extract_skills(text: str) -> List[str]:
    skills_found = []
    for skill in COMMON_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            skills_found.append(skill)
    return skills_found


def parse_resume(resume_text: str) -> Dict[str, Any]:
    """
    Parse resume text and return structured data
    """
    skills = extract_skills(resume_text)
    return {
        "skills": skills,
        "raw_text": resume_text
    }


# Quick test
if __name__ == "__main__":
    sample_text = """
    Experienced backend developer with Python, Django, FastAPI, Docker, AWS, and PostgreSQL.
    """
    parsed = parse_resume(sample_text)
    print(parsed)
