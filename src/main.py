import os
import requests
from apify import Actor
from resume_parser import parse_resume
from github_analyzer import analyze_github_profile
from jd_evaluator import evaluate_jd_fit
from scoring import generate_candidate_summary
import tempfile
import asyncio  # Required for awaiting async functions


async def main():
    async with Actor:
        # -------------------------
        # Get input passed to the Actor
        # -------------------------
        actor_input = await Actor.get_input() or {}
        resume_file_info = actor_input.get("resume_file")  # uploaded file info
        job_description = actor_input.get("job_description", "")
        gemini_api_key = actor_input.get("geminiApiKey", "")

        if not resume_file_info:
            await Actor.fail("resume_file is required!")

        # -------------------------
        # Step 1: Download uploaded resume file
        # -------------------------
        resume_path = os.path.join(tempfile.gettempdir(), "resume.pdf")
        resume_url = resume_file_info.get("url")
        r = requests.get(resume_url)
        with open(resume_path, "wb") as f:
            f.write(r.content)

        # -------------------------
        # Step 2: Parse resume
        # -------------------------
        resume_data = parse_resume(resume_path)

        # -------------------------
        # Step 3: GitHub Analysis (async)
        # -------------------------
        github_url = resume_data.get("github_url")  # extract from resume
        github_analysis = None
        if github_url:
            github_analysis = await analyze_github_profile(
                github_url,
                use_gemini=bool(gemini_api_key),
                gemini_api_key=gemini_api_key
            )

        # -------------------------
        # Step 4: JD Evaluation
        # -------------------------
        jd_evaluation = evaluate_jd_fit(
            resume_text=resume_data.get("raw_text", ""),
            job_description=job_description,
            gemini_api_key=gemini_api_key
        )

        # -------------------------
        # Step 5: Compute final score
        # -------------------------
        candidate_summary = generate_candidate_summary(
            resume_data=resume_data,
            github_data=github_analysis,
            jd_evaluation=jd_evaluation
        )

        # -------------------------
        # Step 6: Output
        # -------------------------
        await Actor.set_output(candidate_summary)


if __name__ == "__main__":
    asyncio.run(main())
