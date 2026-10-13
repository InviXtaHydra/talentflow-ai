from app.integrations.email.sender import outbox
from tests.conftest import PASSWORD, Api, register


def test_register_login_me_logout():
    api = register("candidate", email="Anna@Example.com")
    assert api.user["email"] == "anna@example.com"
    assert api.user["role"] == "candidate"
    assert api.user["email_verified"] is False
    assert api.get("/auth/me").status_code == 200

    assert api.post("/auth/logout").status_code == 200
    assert api.get("/auth/me").status_code == 401

    fresh = Api()
    assert fresh.post("/auth/login", {"email": "anna@example.com", "password": "wrong-password-1"}).status_code == 401
    assert fresh.post("/auth/login", {"email": "anna@example.com", "password": PASSWORD}).status_code == 200
    assert fresh.get("/auth/me").json()["full_name"] == "Test Gebruiker"


def test_session_cookie_is_httponly_and_password_is_hashed(db):
    from app.models.entities import User

    api = Api()
    response = api.post("/auth/register", {"email": "b@example.com", "password": PASSWORD, "full_name": "Bo Bo", "accept_terms": True})
    assert response.status_code == 201
    cookie = response.headers.get_list("set-cookie")
    assert any("tf_session=" in c and "HttpOnly" in c for c in cookie)
    stored = db.query(User).filter(User.email == "b@example.com").one()
    assert stored.password_hash.startswith("$argon2id$")
    assert PASSWORD not in stored.password_hash


def test_role_cannot_be_chosen_freely():
    api = Api()
    response = api.post(
        "/auth/register",
        {"email": "x@example.com", "password": PASSWORD, "full_name": "Xa Xa", "account_type": "admin", "accept_terms": True},
    )
    assert response.status_code == 422
    response = api.post(
        "/auth/register", {"email": "x@example.com", "password": PASSWORD, "full_name": "Xa Xa", "role": "admin", "accept_terms": True}
    )
    assert response.status_code == 201
    assert response.json()["role"] == "candidate"


def test_duplicate_email_and_weak_password():
    register("candidate", email="dup@example.com")
    api = Api()
    assert (
        api.post(
            "/auth/register", {"email": "dup@example.com", "password": PASSWORD, "full_name": "Do Do", "accept_terms": True}
        ).status_code
        == 409
    )
    assert (
        api.post("/auth/register", {"email": "w@example.com", "password": "short", "full_name": "Wi Wi", "accept_terms": True}).status_code
        == 422
    )
    assert (
        api.post(
            "/auth/register", {"email": "t@example.com", "password": PASSWORD, "full_name": "Ti Ti", "accept_terms": False}
        ).status_code
        == 422
    )


def test_csrf_token_is_required_for_state_changes():
    api = register()
    response = api.client.post("/api/v1/auth/logout")  # no X-CSRF-Token header
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    response = api.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "forged"})
    assert response.status_code == 403


def test_email_verification_flow():
    api = register(email="verify@example.com")
    mail = next(m for m in outbox if m.to == "verify@example.com")
    token = mail.text.split("token=")[1].split()[0]
    assert api.post("/auth/verify-email", {"token": token}).json()["email_verified"] is True
    assert api.post("/auth/verify-email", {"token": token}).status_code == 401  # single use


def test_password_reset_does_not_reveal_accounts_and_works():
    register(email="reset@example.com")
    outbox.clear()
    api = Api()
    known = api.post("/auth/forgot-password", {"email": "reset@example.com"})
    unknown = api.post("/auth/forgot-password", {"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(outbox) == 1
    token = outbox[0].text.split("token=")[1].split()[0]
    assert api.post("/auth/reset-password", {"token": token, "password": "a-brand-new-password"}).status_code == 200
    assert api.post("/auth/login", {"email": "reset@example.com", "password": PASSWORD}).status_code == 401
    assert api.post("/auth/login", {"email": "reset@example.com", "password": "a-brand-new-password"}).status_code == 200


def test_login_is_rate_limited():
    register(email="rl@example.com")
    api = Api()
    codes = [api.post("/auth/login", {"email": "rl@example.com", "password": "wrong-password-x"}).status_code for _ in range(10)]
    assert codes[:8] == [401] * 8
    assert codes[-1] == 429


def test_change_password_and_sessions():
    api = register(email="cp@example.com")
    other = Api()
    other.post("/auth/login", {"email": "cp@example.com", "password": PASSWORD})
    assert len(api.get("/auth/sessions").json()) == 2
    assert api.post("/auth/change-password", {"current_password": PASSWORD, "new_password": "another-good-password"}).status_code == 200
    assert other.get("/auth/me").status_code == 401  # other device logged out
    assert api.get("/auth/me").status_code == 200
