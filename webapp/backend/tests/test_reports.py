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
    client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {user_token}"},
        data={"category": "app_bug", "description": "Test bug"},
    )
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
