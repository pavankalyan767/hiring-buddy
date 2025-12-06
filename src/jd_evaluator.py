"""
Medium-weight Job Description (JD) evaluator.

Purpose:
- Parse JD text
- Extract required skills, roles, and experience hints
- Compare with candidate profile (from resume_parser or GitHub analyzer)
- Return structured data and match score
"""

import re
from typing import List, Dict, Any

# Predefined skills and roles (extendable)
PROGRAMMING_LANGUAGES = [
    "python", "java", "javascript", "typescript", "go", "golang", "c++", "c", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r"
]

FRAMEWORKS = [
    "django", "flask", "fastapi", "react", "reactjs", "vue", "angular", "spring", "node.js",
    "express", "tensorflow", "pytorch", "scikit-learn", "keras"
]

TOOLS = [
    "docker", "kubernetes", "git", "ci/cd", "jenkins", "github actions", "gitlab ci",
    "aws", "gcp", "azure", "postgresql", "mongodb", "mysql", "redis"
]

SOFT_SKILLS = [
    "communication", "teamwork", "leadership", "problem solving", "collaboration",
    "mentoring", "ownership", "critical thinking"
]

ROLES = [
    "backend engineer", "frontend engineer", "fullstack engineer", "data scientist",
    "ml engineer", "devops engineer", "software engineer", "mobile engineer", "qa engineer"
]


def normalize_text(text: str) -> str:
    """Lowercase, remove punctuation for matching"""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s/+#.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_keywords(text: str, keyword_list: List[str]) -> List[str]:
    """Return list of keywords from keyword_list present in text"""
    text_norm = normalize_text(text)
    found = []
    for kw in keyword_list:
        kw_norm = normalize_text(kw)
        if re.search(rf"\b{re.escape(kw_norm)}\b", text_norm):
            found.append(kw)
    return found


def extract_jd_skills(jd_text: str) -> Dict[str, List[str]]:
    """Extract skills, frameworks, tools, soft skills, and roles from JD text"""
    skills = extract_keywords(jd_text, PROGRAMMING_LANGUAGES)
    frameworks = extract_keywords(jd_text, FRAMEWORKS)
    tools = extract_keywords(jd_text, TOOLS)
    soft_skills = extract_keywords(jd_text, SOFT_SKILLS)
    roles = extract_keywords(jd_text, ROLES)

    return {
        "skills": skills,
        "frameworks": frameworks,
        "tools": tools,
        "soft_skills": soft_skills,
        "roles": roles
    }


def jd_match_score(jd_keywords: Dict[str, List[str]], candidate_profile: Dict[str, Any]) -> float:
    """
    Compare extracted JD keywords against candidate profile and return 0-100 score.

    Candidate profile is expected in the format returned by resume_parser:
      - languages: dict
      - skills, frameworks, tools, soft_skills, roles: lists
    """
    total_weight = 0
    score = 0.0

    weights = {
        "skills": 0.35,
        "frameworks": 0.25,
        "tools": 0.15,
        "soft_skills": 0.10,
        "roles": 0.15
    }

    # Skills / languages
    jd_skills = jd_keywords.get("skills", [])
    candidate_languages = [k.lower() for k in candidate_profile.get("languages", {}).keys()]
    skill_matches = set([s.lower() for s in jd_skills]) & set(candidate_languages)
    if jd_skills:
        score += (len(skill_matches) / len(jd_skills)) * weights["skills"] * 100
        total_weight += weights["skills"]

    # Frameworks
    jd_frameworks = jd_keywords.get("frameworks", [])
    candidate_frameworks = [f.lower() for f in candidate_profile.get("frameworks", [])]
    framework_matches = set([f.lower() for f in jd_frameworks]) & set(candidate_frameworks)
    if jd_frameworks:
        score += (len(framework_matches) / len(jd_frameworks)) * weights["frameworks"] * 100
        total_weight += weights["frameworks"]

    # Tools
    jd_tools = jd_keywords.get("tools", [])
    candidate_tools = [t.lower() for t in candidate_profile.get("tools", [])]
    tools_matches = set([t.lower() for t in jd_tools]) & set(candidate_tools)
    if jd_tools:
        score += (len(tools_matches) / len(jd_tools)) * weights["tools"] * 100
        total_weight += weights["tools"]

    # Soft skills
    jd_soft = jd_keywords.get("soft_skills", [])
    candidate_soft = [s.lower() for s in candidate_profile.get("soft_skills", [])]
    soft_matches = set([s.lower() for s in jd_soft]) & set(candidate_soft)
    if jd_soft:
        score += (len(soft_matches) / len(jd_soft)) * weights["soft_skills"] * 100
        total_weight += weights["soft_skills"]

    # Roles
    jd_roles = jd_keywords.get("roles", [])
    candidate_roles = [r.lower() for r in candidate_profile.get("roles", [])]
    role_matches = set([r.lower() for r in jd_roles]) & set(candidate_roles)
    if jd_roles:
        score += (len(role_matches) / len(jd_roles)) * weights["roles"] * 100
        total_weight += weights["roles"]

    # Normalize
    final_score = round(score / total_weight, 1) if total_weight > 0 else 0.0
    return final_score


def analyze_jd(jd_text: str, candidate_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main JD analyzer entrypoint.

    If candidate_profile is provided (from resume_parser or GitHub analyzer),
    the JD match score will be computed.
    """
    keywords = extract_jd_skills(jd_text)
    result = {
        "jd_text": jd_text,
        "extracted_keywords": keywords,
        "match_score": None
    }

    if candidate_profile:
        # candidate_profile is expected in the resume_parser format
        result["match_score"] = jd_match_score(keywords, candidate_profile)

    return result


# Quick test
if __name__ == "__main__":
    jd_example = """
    We are looking for a Backend Engineer with strong Python, Django, and FastAPI experience.
    Familiarity with Docker, Kubernetes, and AWS is required.
    Strong communication, teamwork, and problem-solving skills are a must.
    """
    candidate_example = {
        "languages": {"Python": 80, "Go": 20},
        "skills": ["Python", "Go"],
        "frameworks": ["Django", "Flask"],
        "tools": ["Docker", "AWS", "Git"],
        "soft_skills": ["communication", "teamwork"],
        "roles": ["Backend Engineer"]
    }
    analysis = analyze_jd(jd_example, candidate_example)
    print(analysis)
