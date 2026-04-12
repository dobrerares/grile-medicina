# Admin Dashboard & Bug Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin dashboard for managing grile.json/PDFs and reviewing bug reports, plus a user-facing bug report flow.

**Architecture:** Extend the existing FastAPI backend with admin auth (env-var-based), a BugReport model, admin endpoints for file management and report triage, and a user endpoint for submitting reports. Extend the React frontend with an admin page (tabbed layout), a report modal component, and a flag icon on question cards.

**Tech Stack:** Python/FastAPI, SQLAlchemy, SQLite, React 18, React Router, CSS custom properties, python-multipart (already installed)

---

## File Structure

**Backend — create:**
- `webapp/backend/admin_routes.py` — all `/api/admin/*` endpoints (file management + bug report admin)
- `webapp/backend/report_routes.py` — `POST /api/reports` user-facing endpoint
- `webapp/backend/tests/test_admin.py` — backend tests for admin endpoints
- `webapp/backend/tests/test_reports.py` — backend tests for user report submission
- `webapp/backend/tests/__init__.py` — empty init
- `webapp/backend/tests/conftest.py` — shared test fixtures (TestClient, test DB, test user)

**Backend — modify:**
- `webapp/backend/models.py` — add `BugReport` model
- `webapp/backend/auth.py` — add `ADMIN_USERNAME`, `is_admin()`, `get_admin_user()`
- `webapp/backend/routes.py` — add `is_admin` to `/api/auth/me` response
- `webapp/backend/main.py` — include new routers, create screenshots dir on startup
- `webapp/backend/Dockerfile` — create `/app/data/screenshots` dir, set permissions

**Frontend — create:**
- `webapp/frontend/src/components/ReportModal.tsx` — bug report modal (shared by question reports + general feedback)
- `webapp/frontend/src/pages/Admin.tsx` — admin dashboard (tabbed: reports, grile.json, PDFs)

**Frontend — modify:**
- `webapp/frontend/src/types.ts` — add `BugReport`, `GrileInfo`, `PdfFile` types
- `webapp/frontend/src/api.ts` — add admin API functions + `submitReport()`
- `webapp/frontend/src/context/AuthContext.tsx` — add `isAdmin` to context
- `webapp/frontend/src/App.tsx` — add `/admin` route with admin guard
- `webapp/frontend/src/components/QuestionCard.tsx` — add report flag icon
- `webapp/frontend/src/pages/Dashboard.tsx` — add admin link + general feedback link
- `webapp/frontend/src/index.css` — add admin page, modal, and report button styles; fix dark mode contrast on `.choice-correct` / `.correct-statements-info`

**Config — modify:**
- `docker-compose.yml` — add `ADMIN_USERNAME` env var
- `webapp/frontend/nginx.conf` — add `client_max_body_size 10m` for uploads

---

### Task 1: Backend — BugReport model

**Files:**
- Modify: `webapp/backend/models.py`

- [ ] **Step 1: Add BugReport model to models.py**

Add after the `QuizAnswer` class:

```python
class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String, nullable=True)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    screenshot_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
```

- [ ] **Step 2: Verify the model is valid**

Run from `webapp/backend/`:

```bash
python -c "from models import BugReport; print(BugReport.__tablename__)"
```

Expected: `bug_reports`

- [ ] **Step 3: Commit**

```bash
git add webapp/backend/models.py
git commit -m "feat: add BugReport model"
```

---

### Task 2: Backend — Admin auth helpers

**Files:**
- Modify: `webapp/backend/auth.py`
- Modify: `webapp/backend/routes.py`

- [ ] **Step 1: Add admin helpers to auth.py**

Add at the top, after `JWT_EXPIRATION_HOURS`:

```python
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
```

Add at the end of the file:

```python
def is_admin(user: User) -> bool:
    return bool(ADMIN_USERNAME and user.username == ADMIN_USERNAME)


def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user = get_current_user(credentials, db)
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
```

- [ ] **Step 2: Update `/api/auth/me` in routes.py to include is_admin**

Change the `me` endpoint in `routes.py`:

```python
from auth import create_access_token, get_current_user, hash_password, verify_password, is_admin
```

```python
@router.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat(),
        "is_admin": is_admin(current_user),
    }
```

- [ ] **Step 3: Verify imports work**

```bash
cd webapp/backend && python -c "from auth import is_admin, get_admin_user; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add webapp/backend/auth.py webapp/backend/routes.py
git commit -m "feat: add admin auth helpers and is_admin to /me endpoint"
```

---

### Task 3: Backend — Test infrastructure + admin auth tests

**Files:**
- Create: `webapp/backend/tests/__init__.py`
- Create: `webapp/backend/tests/conftest.py`
- Create: `webapp/backend/tests/test_admin_auth.py`

- [ ] **Step 1: Create test infrastructure**

Create `webapp/backend/tests/__init__.py` (empty file).

Create `webapp/backend/tests/conftest.py`:

```python
import os
import json
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set env vars before importing app modules
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["JWT_SECRET"] = "test-secret"

from database import Base, get_db
from main import app
from auth import hash_password
from models import User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session, tmp_path):
    # Create a minimal grile.json
    grile_path = tmp_path / "grile.json"
    grile_data = {
        "version": "1.0",
        "sources": [{
            "file": "Test 2024",
            "year": 2024,
            "tests": [{
                "test_id": "2024_celula_1",
                "title": "Test",
                "topic": "celula",
                "questions": [{
                    "id": "2024_celula_1_q1",
                    "number": 1,
                    "type": "complement_simplu",
                    "text": "Test question?",
                    "choices": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
                    "correct_answer": "A",
                    "correct_statements": None,
                    "page_ref": "pag. 1",
                }],
            }],
        }],
        "metadata": {"total_questions": 1},
    }
    grile_path.write_text(json.dumps(grile_data))

    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()

    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()

    os.environ["DATA_PATH"] = str(grile_path)
    os.environ["PDF_PATH"] = str(pdf_dir)
    os.environ["SCREENSHOT_PATH"] = str(screenshots_dir)

    # Force reload quiz data
    import quiz as quiz_service
    quiz_service._file_mtime = 0.0
    quiz_service.load_data()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_token(client, db_session):
    user = User(username="admin", password_hash=hash_password("password"))
    db_session.add(user)
    db_session.commit()
    res = client.post("/api/auth/login", json={"username": "admin", "password": "password"})
    return res.json()["token"]


@pytest.fixture()
def user_token(client, db_session):
    user = User(username="regular", password_hash=hash_password("password"))
    db_session.add(user)
    db_session.commit()
    res = client.post("/api/auth/login", json={"username": "regular", "password": "password"})
    return res.json()["token"]
```

- [ ] **Step 2: Write admin auth tests**

Create `webapp/backend/tests/test_admin_auth.py`:

```python
def test_me_returns_is_admin_true(client, admin_token):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["is_admin"] is True


def test_me_returns_is_admin_false(client, user_token):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    assert res.json()["is_admin"] is False
```

- [ ] **Step 3: Install pytest and httpx (for TestClient)**

```bash
cd webapp/backend && pip install pytest httpx
```

- [ ] **Step 4: Run tests**

```bash
cd webapp/backend && python -m pytest tests/test_admin_auth.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add webapp/backend/tests/
git commit -m "test: add test infrastructure and admin auth tests"
```

---

### Task 4: Backend — Admin file management endpoints

**Files:**
- Create: `webapp/backend/admin_routes.py`
- Modify: `webapp/backend/main.py`

- [ ] **Step 1: Write tests for file management endpoints**

Add to `webapp/backend/tests/test_admin.py`:

```python
import io
import json


def test_grile_info(client, admin_token):
    res = client.get("/api/admin/grile-info", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "file_size" in data
    assert data["total_questions"] == 1
    assert data["source_count"] == 1


def test_grile_info_forbidden_for_regular_user(client, user_token):
    res = client.get("/api/admin/grile-info", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 403


def test_upload_grile(client, admin_token):
    new_data = {
        "sources": [{
            "file": "New Source",
            "year": 2025,
            "tests": [{"test_id": "t1", "title": "T", "topic": "celula", "questions": [
                {"id": "q1", "number": 1, "type": "complement_simplu",
                 "text": "Q?", "choices": {"A": "a"}, "correct_answer": "A",
                 "correct_statements": None, "page_ref": "pag. 1"}
            ]}],
        }],
    }
    file = io.BytesIO(json.dumps(new_data).encode())
    res = client.post(
        "/api/admin/upload-grile",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("grile.json", file, "application/json")},
    )
    assert res.status_code == 200
    assert res.json()["total_questions"] == 1

    # Verify reload happened
    info = client.get("/api/admin/grile-info", headers={"Authorization": f"Bearer {admin_token}"})
    assert info.json()["source_count"] == 1


def test_upload_grile_invalid_json(client, admin_token):
    file = io.BytesIO(b"not json")
    res = client.post(
        "/api/admin/upload-grile",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("grile.json", file, "application/json")},
    )
    assert res.status_code == 400


def test_upload_grile_missing_sources(client, admin_token):
    file = io.BytesIO(json.dumps({"no_sources": True}).encode())
    res = client.post(
        "/api/admin/upload-grile",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("grile.json", file, "application/json")},
    )
    assert res.status_code == 400


def test_list_pdfs(client, admin_token, tmp_path):
    # Create a fake PDF in the PDF dir
    import os
    pdf_dir = os.environ["PDF_PATH"]
    with open(os.path.join(pdf_dir, "test.pdf"), "wb") as f:
        f.write(b"%PDF-1.4 fake content")
    res = client.get("/api/admin/pdfs", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["filename"] == "test.pdf"


def test_upload_pdf(client, admin_token):
    file = io.BytesIO(b"%PDF-1.4 fake pdf content")
    res = client.post(
        "/api/admin/upload-pdf",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("new.pdf", file, "application/pdf")},
    )
    assert res.status_code == 200

    # Verify it shows up in list
    pdfs = client.get("/api/admin/pdfs", headers={"Authorization": f"Bearer {admin_token}"})
    filenames = [p["filename"] for p in pdfs.json()]
    assert "new.pdf" in filenames


def test_delete_pdf(client, admin_token):
    import os
    pdf_dir = os.environ["PDF_PATH"]
    with open(os.path.join(pdf_dir, "delete_me.pdf"), "wb") as f:
        f.write(b"%PDF-1.4")

    res = client.delete("/api/admin/pdf/delete_me.pdf", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    assert not os.path.exists(os.path.join(pdf_dir, "delete_me.pdf"))


def test_delete_pdf_path_traversal(client, admin_token):
    res = client.delete("/api/admin/pdf/..%2Fsecret.txt", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd webapp/backend && python -m pytest tests/test_admin.py -v
```

Expected: all FAIL (admin_routes not yet created)

- [ ] **Step 3: Create admin_routes.py**

Create `webapp/backend/admin_routes.py`:

```python
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
    path = Path(DATA_PATH)
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

    path = Path(DATA_PATH)
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
    pdf_dir = Path(PDF_PATH)
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
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    _validate_filename(file.filename)

    pdf_dir = Path(PDF_PATH)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    dest = pdf_dir / file.filename
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    return {"status": "ok", "filename": file.filename, "size": len(content)}


@router.delete("/pdf/{filename}")
def delete_pdf(filename: str, admin: User = Depends(get_admin_user)):
    _validate_filename(filename)

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be deleted")

    path = Path(PDF_PATH) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    path.unlink()
    return {"status": "ok"}


# ---------- Screenshots ----------

@router.get("/screenshots/{filename}")
def serve_screenshot(filename: str, admin: User = Depends(get_admin_user)):
    _validate_filename(filename)

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type")

    path = Path(SCREENSHOT_PATH) / filename
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
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete screenshot file if exists
    if report.screenshot_path:
        screenshot = Path(SCREENSHOT_PATH) / report.screenshot_path
        if screenshot.exists():
            screenshot.unlink()

    db.delete(report)
    db.commit()
    return {"status": "ok"}
```

- [ ] **Step 4: Register admin router in main.py**

Add to `webapp/backend/main.py`:

```python
from admin_routes import router as admin_router
from report_routes import router as report_router
```

And after `app.include_router(router)`:

```python
app.include_router(admin_router)
app.include_router(report_router)
```

Also in the `lifespan` function, create the screenshots directory:

```python
import os
screenshots_dir = os.environ.get("SCREENSHOT_PATH", "/app/data/screenshots")
os.makedirs(screenshots_dir, exist_ok=True)
```

- [ ] **Step 5: Run tests**

```bash
cd webapp/backend && python -m pytest tests/test_admin.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add webapp/backend/admin_routes.py webapp/backend/main.py webapp/backend/tests/test_admin.py
git commit -m "feat: add admin file management endpoints with tests"
```

---

### Task 5: Backend — User bug report submission endpoint

**Files:**
- Create: `webapp/backend/report_routes.py`
- Create: `webapp/backend/tests/test_reports.py`

- [ ] **Step 1: Write tests for report submission**

Create `webapp/backend/tests/test_reports.py`:

```python
import io


def test_submit_report_with_question(client, user_token):
    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={
            "question_id": "2024_celula_1_q1",
            "category": "wrong_answer",
            "description": "The answer should be B not A",
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["id"] > 0


def test_submit_report_general(client, user_token):
    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={
            "category": "app_bug",
            "description": "The timer doesn't work",
        },
    )
    assert res.status_code == 200


def test_submit_report_with_screenshot(client, user_token):
    screenshot = io.BytesIO(b"\x89PNG\r\n\x1a\n fake png data")
    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={
            "category": "typo",
            "description": "Typo in question text",
        },
        files={"screenshot": ("shot.png", screenshot, "image/png")},
    )
    assert res.status_code == 200
    assert res.json()["has_screenshot"] is True


def test_submit_report_invalid_category(client, user_token):
    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={
            "category": "invalid_category",
            "description": "Some description",
        },
    )
    assert res.status_code == 400


def test_submit_report_missing_description(client, user_token):
    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={
            "category": "app_bug",
        },
    )
    assert res.status_code == 422


def test_submit_report_screenshot_too_large(client, user_token):
    big_file = io.BytesIO(b"x" * (5 * 1024 * 1024 + 1))
    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={
            "category": "app_bug",
            "description": "Bug",
        },
        files={"screenshot": ("big.png", big_file, "image/png")},
    )
    assert res.status_code == 400


def test_admin_can_see_submitted_report(client, admin_token, user_token):
    # Submit as regular user
    client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={"category": "app_bug", "description": "Test bug"},
    )

    # View as admin
    res = client.get("/api/admin/reports", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["category"] == "app_bug"


def test_admin_resolve_report(client, admin_token, user_token):
    client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={"category": "app_bug", "description": "Bug"},
    )
    reports = client.get("/api/admin/reports", headers={"Authorization": f"Bearer {admin_token}"}).json()
    report_id = reports[0]["id"]

    res = client.patch(f"/api/admin/reports/{report_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # Verify status changed
    updated = client.get("/api/admin/reports", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert updated[0]["status"] == "resolved"


def test_admin_delete_report(client, admin_token, user_token):
    client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={"category": "app_bug", "description": "Bug"},
    )
    reports = client.get("/api/admin/reports", headers={"Authorization": f"Bearer {admin_token}"}).json()
    report_id = reports[0]["id"]

    res = client.delete(f"/api/admin/reports/{report_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    remaining = client.get("/api/admin/reports", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert len(remaining) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd webapp/backend && python -m pytest tests/test_reports.py -v
```

Expected: FAIL (report_routes doesn't exist yet)

- [ ] **Step 3: Create report_routes.py**

Create `webapp/backend/report_routes.py`:

```python
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

    screenshot_filename = None
    if screenshot and screenshot.filename:
        ext = Path(screenshot.filename).suffix.lower()
        if ext not in VALID_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Screenshot must be JPEG, PNG, or WebP")

        content = await screenshot.read()
        if len(content) > MAX_SCREENSHOT_SIZE:
            raise HTTPException(status_code=400, detail="Screenshot must be under 5 MB")

        screenshot_filename = f"{uuid.uuid4().hex}{ext}"
        screenshot_dir = Path(SCREENSHOT_PATH)
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
```

- [ ] **Step 4: Run all backend tests**

```bash
cd webapp/backend && python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add webapp/backend/report_routes.py webapp/backend/tests/test_reports.py
git commit -m "feat: add user bug report submission endpoint with tests"
```

---

### Task 6: Backend — Docker & config updates

**Files:**
- Modify: `docker-compose.yml`
- Modify: `webapp/backend/Dockerfile`
- Modify: `webapp/frontend/nginx.conf`

- [ ] **Step 1: Add ADMIN_USERNAME to docker-compose.yml**

Add to the `backend` service `environment` list:

```yaml
      - ADMIN_USERNAME=${ADMIN_USERNAME:-}
      - SCREENSHOT_PATH=/app/data/screenshots
```

- [ ] **Step 2: Update Dockerfile to create screenshots dir**

In `webapp/backend/Dockerfile`, change the `mkdir` line:

```dockerfile
RUN adduser --disabled-password --no-create-home appuser \
    && mkdir -p /app/data /app/data/screenshots \
    && chown -R appuser:appuser /app/data
```

- [ ] **Step 3: Add client_max_body_size to nginx.conf**

Add inside the `server` block, before the `location` blocks:

```nginx
    client_max_body_size 10m;
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml webapp/backend/Dockerfile webapp/frontend/nginx.conf
git commit -m "chore: add admin env vars, screenshots dir, and upload size limit"
```

---

### Task 7: Frontend — Types and API functions

**Files:**
- Modify: `webapp/frontend/src/types.ts`
- Modify: `webapp/frontend/src/api.ts`

- [ ] **Step 1: Add new types to types.ts**

Add at the end of `webapp/frontend/src/types.ts`:

```typescript
export interface BugReport {
  id: number;
  user_id: number;
  username: string | null;
  question_id: string | null;
  category: string;
  description: string;
  screenshot_path: string | null;
  status: string;
  created_at: string;
  question_data: {
    text: string;
    choices: Record<string, string>;
    correct_answer: string | null;
    type: string;
    source_file: string;
    year: number;
    topic: string;
    page_ref: string | null;
  } | null;
}

export interface GrileInfo {
  file_size: number;
  last_modified: string;
  total_questions: number;
  source_count: number;
}

export interface PdfFile {
  filename: string;
  size: number;
}
```

- [ ] **Step 2: Add API functions to api.ts**

Add the new imports to the import block at the top of `api.ts`:

```typescript
import type {
  AnswerResult,
  AvailableCounts,
  BugReport,
  GrileInfo,
  HistorySession,
  PdfFile,
  QuizDetail,
  Source,
  Stats,
  Topic,
  User,
  WeakQuestion,
} from "./types";
```

Add at the end of `api.ts`, before `export default api;`:

```typescript
// --- Bug Reports (user) ---

export async function submitReport(data: FormData): Promise<{ status: string; id: number }> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch("/api/reports", {
    method: "POST",
    headers,
    body: data,
  });
  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// --- Admin ---

export async function getGrileInfo(): Promise<GrileInfo> {
  return api.get("/admin/grile-info");
}

export async function uploadGrile(file: File): Promise<{ status: string; total_questions: number; source_count: number }> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/admin/upload-grile", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function getAdminPdfs(): Promise<PdfFile[]> {
  return api.get("/admin/pdfs");
}

export async function uploadPdf(file: File): Promise<{ status: string; filename: string }> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/admin/upload-pdf", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function adminDeletePdf(filename: string): Promise<{ status: string }> {
  const token = getToken();
  const res = await fetch(`/api/admin/pdf/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Delete failed (${res.status})`);
  }
  return res.json();
}

export async function getAdminReports(status?: string): Promise<BugReport[]> {
  const query = status ? `?status=${status}` : "";
  return api.get(`/admin/reports${query}`);
}

export async function resolveReport(id: number): Promise<{ status: string }> {
  const token = getToken();
  const res = await fetch(`/api/admin/reports/${id}`, {
    method: "PATCH",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed (${res.status})`);
  }
  return res.json();
}

export async function deleteReport(id: number): Promise<{ status: string }> {
  const token = getToken();
  const res = await fetch(`/api/admin/reports/${id}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed (${res.status})`);
  }
  return res.json();
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd webapp/frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add webapp/frontend/src/types.ts webapp/frontend/src/api.ts
git commit -m "feat: add frontend types and API functions for admin and reports"
```

---

### Task 8: Frontend — Auth context with isAdmin

**Files:**
- Modify: `webapp/frontend/src/context/AuthContext.tsx`

- [ ] **Step 1: Add isAdmin to User type**

In `webapp/frontend/src/types.ts`, update the `User` interface:

```typescript
export interface User {
  id: number;
  username: string;
  is_admin?: boolean;
}
```

- [ ] **Step 2: Add isAdmin to AuthContext**

In `webapp/frontend/src/context/AuthContext.tsx`, update the `AuthContextValue` interface:

```typescript
interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAdmin: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => void;
}
```

Add `isAdmin` to the provider value. In the `AuthProvider` component, derive it from the user:

After `const [loading, setLoading] = useState(true);` — no new state needed, derive it:

In the return, update the value:

```tsx
<AuthContext.Provider value={{ user, token, loading, isAdmin: user?.is_admin ?? false, login, register, logout }}>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd webapp/frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add webapp/frontend/src/types.ts webapp/frontend/src/context/AuthContext.tsx
git commit -m "feat: add isAdmin to auth context"
```

---

### Task 9: Frontend — ReportModal component

**Files:**
- Create: `webapp/frontend/src/components/ReportModal.tsx`

- [ ] **Step 1: Create the ReportModal component**

Create `webapp/frontend/src/components/ReportModal.tsx`:

```tsx
import { useState, useRef } from "react";
import { submitReport } from "../api";

const CATEGORIES = [
  { value: "wrong_answer", label: "Raspuns gresit" },
  { value: "typo", label: "Eroare in text" },
  { value: "missing_answer", label: "Raspuns lipsa" },
  { value: "app_bug", label: "Bug aplicatie" },
  { value: "other", label: "Altele" },
];

interface ReportModalProps {
  onClose: () => void;
  questionId?: string;
  sourceFile?: string;
  pageRef?: string;
  defaultCategory?: string;
}

export default function ReportModal({
  onClose,
  questionId,
  sourceFile,
  pageRef,
  defaultCategory,
}: ReportModalProps) {
  const [category, setCategory] = useState(defaultCategory || (questionId ? "wrong_answer" : "app_bug"));
  const [description, setDescription] = useState("");
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;

    setSubmitting(true);
    setError("");

    const form = new FormData();
    form.append("category", category);
    form.append("description", description.trim());
    if (questionId) {
      form.append("question_id", questionId);
    }
    if (screenshot) {
      form.append("screenshot", screenshot);
    }

    try {
      await submitReport(form);
      setSuccess(true);
      setTimeout(onClose, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la trimitere");
    } finally {
      setSubmitting(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("Fisierul trebuie sa fie sub 5 MB");
      return;
    }
    setScreenshot(file);
    setError("");
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Raporteaza o problema</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {success ? (
          <div className="report-success">Raportul a fost trimis!</div>
        ) : (
          <form onSubmit={handleSubmit}>
            {questionId && (
              <div className="report-context">
                <span className="report-context-label">Intrebare:</span> {questionId}
                {sourceFile && <><br /><span className="report-context-label">Sursa:</span> {sourceFile}</>}
                {pageRef && <><br /><span className="report-context-label">Pagina:</span> {pageRef}</>}
              </div>
            )}

            <label className="report-field">
              <span>Categorie</span>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </label>

            <label className="report-field">
              <span>Descriere</span>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descrie problema..."
                rows={4}
                required
              />
            </label>

            <label className="report-field">
              <span>Captura de ecran (optional)</span>
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
              />
              {screenshot && (
                <span className="report-file-name">{screenshot.name}</span>
              )}
            </label>

            {error && <div className="auth-error">{error}</div>}

            <div className="report-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose}>Anuleaza</button>
              <button type="submit" className="btn btn-primary" disabled={submitting || !description.trim()}>
                {submitting ? "Se trimite..." : "Trimite"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd webapp/frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add webapp/frontend/src/components/ReportModal.tsx
git commit -m "feat: add ReportModal component for bug report submission"
```

---

### Task 10: Frontend — Report button on QuestionCard

**Files:**
- Modify: `webapp/frontend/src/components/QuestionCard.tsx`

- [ ] **Step 1: Add report button and modal state to QuestionCard**

Add at the top of the file:

```tsx
import { useState } from "react";
import ReportModal from "./ReportModal";
```

Inside the `QuestionCard` component, add state:

```tsx
const [showReport, setShowReport] = useState(false);
```

Add a report flag button in the `question-header` div, after the year label:

```tsx
<button
  className="report-flag-btn"
  onClick={() => setShowReport(true)}
  title="Raporteaza o problema"
  type="button"
>
  &#9873;
</button>
```

At the end of the component's return, before the closing `</div>` of `question-card`:

```tsx
{showReport && (
  <ReportModal
    onClose={() => setShowReport(false)}
    questionId={question.question_id}
    sourceFile={sourceFile}
    pageRef={pageRef}
  />
)}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd webapp/frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add webapp/frontend/src/components/QuestionCard.tsx
git commit -m "feat: add report flag button to QuestionCard"
```

---

### Task 11: Frontend — Admin dashboard page

**Files:**
- Create: `webapp/frontend/src/pages/Admin.tsx`

- [ ] **Step 1: Create the Admin page**

Create `webapp/frontend/src/pages/Admin.tsx`:

```tsx
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  getAdminReports,
  getGrileInfo,
  uploadGrile,
  getAdminPdfs,
  uploadPdf,
  adminDeletePdf,
  resolveReport,
  deleteReport,
} from "../api";
import type { BugReport, GrileInfo, PdfFile } from "../types";

const CATEGORY_LABELS: Record<string, string> = {
  wrong_answer: "Raspuns gresit",
  typo: "Eroare in text",
  missing_answer: "Raspuns lipsa",
  app_bug: "Bug aplicatie",
  other: "Altele",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes} min in urma`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ore in urma`;
  const days = Math.floor(hours / 24);
  return `${days} zile in urma`;
}

type Tab = "reports" | "grile" | "pdfs";

export default function Admin() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("reports");

  useEffect(() => {
    if (!isAdmin) navigate("/dashboard", { replace: true });
  }, [isAdmin, navigate]);

  if (!isAdmin) return null;

  return (
    <div className="admin-page">
      <header className="admin-header">
        <h1>Admin Dashboard</h1>
        <button className="btn btn-secondary" onClick={() => navigate("/dashboard")}>
          Inapoi la app
        </button>
      </header>

      <div className="admin-tabs">
        <button className={`admin-tab ${tab === "reports" ? "admin-tab-active" : ""}`} onClick={() => setTab("reports")}>
          Bug Reports
        </button>
        <button className={`admin-tab ${tab === "grile" ? "admin-tab-active" : ""}`} onClick={() => setTab("grile")}>
          Grile.json
        </button>
        <button className={`admin-tab ${tab === "pdfs" ? "admin-tab-active" : ""}`} onClick={() => setTab("pdfs")}>
          PDFs
        </button>
      </div>

      {tab === "reports" && <ReportsTab />}
      {tab === "grile" && <GrileTab />}
      {tab === "pdfs" && <PdfsTab />}
    </div>
  );
}


function ReportsTab() {
  const [reports, setReports] = useState<BugReport[]>([]);
  const [filter, setFilter] = useState<"open" | "resolved">("open");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getAdminReports(filter);
      setReports(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  async function handleResolve(id: number) {
    try {
      await resolveReport(id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Sterge raportul?")) return;
    try {
      await deleteReport(id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-filter-bar">
        <button
          className={`admin-pill ${filter === "open" ? "admin-pill-active" : ""}`}
          onClick={() => setFilter("open")}
        >
          Open ({filter === "open" ? reports.length : "..."})
        </button>
        <button
          className={`admin-pill ${filter === "resolved" ? "admin-pill-active" : ""}`}
          onClick={() => setFilter("resolved")}
        >
          Resolved ({filter === "resolved" ? reports.length : "..."})
        </button>
      </div>

      {error && <div className="auth-error">{error}</div>}
      {loading && <div className="admin-loading">Se incarca...</div>}

      {!loading && reports.length === 0 && (
        <div className="admin-empty">Niciun raport {filter}.</div>
      )}

      <div className="admin-report-list">
        {reports.map((r) => (
          <div key={r.id} className="admin-report-row">
            <div className="admin-report-header" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>
              <div className="admin-report-info">
                <span className="admin-report-category">{CATEGORY_LABELS[r.category] || r.category}</span>
                <span className="admin-report-question">
                  {r.question_id ? `Q ${r.question_id}` : "General"}
                </span>
                <span className="admin-report-meta">
                  {r.username || `user #${r.user_id}`} — {timeAgo(r.created_at)}
                </span>
              </div>
              <div className="admin-report-actions">
                {r.status === "open" && (
                  <button
                    className="admin-action-btn admin-action-resolve"
                    onClick={(e) => { e.stopPropagation(); handleResolve(r.id); }}
                    title="Rezolva"
                  >
                    &#10003;
                  </button>
                )}
                <button
                  className="admin-action-btn admin-action-delete"
                  onClick={(e) => { e.stopPropagation(); handleDelete(r.id); }}
                  title="Sterge"
                >
                  &#10005;
                </button>
              </div>
            </div>

            {expanded === r.id && (
              <div className="admin-report-detail">
                <p className="admin-report-description">{r.description}</p>

                {r.screenshot_path && (
                  <img
                    className="admin-report-screenshot"
                    src={`/api/admin/screenshots/${r.screenshot_path}`}
                    alt="Screenshot"
                  />
                )}

                {r.question_data && (
                  <div className="admin-question-context">
                    <h4>Detalii intrebare</h4>
                    <p className="admin-q-text">{r.question_data.text}</p>
                    <div className="admin-q-choices">
                      {Object.entries(r.question_data.choices).map(([key, val]) => (
                        <div
                          key={key}
                          className={`admin-q-choice ${key === r.question_data!.correct_answer ? "admin-q-choice-correct" : ""}`}
                        >
                          <strong>{key}.</strong> {val}
                        </div>
                      ))}
                    </div>
                    <div className="admin-q-meta">
                      <span>Tip: {r.question_data.type === "complement_grupat" ? "CG" : "CS"}</span>
                      <span>An: {r.question_data.year}</span>
                      <span>Tema: {r.question_data.topic}</span>
                      <span>Sursa: {r.question_data.source_file}</span>
                      {r.question_data.page_ref && <span>Pagina: {r.question_data.page_ref}</span>}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}


function GrileTab() {
  const [info, setInfo] = useState<GrileInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    getGrileInfo()
      .then(setInfo)
      .catch((err) => setError(err instanceof Error ? err.message : "Eroare"))
      .finally(() => setLoading(false));
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!confirm("Inlocuiesti grile.json? Aceasta actiune nu poate fi anulata.")) {
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    try {
      const res = await uploadGrile(file);
      setSuccess(`Incarcat cu succes: ${res.total_questions} intrebari din ${res.source_count} surse`);
      const updated = await getGrileInfo();
      setInfo(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la incarcare");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="admin-tab-content">
      {loading && <div className="admin-loading">Se incarca...</div>}
      {error && <div className="auth-error">{error}</div>}
      {success && <div className="admin-success">{success}</div>}

      {info && (
        <div className="admin-file-info">
          <div className="admin-info-grid">
            <div className="admin-info-item">
              <span className="admin-info-label">Dimensiune</span>
              <span className="admin-info-value">{formatSize(info.file_size)}</span>
            </div>
            <div className="admin-info-item">
              <span className="admin-info-label">Ultima modificare</span>
              <span className="admin-info-value">{new Date(info.last_modified).toLocaleString("ro-RO")}</span>
            </div>
            <div className="admin-info-item">
              <span className="admin-info-label">Total intrebari</span>
              <span className="admin-info-value">{info.total_questions.toLocaleString()}</span>
            </div>
            <div className="admin-info-item">
              <span className="admin-info-label">Surse</span>
              <span className="admin-info-value">{info.source_count}</span>
            </div>
          </div>
        </div>
      )}

      <div className="admin-upload-section">
        <label className="btn btn-primary admin-upload-btn">
          {uploading ? "Se incarca..." : "Incarca grile.json nou"}
          <input type="file" accept=".json" onChange={handleUpload} hidden disabled={uploading} />
        </label>
      </div>
    </div>
  );
}


function PdfsTab() {
  const [pdfs, setPdfs] = useState<PdfFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAdminPdfs();
      setPdfs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");
    setSuccess("");
    try {
      await uploadPdf(file);
      setSuccess(`${file.name} incarcat cu succes`);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la incarcare");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(filename: string) {
    if (!confirm(`Stergi ${filename}?`)) return;
    setError("");
    setSuccess("");
    try {
      await adminDeletePdf(filename);
      setSuccess(`${filename} sters`);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la stergere");
    }
  }

  return (
    <div className="admin-tab-content">
      {error && <div className="auth-error">{error}</div>}
      {success && <div className="admin-success">{success}</div>}
      {loading && <div className="admin-loading">Se incarca...</div>}

      <div className="admin-upload-section">
        <label className="btn btn-primary admin-upload-btn">
          {uploading ? "Se incarca..." : "Incarca PDF"}
          <input type="file" accept=".pdf" onChange={handleUpload} hidden disabled={uploading} />
        </label>
      </div>

      <div className="admin-pdf-list">
        {pdfs.map((p) => (
          <div key={p.filename} className="admin-pdf-row">
            <span className="admin-pdf-name">{p.filename}</span>
            <span className="admin-pdf-size">{formatSize(p.size)}</span>
            <button
              className="admin-action-btn admin-action-delete"
              onClick={() => handleDelete(p.filename)}
              title="Sterge"
            >
              &#10005;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd webapp/frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add webapp/frontend/src/pages/Admin.tsx
git commit -m "feat: add admin dashboard page with reports, grile, and PDF tabs"
```

---

### Task 12: Frontend — Routing, Dashboard links, and general feedback

**Files:**
- Modify: `webapp/frontend/src/App.tsx`
- Modify: `webapp/frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Add admin route to App.tsx**

Add import:

```tsx
import Admin from "./pages/Admin";
```

Add a new route inside `<Routes>`, after the quiz results route and before the catch-all:

```tsx
<Route
  path="/admin"
  element={
    <ProtectedRoute>
      <Admin />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 2: Add admin link and general feedback to Dashboard.tsx**

Add at the top imports:

```tsx
import { useState } from "react";
import ReportModal from "../components/ReportModal";
```

Note: `useEffect` and `useState` should be combined in the import — update the existing `import { useEffect, useState } from "react";` (it already imports `useEffect` and `useState`, so just add `useState` to the existing import if not there — it already has it).

Add the ReportModal import.

Inside the `Dashboard` component, add state:

```tsx
const [showReport, setShowReport] = useState(false);
```

And destructure `isAdmin` from `useAuth()`:

```tsx
const { user, logout, isAdmin } = useAuth();
```

In the header section, add an admin link and general feedback link. After the logout button:

```tsx
{isAdmin && (
  <button className="btn btn-secondary" onClick={() => navigate("/admin")}>
    Admin
  </button>
)}
```

In the quick actions section, add a feedback button:

```tsx
<button className="btn btn-secondary" onClick={() => setShowReport(true)}>
  Raporteaza o problema
</button>
```

At the end of the component, before the closing `</div>` of `dashboard-page`:

```tsx
{showReport && (
  <ReportModal
    onClose={() => setShowReport(false)}
    defaultCategory="app_bug"
  />
)}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd webapp/frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add webapp/frontend/src/App.tsx webapp/frontend/src/pages/Dashboard.tsx
git commit -m "feat: add admin route, admin link, and general feedback button"
```

---

### Task 13: Frontend — CSS styles for admin, modal, report button, and dark mode contrast fix

**Files:**
- Modify: `webapp/frontend/src/index.css`

- [ ] **Step 1: Fix dark mode contrast on correct answer elements**

In `index.css`, the light-mode `--color-success` is `#16a34a` and `--color-success-bg` is `#f0fdf4`. In dark mode, `--color-success` is `#4ade80` and `--color-success-bg` is `#1a2e1a`.

The issue is `.choice-correct` and `.correct-statements-info` use these vars, but the green text on dark green background has poor contrast. Fix by brightening the dark mode success colors:

In the second `@media (prefers-color-scheme: dark)` block, update:

```css
    --color-success: #86efac;
    --color-success-bg: #14532d;
```

This gives brighter green text (`#86efac`) on a darker green background (`#14532d`) — higher contrast.

- [ ] **Step 2: Add modal styles**

Add at the end of `index.css`:

```css
/* ------ Modal ------ */

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 1.5rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.modal-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
}

.modal-close:hover {
  color: var(--color-text);
}

/* ------ Report Modal ------ */

.report-context {
  background: var(--color-bg-muted);
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
  line-height: 1.6;
}

.report-context-label {
  font-weight: 600;
  color: var(--color-text);
}

.report-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}

.report-field select,
.report-field textarea,
.report-field input[type="file"] {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.9375rem;
  color: var(--color-text);
  font-family: inherit;
}

.report-field textarea {
  resize: vertical;
  min-height: 80px;
}

.report-field select:focus,
.report-field textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.report-file-name {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.report-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 0.5rem;
}

.report-success {
  padding: 1.5rem;
  text-align: center;
  font-weight: 500;
  color: var(--color-success);
  font-size: 1rem;
}

.report-flag-btn {
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.125rem 0.25rem;
  margin-left: auto;
  opacity: 0.6;
  transition: opacity 0.15s, color 0.15s;
}

.report-flag-btn:hover {
  opacity: 1;
  color: var(--color-warning, #d97706);
}
```

- [ ] **Step 3: Add admin dashboard styles**

Continue appending to `index.css`:

```css
/* ------ Admin Dashboard ------ */

.admin-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.admin-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.admin-tabs {
  display: flex;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 1.5rem;
}

.admin-tab {
  background: none;
  border: none;
  padding: 0.75rem 1.25rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--color-text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s;
}

.admin-tab:hover {
  color: var(--color-text);
}

.admin-tab-active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.admin-tab-content {
  min-height: 300px;
}

.admin-filter-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.admin-pill {
  padding: 0.375rem 0.875rem;
  border-radius: 99px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  font-size: 0.8125rem;
  color: var(--color-text);
  cursor: pointer;
  transition: all 0.15s;
}

.admin-pill:hover {
  border-color: var(--color-primary);
}

.admin-pill-active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.admin-loading {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
}

.admin-empty {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.9375rem;
}

.admin-success {
  background: var(--color-success-bg);
  color: var(--color-success);
  padding: 0.625rem 0.75rem;
  border-radius: var(--radius);
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

/* Admin reports */

.admin-report-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.admin-report-row {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.admin-report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem 1rem;
  cursor: pointer;
  transition: background 0.1s;
}

.admin-report-header:hover {
  background: var(--color-bg-hover);
}

.admin-report-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.admin-report-category {
  font-weight: 500;
  font-size: 0.9375rem;
}

.admin-report-question {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.admin-report-meta {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.admin-report-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.admin-action-btn {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.15s;
}

.admin-action-resolve {
  color: var(--color-success);
}

.admin-action-resolve:hover {
  background: var(--color-success-bg);
  border-color: var(--color-success);
}

.admin-action-delete {
  color: var(--color-error);
}

.admin-action-delete:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error);
}

/* Admin report detail */

.admin-report-detail {
  padding: 1rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-detail);
}

.admin-report-description {
  font-size: 0.9375rem;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.admin-report-screenshot {
  max-width: 100%;
  max-height: 300px;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  margin-bottom: 1rem;
}

.admin-question-context {
  background: var(--color-bg-muted);
  border-radius: var(--radius);
  padding: 1rem;
}

.admin-question-context h4 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.admin-q-text {
  font-size: 0.875rem;
  line-height: 1.6;
  margin-bottom: 0.75rem;
}

.admin-q-choices {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}

.admin-q-choice {
  padding: 0.375rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8125rem;
}

.admin-q-choice-correct {
  background: var(--color-success-bg);
  color: var(--color-success);
  font-weight: 500;
}

.admin-q-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

/* Admin file info */

.admin-file-info {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.25rem;
  margin-bottom: 1rem;
}

.admin-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.admin-info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.admin-info-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.admin-info-value {
  font-size: 1.125rem;
  font-weight: 600;
}

.admin-upload-section {
  margin-bottom: 1.5rem;
}

.admin-upload-btn {
  cursor: pointer;
}

/* Admin PDF list */

.admin-pdf-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.admin-pdf-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.admin-pdf-name {
  flex: 1;
  font-size: 0.875rem;
  font-weight: 500;
}

.admin-pdf-size {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

/* Responsive admin */

@media (max-width: 768px) {
  .admin-info-grid {
    grid-template-columns: 1fr;
  }

  .admin-report-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .admin-report-actions {
    align-self: flex-end;
  }
}
```

- [ ] **Step 4: Verify the build works**

```bash
cd webapp/frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add webapp/frontend/src/index.css
git commit -m "feat: add admin, modal, and report styles; fix dark mode contrast"
```

---

### Task 14: Manual verification

- [ ] **Step 1: Start the backend**

```bash
cd webapp/backend && ADMIN_USERNAME=admin DATA_PATH=../../output/grile.json PDF_PATH=../../pdfs SCREENSHOT_PATH=/tmp/screenshots JWT_SECRET=dev-secret DB_PATH=/tmp/quiz-test.db python -m uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: Start the frontend**

```bash
cd webapp/frontend && npm run dev
```

- [ ] **Step 3: Test the following flows in the browser**

1. Register a user, log in
2. Verify the dashboard does NOT show an admin link
3. Log out, register/log in as the admin username
4. Verify the dashboard shows the "Admin" button
5. Navigate to `/admin` — verify the tabbed layout renders
6. Check the Bug Reports tab (should be empty)
7. Check the Grile.json tab — verify file info shows
8. Check the PDFs tab — verify PDF list shows
9. Upload a PDF, verify it appears in the list
10. Delete a PDF, verify it disappears
11. Start a quiz, click the flag icon on a question card
12. Submit a bug report from the modal
13. Go to admin → Bug Reports tab, verify the report appears
14. Expand the report, verify question context renders
15. Resolve the report, verify it moves to "Resolved"
16. Submit a general feedback report from the dashboard
17. Delete a report from admin
18. Test all of the above in dark mode — check contrast

- [ ] **Step 4: Run all backend tests**

```bash
cd webapp/backend && python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit any fixes found during manual testing**
