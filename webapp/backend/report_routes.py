import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import BugReport, User

router = APIRouter()

SCREENSHOT_PATH = os.environ.get("SCREENSHOT_PATH", "/app/data/screenshots")
MAX_SCREENSHOT_SIZE = 5 * 1024 * 1024  # 5 MB
VALID_CATEGORIES = {"wrong_answer", "typo", "missing_answer", "app_bug", "other"}
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/api/reports")
async def submit_report(
    category: str = Form(...),
    description: str = Form(...),
    question_id: str | None = Form(None),
    screenshot: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    import report_routes as _self
    screenshot_filename = None
    if screenshot and screenshot.filename:
        ext = Path(screenshot.filename).suffix.lower()
        if ext not in VALID_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Screenshot must be JPEG, PNG, or WebP")

        content = await screenshot.read()
        if len(content) > MAX_SCREENSHOT_SIZE:
            raise HTTPException(status_code=400, detail="Screenshot must be under 5 MB")

        screenshot_filename = f"{uuid.uuid4().hex}{ext}"
        screenshot_dir = Path(_self.SCREENSHOT_PATH)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        with open(screenshot_dir / screenshot_filename, "wb") as f:
            f.write(content)

    report = BugReport(
        user_id=current_user.id,
        question_id=question_id or None,
        category=category,
        description=description,
        screenshot_path=screenshot_filename,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {"status": "ok", "id": report.id, "has_screenshot": screenshot_filename is not None}
