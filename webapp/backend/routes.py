import datetime
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password, is_admin
from database import get_db
from models import QuizAnswer, QuizSession, QuizSessionQuestion, User
import quiz as quiz_service

router = APIRouter()

PDF_PATH = os.environ.get("PDF_PATH", "/data/pdfs")
INVITE_CODE = os.environ.get("INVITE_CODE", "grile2025")


# ---------- Pydantic schemas ----------

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    invite_code: str


class LoginRequest(BaseModel):
    username: str
    password: str


class GenerateQuizRequest(BaseModel):
    sources: Optional[list[str]] = None
    years: Optional[list[int]] = None
    topics: Optional[list[str]] = None
    cs_count: int = 0
    cg_count: int = 0


class ReviewQuizRequest(BaseModel):
    count: int = 20
    topics: Optional[list[str]] = None


class AnswerRequest(BaseModel):
    question_id: str
    answer: str
    time_spent_ms: Optional[int] = None


class AvailableCountsRequest(BaseModel):
    sources: Optional[list[str]] = None
    years: Optional[list[int]] = None
    topics: Optional[list[str]] = None


# ---------- Auth endpoints ----------

@router.post("/api/auth/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if body.invite_code != INVITE_CODE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cod de invitație invalid")

    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username}}


@router.post("/api/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username}}


@router.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat(),
        "is_admin": is_admin(current_user),
    }


# ---------- Data endpoints ----------

@router.get("/api/sources")
def list_sources():
    return quiz_service.get_sources()


@router.get("/api/topics")
def list_topics():
    return quiz_service.get_topics()


@router.post("/api/quiz/available-counts")
def available_counts(body: AvailableCountsRequest):
    return quiz_service.get_available_counts(body.sources, body.years, body.topics)


# ---------- Quiz endpoints ----------

@router.post("/api/quiz/generate")
def generate_quiz(body: GenerateQuizRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    questions = quiz_service.generate_quiz(
        sources=body.sources,
        years=body.years,
        topics=body.topics,
        cs_count=body.cs_count,
        cg_count=body.cg_count,
    )

    if not questions:
        raise HTTPException(status_code=400, detail="No questions match the given filters")

    session = QuizSession(
        user_id=current_user.id,
        session_type="practice",
        filters=json.dumps({
            "sources": body.sources,
            "years": body.years,
            "topics": body.topics,
            "cs_count": body.cs_count,
            "cg_count": body.cg_count,
        }),
    )
    db.add(session)
    db.flush()

    for i, q in enumerate(questions):
        sq = QuizSessionQuestion(session_id=session.id, question_id=q["id"], position=i + 1)
        db.add(sq)

    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "question_count": len(questions)}


@router.post("/api/quiz/review")
def generate_review(body: ReviewQuizRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    questions = quiz_service.generate_review_quiz(
        user_id=current_user.id,
        count=body.count,
        topics=body.topics,
        db=db,
    )

    if not questions:
        raise HTTPException(status_code=400, detail="No review questions available (answer some quizzes first)")

    session = QuizSession(
        user_id=current_user.id,
        session_type="review",
        filters=json.dumps({"count": body.count, "topics": body.topics}),
    )
    db.add(session)
    db.flush()

    for i, q in enumerate(questions):
        sq = QuizSessionQuestion(session_id=session.id, question_id=q["id"], position=i + 1)
        db.add(sq)

    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "question_count": len(questions)}


@router.get("/api/quiz/{session_id}")
def get_quiz(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    session_questions = (
        db.query(QuizSessionQuestion)
        .filter(QuizSessionQuestion.session_id == session_id)
        .order_by(QuizSessionQuestion.position)
        .all()
    )

    questions = []
    for sq in session_questions:
        q = quiz_service.get_question(sq.question_id)
        if q is None:
            continue

        # Check if already answered
        existing_answer = db.query(QuizAnswer).filter(QuizAnswer.session_question_id == sq.id).first()

        questions.append({
            "session_question_id": sq.id,
            "question_id": sq.question_id,
            "position": sq.position,
            "type": q.get("type"),
            "text": q.get("text"),
            "choices": q.get("choices"),
            "topic": q.get("topic"),
            "year": q.get("year"),
            "source_file": q.get("source_file"),
            "page_ref": q.get("page_ref"),
            "answered": existing_answer is not None,
            # Do NOT include correct_answer
        })

    return {
        "session_id": session.id,
        "session_type": session.session_type,
        "started_at": session.started_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "question_count": len(questions),
        "questions": questions,
    }


@router.post("/api/quiz/{session_id}/answer")
def submit_answer(
    session_id: int,
    body: AnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.completed_at is not None:
        raise HTTPException(status_code=400, detail="Session already completed")

    # Find the session question
    sq = (
        db.query(QuizSessionQuestion)
        .filter(
            QuizSessionQuestion.session_id == session_id,
            QuizSessionQuestion.question_id == body.question_id,
        )
        .first()
    )
    if not sq:
        raise HTTPException(status_code=404, detail="Question not in this session")

    # Look up question data
    q = quiz_service.get_question(body.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found in data")

    # Prevent duplicate answers
    existing_answer = db.query(QuizAnswer).filter(QuizAnswer.session_question_id == sq.id).first()
    if existing_answer:
        raise HTTPException(status_code=400, detail="Already answered")

    # Create answer
    answer = QuizAnswer(
        session_question_id=sq.id,
        user_answer=body.answer,
        time_spent_ms=body.time_spent_ms,
    )
    db.add(answer)
    db.commit()

    is_correct = q.get("correct_answer") == body.answer

    result = {
        "is_correct": is_correct,
        "correct_answer": q.get("correct_answer"),
    }

    # For complement_grupat, also return correct_statements
    if q.get("type") == "complement_grupat":
        result["correct_statements"] = q.get("correct_statements")

    return result


@router.post("/api/quiz/{session_id}/complete")
def complete_quiz(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    already_completed = session.completed_at is not None
    if not already_completed:
        session.completed_at = datetime.datetime.utcnow()
        db.commit()

    # Build full results
    session_questions = (
        db.query(QuizSessionQuestion)
        .filter(QuizSessionQuestion.session_id == session_id)
        .order_by(QuizSessionQuestion.position)
        .all()
    )

    results = []
    correct_count = 0
    total_answered = 0

    for sq in session_questions:
        q = quiz_service.get_question(sq.question_id)
        # Get the latest answer for this question
        latest_answer = (
            db.query(QuizAnswer)
            .filter(QuizAnswer.session_question_id == sq.id)
            .order_by(QuizAnswer.answered_at.desc())
            .first()
        )

        entry = {
            "question_id": sq.question_id,
            "position": sq.position,
            "text": q.get("text") if q else None,
            "type": q.get("type") if q else None,
            "choices": q.get("choices") if q else None,
            "correct_answer": q.get("correct_answer") if q else None,
            "correct_statements": q.get("correct_statements") if q else None,
            "user_answer": latest_answer.user_answer if latest_answer else None,
            "is_correct": None,
            "time_spent_ms": latest_answer.time_spent_ms if latest_answer else None,
        }

        if latest_answer and q:
            is_correct = q.get("correct_answer") == latest_answer.user_answer
            entry["is_correct"] = is_correct
            total_answered += 1
            if is_correct:
                correct_count += 1

        results.append(entry)

    return {
        "session_id": session.id,
        "completed_at": session.completed_at.isoformat(),
        "total_questions": len(session_questions),
        "total_answered": total_answered,
        "correct_count": correct_count,
        "accuracy": correct_count / total_answered if total_answered > 0 else 0,
        "results": results,
    }


# ---------- Stats endpoints ----------

@router.get("/api/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Fetch all answers for user
    rows = (
        db.query(QuizSessionQuestion.question_id, QuizAnswer.user_answer)
        .join(QuizAnswer, QuizAnswer.session_question_id == QuizSessionQuestion.id)
        .join(QuizSession, QuizSession.id == QuizSessionQuestion.session_id)
        .filter(QuizSession.user_id == current_user.id)
        .all()
    )

    total = 0
    correct = 0
    by_topic: dict[str, dict] = {}
    by_year: dict[int, dict] = {}

    for question_id, user_answer in rows:
        q = quiz_service.get_question(question_id)
        if not q:
            continue

        total += 1
        is_correct = q.get("correct_answer") == user_answer
        if is_correct:
            correct += 1

        topic = q.get("topic", "unknown")
        if topic not in by_topic:
            by_topic[topic] = {"total": 0, "correct": 0}
        by_topic[topic]["total"] += 1
        if is_correct:
            by_topic[topic]["correct"] += 1

        year = q.get("year")
        if year is not None:
            if year not in by_year:
                by_year[year] = {"total": 0, "correct": 0}
            by_year[year]["total"] += 1
            if is_correct:
                by_year[year]["correct"] += 1

    # Compute study streak: consecutive days with at least one completed session
    import datetime as _dt
    completed_dates = (
        db.query(func.date(QuizSession.completed_at))
        .filter(QuizSession.user_id == current_user.id, QuizSession.completed_at.isnot(None))
        .distinct()
        .order_by(func.date(QuizSession.completed_at).desc())
        .all()
    )
    study_streak = 0
    today = _dt.date.today()
    check_date = today
    for (d,) in completed_dates:
        if isinstance(d, str):
            d = _dt.date.fromisoformat(d)
        if d == check_date:
            study_streak += 1
            check_date -= _dt.timedelta(days=1)
        elif d < check_date:
            break

    # Compute accuracy trend: this month vs last month
    now = _dt.datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_of_last_month = (first_of_month - _dt.timedelta(days=1)).replace(day=1)

    def _month_accuracy(start: _dt.datetime, end: _dt.datetime) -> float | None:
        month_rows = (
            db.query(QuizSessionQuestion.question_id, QuizAnswer.user_answer)
            .join(QuizAnswer, QuizAnswer.session_question_id == QuizSessionQuestion.id)
            .join(QuizSession, QuizSession.id == QuizSessionQuestion.session_id)
            .filter(
                QuizSession.user_id == current_user.id,
                QuizAnswer.answered_at >= start,
                QuizAnswer.answered_at < end,
            )
            .all()
        )
        if not month_rows:
            return None
        m_correct = sum(
            1 for qid, ua in month_rows
            if (qq := quiz_service.get_question(qid)) and qq.get("correct_answer") == ua
        )
        return m_correct / len(month_rows)

    this_month_acc = _month_accuracy(first_of_month, now)
    last_month_acc = _month_accuracy(first_of_last_month, first_of_month)
    accuracy_trend = 0.0
    if this_month_acc is not None and last_month_acc is not None and last_month_acc > 0:
        accuracy_trend = this_month_acc - last_month_acc

    return {
        "total_answered": total,
        "total_correct": correct,
        "accuracy": correct / total if total > 0 else 0,
        "by_topic": {
            k: {**v, "accuracy": v["correct"] / v["total"] if v["total"] > 0 else 0}
            for k, v in sorted(by_topic.items())
        },
        "by_year": {
            k: {**v, "accuracy": v["correct"] / v["total"] if v["total"] > 0 else 0}
            for k, v in sorted(by_year.items())
        },
        "study_streak": study_streak,
        "accuracy_trend": accuracy_trend,
    }


@router.get("/api/stats/history")
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(QuizSession)
        .filter(QuizSession.user_id == current_user.id)
        .order_by(QuizSession.started_at.desc())
        .limit(20)
        .all()
    )

    result = []
    for session in sessions:
        session_questions = (
            db.query(QuizSessionQuestion)
            .filter(QuizSessionQuestion.session_id == session.id)
            .all()
        )

        answered = 0
        correct = 0
        for sq in session_questions:
            latest = (
                db.query(QuizAnswer)
                .filter(QuizAnswer.session_question_id == sq.id)
                .order_by(QuizAnswer.answered_at.desc())
                .first()
            )
            if latest:
                answered += 1
                q = quiz_service.get_question(sq.question_id)
                if q and q.get("correct_answer") == latest.user_answer:
                    correct += 1

        result.append({
            "session_id": session.id,
            "session_type": session.session_type,
            "started_at": session.started_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "total_questions": len(session_questions),
            "answered": answered,
            "correct": correct,
            "accuracy": correct / answered if answered > 0 else 0,
        })

    return result


@router.get("/api/stats/weakest")
def get_weakest(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(QuizSessionQuestion.question_id, QuizAnswer.user_answer)
        .join(QuizAnswer, QuizAnswer.session_question_id == QuizSessionQuestion.id)
        .join(QuizSession, QuizSession.id == QuizSessionQuestion.session_id)
        .filter(QuizSession.user_id == current_user.id)
        .all()
    )

    stats: dict[str, dict] = {}
    for question_id, user_answer in rows:
        if question_id not in stats:
            stats[question_id] = {"total": 0, "wrong": 0}
        stats[question_id]["total"] += 1
        q = quiz_service.get_question(question_id)
        if q and q.get("correct_answer") != user_answer:
            stats[question_id]["wrong"] += 1

    ranked = sorted(
        stats.items(),
        key=lambda x: (x[1]["wrong"] / max(x[1]["total"], 1), x[1]["wrong"]),
        reverse=True,
    )[:20]

    result = []
    for question_id, s in ranked:
        q = quiz_service.get_question(question_id)
        if q:
            result.append({
                "question_id": question_id,
                "text": q.get("text", "")[:200],
                "topic": q.get("topic"),
                "year": q.get("year"),
                "type": q.get("type"),
                "total_attempts": s["total"],
                "wrong_count": s["wrong"],
                "error_rate": s["wrong"] / s["total"] if s["total"] > 0 else 0,
            })

    return result


# ---------- PDF endpoint ----------

@router.get("/api/pdf/{filename}")
def serve_pdf(filename: str):
    # Security: only allow .pdf files, no path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are served")

    path = Path(PDF_PATH) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(path, media_type="application/pdf", filename=filename)
