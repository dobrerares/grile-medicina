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


def test_delete_pdf(client, admin_token):
    import os
    pdf_dir = os.environ["PDF_PATH"]
    with open(os.path.join(pdf_dir, "delete_me.pdf"), "wb") as f:
        f.write(b"%PDF-1.4")
    res = client.delete("/api/admin/pdf/delete_me.pdf", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert not os.path.exists(os.path.join(pdf_dir, "delete_me.pdf"))


def test_delete_pdf_path_traversal(client, admin_token):
    # %2F (URL-encoded slash) gets normalized by Starlette's router before it reaches the handler,
    # resulting in a 404. Test a dotdot pattern that reaches the handler instead.
    res = client.delete("/api/admin/pdf/..secret.txt", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 400
