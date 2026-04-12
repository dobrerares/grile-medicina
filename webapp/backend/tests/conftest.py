import os
import json
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set env vars before importing any app modules.
# DB_PATH must be set before database.py is imported since it reads it at module level.
_tmpdir = tempfile.mkdtemp()
_test_db_path = os.path.join(_tmpdir, "test.db")
_test_grile_path = os.path.join(_tmpdir, "grile.json")

os.environ["ADMIN_USERNAME"] = "admin"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["DB_PATH"] = _test_db_path
os.environ["DATA_PATH"] = _test_grile_path

# Write a minimal grile.json so quiz.py doesn't fail at import time
_grile_data = {
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
with open(_test_grile_path, "w") as _f:
    json.dump(_grile_data, _f)

from database import Base, get_db
from main import app
from auth import hash_password
from models import User


@pytest.fixture()
def db_session():
    engine = create_engine(
        f"sqlite:///{_test_db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, tmp_path):
    # Create per-test grile.json (same content, just ensuring clean state)
    grile_path = tmp_path / "grile.json"
    grile_path.write_text(json.dumps(_grile_data))

    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()

    # Patch quiz module to use test data
    import quiz as quiz_service
    quiz_service.DATA_PATH = str(grile_path)
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
