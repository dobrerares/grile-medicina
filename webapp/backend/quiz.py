import json
import os
import random
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from models import QuizAnswer, QuizSession, QuizSessionQuestion

DATA_PATH = os.environ.get("DATA_PATH", "/data/grile.json")

# In-memory data store
_data: dict = {}
_by_id: dict[str, dict] = {}
_by_year: dict[int, list[dict]] = {}
_by_topic: dict[str, list[dict]] = {}
_by_type: dict[str, list[dict]] = {}
_sources: list[dict] = []
_file_mtime: float = 0.0


def load_data() -> None:
    """Load grile.json and build in-memory indexes. Checks mtime for hot-reload."""
    global _data, _by_id, _by_year, _by_topic, _by_type, _sources, _file_mtime

    path = Path(DATA_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_PATH}")

    current_mtime = path.stat().st_mtime
    if current_mtime == _file_mtime and _data:
        return  # no changes

    with open(path, "r", encoding="utf-8") as f:
        _data = json.load(f)

    _by_id = {}
    _by_year = {}
    _by_topic = {}
    _by_type = {}
    _sources = []

    for source in _data.get("sources", []):
        year = source.get("year")
        file_name = source.get("file", "")
        source_info = {
            "file": file_name,
            "year": year,
            "cs_count": 0,
            "cg_count": 0,
            "total": 0,
        }

        for test in source.get("tests", []):
            topic = test.get("topic", "unknown")
            for question in test.get("questions", []):
                qid = question["id"]
                q_type = question.get("type", "complement_simplu")

                enriched = {
                    **question,
                    "year": year,
                    "source_file": file_name,
                    "topic": topic,
                    "test_title": test.get("title", ""),
                    "test_id": test.get("test_id", ""),
                }

                _by_id[qid] = enriched
                _by_year.setdefault(year, []).append(enriched)
                _by_topic.setdefault(topic, []).append(enriched)
                _by_type.setdefault(q_type, []).append(enriched)

                if q_type == "complement_simplu":
                    source_info["cs_count"] += 1
                else:
                    source_info["cg_count"] += 1
                source_info["total"] += 1

        _sources.append(source_info)

    _file_mtime = current_mtime


def get_sources() -> list[dict]:
    """List sources with year, file, and question counts per type."""
    load_data()
    return _sources


def get_topics() -> list[dict]:
    """List topics with question counts."""
    load_data()
    result = []
    for topic, questions in sorted(_by_topic.items()):
        answerable = [q for q in questions if q.get("correct_answer") is not None]
        result.append({
            "topic": topic,
            "total": len(questions),
            "answerable": len(answerable),
            "cs_count": sum(1 for q in answerable if q.get("type") == "complement_simplu"),
            "cg_count": sum(1 for q in answerable if q.get("type") == "complement_grupat"),
        })
    return result


def _filter_pool(
    sources: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    topics: Optional[list[str]] = None,
) -> list[dict]:
    """Filter the question pool based on criteria. Excludes null answers."""
    load_data()
    pool = list(_by_id.values())

    if sources:
        pool = [q for q in pool if q["source_file"] in sources]
    if years:
        pool = [q for q in pool if q["year"] in years]
    if topics:
        pool = [q for q in pool if q["topic"] in topics]

    # Exclude questions without correct answers
    pool = [q for q in pool if q.get("correct_answer") is not None]
    return pool


def get_available_counts(
    sources: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    topics: Optional[list[str]] = None,
) -> dict:
    """Returns how many CS and CG questions match the filters."""
    pool = _filter_pool(sources, years, topics)
    cs = sum(1 for q in pool if q.get("type") == "complement_simplu")
    cg = sum(1 for q in pool if q.get("type") == "complement_grupat")
    return {"cs_available": cs, "cg_available": cg, "total": cs + cg}


def generate_quiz(
    sources: Optional[list[str]] = None,
    years: Optional[list[int]] = None,
    topics: Optional[list[str]] = None,
    cs_count: int = 0,
    cg_count: int = 0,
) -> list[dict]:
    """Random sample from filtered pool, split by question type."""
    pool = _filter_pool(sources, years, topics)

    cs_pool = [q for q in pool if q.get("type") == "complement_simplu"]
    cg_pool = [q for q in pool if q.get("type") == "complement_grupat"]

    cs_sample = random.sample(cs_pool, min(cs_count, len(cs_pool)))
    cg_sample = random.sample(cg_pool, min(cg_count, len(cg_pool)))

    combined = cs_sample + cg_sample
    random.shuffle(combined)
    return combined


def generate_review_quiz(
    user_id: int,
    count: int,
    topics: Optional[list[str]],
    db: Session,
) -> list[dict]:
    """Pick questions the user got wrong most often."""
    load_data()

    # Fetch raw answer data and compute correctness in Python (since it depends on grile.json)
    rows = (
        db.query(QuizSessionQuestion.question_id, QuizAnswer.user_answer)
        .join(QuizAnswer, QuizAnswer.session_question_id == QuizSessionQuestion.id)
        .join(QuizSession, QuizSession.id == QuizSessionQuestion.session_id)
        .filter(QuizSession.user_id == user_id)
        .all()
    )

    # Compute wrong counts
    stats: dict[str, dict] = {}
    for question_id, user_answer in rows:
        if question_id not in stats:
            stats[question_id] = {"total": 0, "wrong": 0}
        stats[question_id]["total"] += 1
        q = _by_id.get(question_id)
        if q and q.get("correct_answer") != user_answer:
            stats[question_id]["wrong"] += 1

    # Rank by wrong_count / total_attempts descending
    ranked = sorted(
        stats.items(),
        key=lambda x: (x[1]["wrong"] / max(x[1]["total"], 1), x[1]["wrong"]),
        reverse=True,
    )

    result = []
    for question_id, _ in ranked:
        q = _by_id.get(question_id)
        if q is None or q.get("correct_answer") is None:
            continue
        if topics and q["topic"] not in topics:
            continue
        result.append(q)
        if len(result) >= count:
            break

    return result


def get_question(question_id: str) -> Optional[dict]:
    """Lookup a single question by ID with all details."""
    load_data()
    return _by_id.get(question_id)
