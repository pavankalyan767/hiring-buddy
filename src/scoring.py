"""
src/scoring.py

Combine resume, GitHub, and JD evaluation to compute a final candidate score.
"""

from typing import Dict, Any

def compute_final_score(resume_data: Dict[str, Any], github_data: Dict[str, Any], jd_score: float = 0) -> float:
    """
    Compute final hiring score combining resume, GitHub, and JD fit.

    Weights (adjustable):
    - Resume skills: 25%
    - GitHub analysis: 50%
    - JD fit score: 25%
    """
    score = 0.0
    total_weight = 0.0

    # -------------------------
    # 1. Resume skills
    # -------------------------
    resume_skills = resume_data.get("skills", [])
    if resume_skills:
        # Simple heuristic: more skills = higher score
        resume_score = min(len(resume_skills) / 20, 1.0) * 100  # Cap at 20 skills
        score += resume_score * 0.25
        total_weight += 0.25

    # -------------------------
    # 2. GitHub analysis
    # -------------------------
    if github_data and "overall_score" in github_data.get("details", {}):
        github_score = github_data["details"]["overall_score"] * 10  # Scale 0-10 to 0-100
        score += github_score * 0.50
        total_weight += 0.50

    # -------------------------
    # 3. JD fit score
    # -------------------------
    if jd_score is not None:
        score += jd_score * 0.25
        total_weight += 0.25

    # -------------------------
    # Normalize
    # -------------------------
    if total_weight > 0:
        final_score = round(score / total_weight, 1)
    else:
        final_score = 0.0

    return final_score


def generate_candidate_summary(resume_data: Dict[str, Any], github_data: Dict[str, Any], jd_evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a full candidate summary with all details and final hiring score
    """
    jd_score = jd_evaluation.get("match_score", 0)

    final_score = compute_final_score(
        resume_data=resume_data,
        github_data=github_data,
        jd_score=jd_score
    )

    summary = {
        "resume_data": resume_data,
        "github_analysis": github_data,
        "jd_evaluation": jd_evaluation,
        "final_hiring_score": final_score
    }

    return summary


# Quick test
if __name__ == "__main__":
    resume = {
        "skills": ["Python", "Django", "FastAPI", "Docker", "AWS"],
        "raw_text": "Sample resume text..."
    }

    github = {
        "details": {
            "overall_score": 8.5,
            "strengths": ["Clean code", "Good architecture"],
            "critical_issues": [],
            "file_analysis": []
        }
    }

    jd_eval = {
        "jd_text": "Looking for Python backend engineer with Django and FastAPI. Docker and AWS required.",
        "extracted_keywords": {},
        "match_score": 85
    }

    summary = generate_candidate_summary(resume, github, jd_eval)
    print(summary)
