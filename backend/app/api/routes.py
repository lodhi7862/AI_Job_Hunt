from datetime import datetime
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.guards import enforce_rate_limit, sanitize_text, validate_resume_filename
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.entities import (
    AILog,
    Application,
    CoverLetter,
    InterviewQuestion,
    Job,
    JobMatch,
    LinkedInProfile,
    Resume,
    User,
)
from app.schemas.schemas import ApplicationIn, JobIn, LinkedInIn, TokenOut, UserCreate, UserLogin
from app.services.ai_service import ai_service
from app.services.cache_service import cache_service
from app.services.resume_service import basic_ats_checks, extract_text

router = APIRouter()


@router.get("/ai/status")
def ai_status():
    provider = "deepseek" if settings.deepseek_api_key else "openai" if settings.openai_api_key else "none"
    return {"configured": provider != "none", "provider": provider, "model": settings.ai_model}


@router.post("/auth/register", response_model=TokenOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    enforce_rate_limit(f"register:{payload.email.lower()}")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/auth/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    enforce_rate_limit(f"login:{payload.email.lower()}")
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cache_key = f"dashboard:{current_user.id}"
    cached = cache_service.get_json(cache_key)
    if cached:
        return cached
    applications = db.query(Application).filter(Application.user_id == current_user.id).count()
    resume_versions = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    matches = (
        db.query(JobMatch)
        .filter(JobMatch.user_id == current_user.id)
        .order_by(desc(JobMatch.created_at))
        .limit(10)
        .all()
    )
    avg_score = round(sum(m.score for m in matches) / len(matches), 1) if matches else 0
    payload = {
        "profile_completion": 85 if current_user.full_name else 60,
        "applications": applications,
        "resume_versions": resume_versions,
        "match_score_history": [m.score for m in reversed(matches)],
        "upcoming_interviews": 0,
        "average_match_score": avg_score,
    }
    cache_service.set_json(cache_key, payload, ttl_seconds=90)
    return payload


@router.post("/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(f"resume_upload:{current_user.id}")
    safe_filename = sanitize_text(file.filename or "resume")
    validate_resume_filename(safe_filename)
    raw = await file.read()
    if len(raw) > settings.max_resume_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    try:
        text = extract_text(safe_filename, raw)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=422, detail="Resume file is malformed and could not be parsed")
    if not text:
        raise HTTPException(status_code=422, detail="Resume content is empty after parsing")
    ats_issues = basic_ats_checks(text)
    structured = ai_service.generate_structured(
        "Extract resume fields as JSON. Never invent facts.",
        f"Resume:\n{text}",
        fallback={"name": "", "email": "", "phone": "", "skills": [], "experience": [], "education": [], "certifications": []},
    )
    resume = Resume(
        user_id=current_user.id,
        original_filename=safe_filename,
        raw_text=text,
        structured_data=structured,
        ats_issues=ats_issues,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    cache_service.delete(f"dashboard:{current_user.id}")
    return {"resume_id": resume.id, "structured_data": structured, "ats_issues": ats_issues}


@router.post("/jobs/analyze")
def analyze_job(payload: JobIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"job_analyze:{current_user.id}")
    sanitized_title = sanitize_text(payload.title)
    sanitized_company = sanitize_text(payload.company)
    sanitized_description = sanitize_text(payload.description)
    analysis = ai_service.generate_structured(
        "Analyze JD and return required_skills, preferred_skills, seniority_level, industry, keywords, salary.",
        sanitized_description,
        fallback={
            "required_skills": [],
            "preferred_skills": [],
            "seniority_level": "unknown",
            "industry": "unknown",
            "keywords": [],
            "salary": "Not specified",
        },
    )
    job = Job(
        user_id=current_user.id,
        title=sanitized_title,
        company=sanitized_company,
        description=sanitized_description,
        analysis=analysis,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.id, "analysis": analysis}


@router.post("/match/{resume_id}/{job_id}")
def match_resume_job(resume_id: int, job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"match:{current_user.id}")
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not resume or not job:
        raise HTTPException(status_code=404, detail="Resume or job not found")
    match = ai_service.generate_structured(
        "Return JSON with score(0-100), missing_skills, strengths, weaknesses, reasoning.",
        f"Resume:{resume.raw_text}\n\nJob:{job.description}",
        fallback={"score": 65, "missing_skills": [], "strengths": [], "weaknesses": [], "reasoning": "Fallback score"},
    )
    job_match = JobMatch(
        user_id=current_user.id,
        resume_id=resume.id,
        job_id=job.id,
        score=max(0.0, min(float(match.get("score", 0)), 100.0)),
        missing_skills=match.get("missing_skills", []),
        strengths=match.get("strengths", []),
        weaknesses=match.get("weaknesses", []),
        reasoning=match.get("reasoning", "No reasoning provided."),
    )
    db.add(job_match)
    db.commit()
    db.refresh(job_match)
    cache_service.delete(f"dashboard:{current_user.id}")
    return {
        "score": job_match.score,
        "missing_skills": job_match.missing_skills,
        "strengths": job_match.strengths,
        "weaknesses": job_match.weaknesses,
        "reasoning": job_match.reasoning,
    }


@router.post("/cover-letter/{job_id}/{resume_id}")
def generate_cover_letter(job_id: int, resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"cover_letter:{current_user.id}")
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not resume or not job:
        raise HTTPException(status_code=404, detail="Resume or job not found")
    result = ai_service.generate_structured(
        "Generate JSON with professional cover_letter. Never invent user experience.",
        f"Resume:{resume.raw_text}\nJob:{job.description}",
        fallback={"cover_letter": "I am excited to apply for this role and bring relevant proven experience."},
    )
    letter_content = sanitize_text(result.get("cover_letter", "")) or "Unable to generate cover letter."
    letter = CoverLetter(user_id=current_user.id, job_id=job.id, content=letter_content)
    db.add(letter)
    db.commit()
    db.refresh(letter)
    return {"cover_letter": letter.content}


@router.post("/application-email/{job_id}/{resume_id}")
def generate_application_email(job_id: int, resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"application_email:{current_user.id}")
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not resume or not job:
        raise HTTPException(status_code=404, detail="Resume or job not found")

    found_email = ""
    email_matches = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", job.description)
    if email_matches:
        found_email = email_matches[0]

    result = ai_service.generate_structured(
        "Return JSON with subject and body for a short professional job application email. Keep body under 120 words. Never invent fake experience.",
        f"Job title: {job.title}\nCompany: {job.company}\nJob description: {job.description}\nResume: {resume.raw_text}",
        fallback={
            "subject": f"Application for {job.title} - {resume.structured_data.get('name', 'Candidate')}",
            "body": "Hello Hiring Team,\n\nI am applying for this role and have attached my CV for your review. I believe my experience aligns well with your requirements.\n\nThank you for your time.\nBest regards,",
        },
    )
    subject = sanitize_text(result.get("subject", "")) or f"Application for {job.title}"
    body = sanitize_text(result.get("body", "")) or "Hello Hiring Team, I have attached my CV and would appreciate your consideration."
    return {"email": found_email, "subject": subject, "body": body}


@router.post("/resume-optimize/{job_id}/{resume_id}")
def optimize_resume(job_id: int, resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"resume_optimize:{current_user.id}")
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not resume or not job:
        raise HTTPException(status_code=404, detail="Resume or job not found")
    result = ai_service.generate_structured(
        "Generate JSON: optimized_resume, improved_bullets(array), summary, confidence(0-1). Never invent fake experience.",
        f"Original resume:\n{resume.raw_text}\n\nJob description:\n{job.description}",
        fallback={
            "optimized_resume": resume.raw_text,
            "improved_bullets": [],
            "summary": "AI optimization unavailable; showing original resume.",
            "confidence": 0.4,
        },
    )
    return {
        "optimized_resume": result.get("optimized_resume", resume.raw_text),
        "improved_bullets": result.get("improved_bullets", []),
        "summary": result.get("summary", ""),
        "confidence": float(result.get("confidence", 0.4)),
    }


@router.post("/interview/{job_id}")
def generate_interview_questions(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"interview:{current_user.id}")
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = ai_service.generate_structured(
        "Create JSON with questions:[{kind,question,ideal_answer,tip}]",
        job.description,
        fallback={"questions": [{"kind": "behavioral", "question": "Tell me about yourself", "ideal_answer": "Concise impact story", "tip": "Use STAR"}]},
    )
    created_questions = []
    for q in result.get("questions", []):
        question = sanitize_text(str(q.get("question", "")))
        answer = sanitize_text(str(q.get("ideal_answer", "")))
        kind = sanitize_text(str(q.get("kind", "behavioral"))) or "behavioral"
        if not question or not answer:
            continue
        db.add(InterviewQuestion(user_id=current_user.id, job_id=job.id, question=question, answer=answer, kind=kind))
        created_questions.append({"kind": kind, "question": question, "ideal_answer": answer})
    db.commit()
    return {"questions": created_questions}


@router.post("/career-suggestions/{job_id}/{resume_id}")
def generate_career_suggestions(job_id: int, resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"career_suggestions:{current_user.id}")
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not resume or not job:
        raise HTTPException(status_code=404, detail="Resume or job not found")
    result = ai_service.generate_structured(
        "Return JSON with suggestions(array), upskill_plan(array), networking_tips(array), confidence(0-1).",
        f"Resume:\n{resume.raw_text}\n\nJob:\n{job.description}",
        fallback={
            "suggestions": ["Build measurable project outcomes into resume bullets."],
            "upskill_plan": ["Strengthen one role-specific technical skill this month."],
            "networking_tips": ["Reach out to 3 professionals in target domain per week."],
            "confidence": 0.5,
        },
    )
    return {
        "suggestions": result.get("suggestions", []),
        "upskill_plan": result.get("upskill_plan", []),
        "networking_tips": result.get("networking_tips", []),
        "confidence": float(result.get("confidence", 0.5)),
    }


@router.post("/applications")
def create_application(payload: ApplicationIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"application_create:{current_user.id}")
    if payload.date_applied:
        try:
            datetime.strptime(payload.date_applied, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=422, detail="date_applied must be in YYYY-MM-DD format")
    application = Application(
        user_id=current_user.id,
        company=sanitize_text(payload.company),
        role=sanitize_text(payload.role),
        date_applied=payload.date_applied,
        status=payload.status.value,
        notes=sanitize_text(payload.notes),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    cache_service.delete(f"dashboard:{current_user.id}")
    return application


@router.get("/applications")
def list_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(desc(Application.id))
        .limit(200)
        .all()
    )


@router.post("/linkedin/analyze")
def analyze_linkedin(payload: LinkedInIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"linkedin_analyze:{current_user.id}")
    profile_text = sanitize_text(payload.profile_text)
    profile_url = str(payload.profile_url or "")
    profile_url = sanitize_text(profile_url)
    if not profile_text and not profile_url:
        raise HTTPException(status_code=422, detail="Provide profile_url or profile_text")
    analysis = ai_service.generate_structured(
        "Evaluate LinkedIn profile and return headline_quality, summary_quality, keyword_optimization, completeness, suggestions.",
        profile_text or profile_url,
        fallback={
            "headline_quality": 70,
            "summary_quality": 70,
            "keyword_optimization": 65,
            "completeness": 68,
            "suggestions": ["Add measurable achievements to About section."],
        },
    )
    profile = LinkedInProfile(user_id=current_user.id, profile_url=profile_url, profile_text=profile_text, analysis=analysis)
    db.add(profile)
    db.commit()
    return analysis


@router.get("/admin/overview")
def admin_overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return {
        "users": db.query(User).count(),
        "api_usage_logs": db.query(AILog).count(),
        "failed_jobs": 0,
    }
