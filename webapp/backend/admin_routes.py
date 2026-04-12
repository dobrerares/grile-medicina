import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from auth import get_admin_user
from database import get_db
from models import BugReport, User
import quiz as quiz_service

router = APIRouter(prefix="/api/admin")

DATA_PATH = os.environ.get("DATA_PATH", "/data/grile.json")
PDF_PATH = os.environ.get("PDF_PATH", "/data/pdfs")
SCREENSHOT_PATH = os.environ.get("SCREENSHOT_PATH", "/app/data/screenshots")


def _validate_filename(filename: str) -> None:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")


# ---------- Grile.json management ----------

@router.get("/grile-info")
def grile_info(admin: User = Depends(get_admin_user)):
    import admin_routes as _self
    path = Path(_self.DATA_PATH)
    if not path.exists():
        raise HTTPException(status_code=404, detail="grile.json not found")

    stat = path.stat()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sources = data.get("sources", [])
    total_questions = sum(
        len(t.get("questions", []))
        for s in sources
        for t in s.get("tests", [])
    )

    return {
        "file_size": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "total_questions": total_questions,
        "source_count": len(sources),
    }


@router.post("/upload-grile")
async def upload_grile(
    file: UploadFile = File(...),
    admin: User = Depends(get_admin_user),
):
    import admin_routes as _self
    content = await file.read()
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    sources = data.get("sources")
    if not isinstance(sources, list):
        raise HTTPException(status_code=400, detail="Missing or invalid 'sources' array")

    for source in sources:
        tests = source.get("tests")
        if not isinstance(tests, list):
            raise HTTPException(status_code=400, detail="Each source must have a 'tests' array")
        for test in tests:
            questions = test.get("questions")
            if not isinstance(questions, list):
                raise HTTPException(status_code=400, detail="Each test must have a 'questions' array")

    path = Path(_self.DATA_PATH)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.decode("utf-8"))

    # Force reload
    quiz_service._file_mtime = 0.0
    quiz_service.load_data()

    total_questions = sum(
        len(t.get("questions", []))
        for s in sources
        for t in s.get("tests", [])
    )

    return {"status": "ok", "total_questions": total_questions, "source_count": len(sources)}


# ---------- PDF management ----------

@router.get("/pdfs")
def list_pdfs(admin: User = Depends(get_admin_user)):
    import admin_routes as _self
    pdf_dir = Path(_self.PDF_PATH)
    if not pdf_dir.exists():
        return []
    files = []
    for f in sorted(pdf_dir.iterdir()):
        if f.is_file() and f.suffix.lower() == ".pdf":
            files.append({"filename": f.name, "size": f.stat().st_size})
    return files


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    admin: User = Depends(get_admin_user),
):
    import admin_routes as _self
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    _validate_filename(file.filename)

    pdf_dir = Path(_self.PDF_PATH)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    dest = pdf_dir / file.filename
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    return {"status": "ok", "filename": file.filename, "size": len(content)}


@router.delete("/pdf/{filename}")
def delete_pdf(filename: str, admin: User = Depends(get_admin_user)):
    import admin_routes as _self
    _validate_filename(filename)

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be deleted")

    path = Path(_self.PDF_PATH) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    path.unlink()
    return {"status": "ok"}


# ---------- Screenshots ----------

@router.get("/screenshots/{filename}")
def serve_screenshot(filename: str, admin: User = Depends(get_admin_user)):
    import admin_routes as _self
    _validate_filename(filename)

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type")

    path = Path(_self.SCREENSHOT_PATH) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")

    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(path, media_type=media_types.get(ext, "application/octet-stream"))


# ---------- Bug report admin ----------

@router.get("/reports")
def list_reports(
    status: str | None = Query(None),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(BugReport).order_by(BugReport.created_at.desc())
    if status:
        query = query.filter(BugReport.status == status)

    reports = query.all()
    result = []
    for report in reports:
        entry = {
            "id": report.id,
            "user_id": report.user_id,
            "username": report.user.username if report.user else None,
            "question_id": report.question_id,
            "category": report.category,
            "description": report.description,
            "screenshot_path": report.screenshot_path,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "question_data": None,
        }
        if report.question_id:
            q = quiz_service.get_question(report.question_id)
            if q:
                entry["question_data"] = {
                    "text": q.get("text"),
                    "choices": q.get("choices"),
                    "correct_answer": q.get("correct_answer"),
                    "type": q.get("type"),
                    "source_file": q.get("source_file"),
                    "year": q.get("year"),
                    "topic": q.get("topic"),
                    "page_ref": q.get("page_ref"),
                }
        result.append(entry)
    return result


@router.patch("/reports/{report_id}")
def resolve_report(
    report_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = "resolved"
    db.commit()
    return {"status": "ok"}


@router.delete("/reports/{report_id}")
def delete_report(
    report_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    import admin_routes as _self
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete screenshot file if exists
    if report.screenshot_path:
        screenshot = Path(_self.SCREENSHOT_PATH) / report.screenshot_path
        if screenshot.exists():
            screenshot.unlink()

    db.delete(report)
    db.commit()
    return {"status": "ok"}
