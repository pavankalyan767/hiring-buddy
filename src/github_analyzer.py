"""
Medium-weight GitHub analyzer for HiringBuddy with Gemini LLM support.

Features:
- Parse owner/repo from a GitHub URL
- Fetch repo metadata (stars, forks, watchers, open issues)
- Fetch language breakdown (bytes -> %)
- Count commits in the last N days (default 90)
- Fetch contributors (top N)
- Check for README, tests folder, CI workflows
- Compute heuristics: activity_score, quality_score, bus_factor
- Optionally perform Gemini LLM review for code quality scoring
- Combine scores into final_github_score (0-100)
- Assign candidate level (Beginner / Intermediate / Pro)
"""

import os
import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from enhanced_github_code_reviewer import EnhancedGitHubCodeReviewer

GITHUB_API = "https://api.github.com"
REQUEST_TIMEOUT = 10  # seconds
RECENT_DAYS = 90  # lookback for activity


def _get_headers():
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "HiringBuddy-GitHubAnalyzer/1.0"
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def parse_github_url(url: str) -> Optional[Dict[str, str]]:
    if not url:
        return None
    if url.startswith("git@"):
        try:
            path = url.split(":", 1)[1]
            if path.endswith(".git"):
                path = path[:-4]
            owner, repo = path.split("/", 1)
            return {"owner": owner, "repo": repo}
        except Exception:
            return None
    m = re.search(r"github\.com/([^/]+)/([^/]+)/?", url)
    if m:
        owner = m.group(1)
        repo = m.group(2).replace(".git", "")
        return {"owner": owner, "repo": repo}
    return None


def github_api_get(path: str, params: dict = None) -> Optional[dict]:
    url = GITHUB_API + path
    try:
        r = requests.get(url, headers=_get_headers(), params=params or {}, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (202, 204):
            return {}
        return None
    except Exception:
        return None


def get_repo_basic(owner: str, repo: str) -> Optional[dict]:
    return github_api_get(f"/repos/{owner}/{repo}")


def get_languages(owner: str, repo: str) -> Dict[str, float]:
    data = github_api_get(f"/repos/{owner}/{repo}/languages")
    if not data:
        return {}
    total = sum(data.values()) or 1
    return {k: round((v / total) * 100, 1) for k, v in data.items()}


def get_recent_commit_count(owner: str, repo: str, days: int = RECENT_DAYS) -> int:
    since_dt = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
    per_page = 100
    page = 1
    total = 0
    while True:
        params = {"since": since_dt, "per_page": per_page, "page": page}
        res = github_api_get(f"/repos/{owner}/{repo}/commits", params=params)
        if res is None or isinstance(res, dict):
            break
        count = len(res)
        total += count
        if count < per_page or page >= 10:
            break
        page += 1
    return total


def get_contributors(owner: str, repo: str, top_n: int = 10) -> List[Dict[str, Any]]:
    contributors = github_api_get(f"/repos/{owner}/{repo}/contributors?per_page={top_n}")
    if not contributors:
        return []
    return [{"login": c.get("login"), "contributions": c.get("contributions", 0)} for c in contributors[:top_n]]


def check_file_presence(owner: str, repo: str, path: str) -> bool:
    res = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                       headers=_get_headers(), timeout=REQUEST_TIMEOUT)
    return res.status_code == 200


def detect_ci_workflows(owner: str, repo: str) -> bool:
    return check_file_presence(owner, repo, ".github/workflows")


def detect_tests(owner: str, repo: str) -> bool:
    common_paths = ["tests", "test", "spec", "unittest", "pytest.ini"]
    for p in common_paths:
        if check_file_presence(owner, repo, p):
            return True
    return False


def compute_activity_score(commit_count: int) -> float:
    if commit_count <= 0:
        return 0.0
    if commit_count <= 5:
        return round(2.0 + (commit_count - 1) * 0.2, 1)
    if commit_count <= 30:
        return round(4.0 + (commit_count - 6) * (3.0 / 24.0), 1)
    if commit_count <= 100:
        return round(7.0 + (commit_count - 31) * (2.0 / 69.0), 1)
    return 10.0


def compute_quality_score(repo_info: dict, has_readme: bool, has_tests: bool, has_ci: bool) -> float:
    base = 0.0
    if has_readme:
        base += 1.5
    if has_tests:
        base += 2.5
    if has_ci:
        base += 1.5

    stars = repo_info.get("stargazers_count", 0)
    forks = repo_info.get("forks_count", 0)
    watchers = repo_info.get("subscribers_count", repo_info.get("watchers_count", 0))

    popularity_score = min(3.0, (stars / 50.0) * 3.0)
    popularity_score += min(1.0, (forks / 20.0) * 1.0)
    popularity_score += min(0.5, (watchers / 50.0) * 0.5)

    quality = base + popularity_score
    return min(10.0, round(quality, 1))


def compute_bus_factor(contributors: List[Dict[str, Any]]) -> float:
    n = len(contributors)
    if n <= 1:
        return 1.0
    if n == 2:
        return 3.5
    if n == 3:
        return 5.0
    if n == 4:
        return 6.5
    return min(10.0, 7.0 + (n - 4) * 0.8)


def normalize_to_100(value: float, max_val: float = 10.0) -> float:
    return round((value / max_val) * 100, 1)


def assign_level(score_100: float) -> str:
    if score_100 >= 80:
        return "Pro"
    elif score_100 >= 60:
        return "Intermediate"
    else:
        return "Beginner"


# ---------------------------
# Enhanced GitHub Analyzer with Gemini integration
# ---------------------------
async def analyze_github_profile(
    github_url: str,
    use_gemini: bool = False,
    gemini_api_key: Optional[str] = None
) -> dict:
    parsed = parse_github_url(github_url)
    if not parsed:
        return {"error": "invalid_github_url"}

    owner = parsed["owner"]
    repo = parsed["repo"]

    repo_info = get_repo_basic(owner, repo)
    if not repo_info:
        return {"error": "repo_not_found_or_api_error", "owner": owner, "repo": repo}

    commit_count_recent = get_recent_commit_count(owner, repo, days=RECENT_DAYS)
    contributors = get_contributors(owner, repo, top_n=30)
    contributor_count = len(contributors)
    has_readme = check_file_presence(owner, repo, "README.md") or check_file_presence(owner, repo, "README")
    has_tests = detect_tests(owner, repo)
    has_ci = detect_ci_workflows(owner, repo)

    # Heuristic scores
    activity_score_10 = compute_activity_score(commit_count_recent)
    quality_score_10 = compute_quality_score(repo_info, has_readme, has_tests, has_ci)
    bus_factor_10 = compute_bus_factor(contributors)
    popularity_10 = min(10.0, (repo_info.get("stargazers_count", 0) / 50.0) * 10.0)

    final_10 = (
        (activity_score_10 * 0.40) +
        (quality_score_10 * 0.30) +
        (popularity_10 * 0.15) +
        (bus_factor_10 * 0.15)
    )
    final_score_100 = normalize_to_100(final_10, max_val=10.0)
    level = assign_level(final_score_100)

    strengths = []
    if has_readme:
        strengths.append("Has README")
    if has_tests:
        strengths.append("Has Tests")
    if has_ci:
        strengths.append("Has CI Workflows")
    if commit_count_recent > 50:
        strengths.append("Active commits")

    result = {
        "repo_full_name": f"{owner}/{repo}",
        "description": repo_info.get("description", ""),
        "stars": repo_info.get("stargazers_count", 0),
        "forks": repo_info.get("forks_count", 0),
        "open_issues": repo_info.get("open_issues_count", 0),
        "watchers": repo_info.get("subscribers_count", repo_info.get("watchers_count", 0)),
        "languages": get_languages(owner, repo),
        "commit_count_recent": commit_count_recent,
        "contributors": contributors,
        "contributor_count": contributor_count,
        "has_readme": bool(has_readme),
        "has_tests": bool(has_tests),
        "has_ci": bool(has_ci),
        "scores": {
            "activity_score_10": activity_score_10,
            "quality_score_10": quality_score_10,
            "popularity_score_10": round(popularity_10, 1),
            "bus_factor_10": round(bus_factor_10, 1),
            "final_score_100": final_score_100,
            "level": level,
            "strengths": strengths
        },
        "meta": {
            "created_at": repo_info.get("created_at"),
            "updated_at": repo_info.get("updated_at")
        }
    }

    # Optional Gemini LLM review
    if use_gemini:
        reviewer = EnhancedGitHubCodeReviewer()
        reviewer.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        await reviewer.initialize()

        gemini_result = await reviewer.validate_submission(
            requirements={"description": "General code quality assessment"},
            submission={"github_url": github_url}
        )

        gemini_score = gemini_result.get("details", {}).get("overall_score")
        if gemini_score is not None:
            # Hybrid scoring: combine heuristic and Gemini
            final_score_100 = round(0.5 * final_score_100 + 0.5 * gemini_score, 1)
            result["scores"]["final_score_100"] = final_score_100

        result["gemini_review"] = gemini_result

    return result
