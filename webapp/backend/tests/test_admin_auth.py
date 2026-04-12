def test_me_returns_is_admin_true(client, admin_token):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["is_admin"] is True


def test_me_returns_is_admin_false(client, user_token):
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    assert res.json()["is_admin"] is False
