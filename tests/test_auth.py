"""Login, logout and the access-control decorators in util.py.

The decorators are plain session checks, not flask-login's, and the cutover
removes flask-login, so these assert the observable session instead of
current_user."""
import pytest

from tests.conftest import login
from tests.seed import PASSWORD


def session_user(client):
    with client.session_transaction() as s:
        return s.get("user")


def test_login_page_renders(client):
    assert client.get("/auth/login").status_code == 200


def test_login_sets_session(client):
    r = login(client, "alice")
    assert r.status_code == 302
    u = session_user(client)
    assert u["username"] == "alice"
    assert u["email"] == "alice@example.test"
    assert u["email_verified"] is True


def test_login_by_email_case_insensitive(client):
    assert login(client, "ALICE@example.test").status_code == 302
    assert session_user(client)["username"] == "alice"


@pytest.mark.parametrize("username,password", [
    ("alice", "wrong"), ("nobody", PASSWORD)])
def test_login_rejects_bad_credentials(client, username, password):
    r = login(client, username, password)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/auth/login")
    assert session_user(client) is None


def test_login_sets_loggedin_cookie(client):
    r = login(client, "alice")
    assert any(c.startswith("loggedin=") for c in r.headers.getlist("Set-Cookie"))


# remember-me differs by design: master uses flask-login's remember_token
# cookie, the cutover (no flask-login) makes the Flask session permanent.
@pytest.mark.legacy
def test_remember_me_sets_remember_cookie(client):
    r = login(client, "alice", remember_me="y")
    assert any(c.startswith("remember_token=") for c in r.headers.getlist("Set-Cookie"))


@pytest.mark.ytac
def test_remember_me_makes_session_permanent(client):
    login(client, "alice", remember_me="y")
    with client.session_transaction() as s:
        assert s.permanent is True


def test_no_remember_me_is_not_permanent(client):
    login(client, "alice")
    with client.session_transaction() as s:
        assert s.permanent is False


def test_unverified_login_sends_confirmation_mail(client, outbox):
    login(client, "newbie")
    assert session_user(client)["email_verified"] is False
    assert len(outbox) == 1


def test_logout_clears_session_and_cookie(user_client):
    r = user_client.get("/auth/logout")
    assert r.status_code == 302
    assert session_user(user_client) is None
    assert any(c.startswith("loggedin=;") for c in r.headers.getlist("Set-Cookie"))


def test_logout_without_login_is_harmless(client):
    assert client.get("/auth/logout").status_code == 302


def test_login_page_redirects_when_logged_in(user_client):
    assert user_client.get("/auth/login").status_code == 302


# login_required redirects anonymous users to the front page, it does not 401
@pytest.mark.parametrize("path", [
    "/playlist/create", "/settings/update_user", "/auth/delete"])
def test_login_required_redirects_anonymous(client, path):
    r = client.get(path)
    assert r.status_code == 302
    assert r.headers["Location"] in ("/", "http://altcensored.com/",
                                     "https://altcensored.com/")


@pytest.mark.parametrize("path", [
    "/playlist/create", "/settings/update_user"])
def test_login_required_allows_user(user_client, path):
    assert user_client.get(path).status_code == 200


def test_admin_gate_blocks_regular_user(user_client):
    r = user_client.get("/admin/")
    assert r.status_code == 302


def test_admin_gate_allows_admin(admin_client):
    assert admin_client.get("/admin/").status_code in (200, 302)


def test_reset_request_unknown_user_does_not_leak(client, outbox):
    r = client.post("/auth/reset_password_request", data=dict(identity="nobody"))
    assert r.status_code == 302
    assert outbox == []


def test_reset_request_known_user_sends_mail(client, outbox):
    client.post("/auth/reset_password_request", data=dict(identity="alice"))
    assert len(outbox) == 1


def test_reset_password_bad_token(client):
    assert client.get("/auth/reset_password/garbage").status_code == 302


def test_confirm_email_bad_token(client):
    assert client.get("/auth/confirm_email/garbage").status_code == 302


@pytest.mark.writes
def test_confirm_email_verifies_user(client, engine):
    from sqlalchemy import text
    from alt2.services.email import generate_confirmation_token
    token = generate_confirmation_token("newbie@example.test")
    assert client.get(f"/auth/confirm_email/{token}").status_code == 302
    with engine.connect() as c:
        ok = c.execute(text("select email_verified from altcen_user "
                            "where username='newbie'")).scalar()
    assert ok is True


@pytest.mark.writes
def test_reset_password_changes_password(client, engine):
    from alt2.models import User
    from alt2.database import db_session
    with client.application.app_context():
        user = db_session.query(User).filter_by(username="alice").one()
        token = user.get_reset_password_token()
    r = client.post(f"/auth/reset_password/{token}",
                    data=dict(password="new-pass-123", password2="new-pass-123"))
    assert r.status_code == 302
    assert login(client, "alice", "new-pass-123").status_code == 302
    assert session_user(client) is not None


# --- registration ------------------------------------------------------------------
# Cloudflare Turnstile is stubbed where routes.py looks it up; the real check is a
# network call and stays on the manual checklist in README.md.

# example.com, not .test: the Email() validator rejects reserved test TLDs
NEW = dict(username="carol", email="carol@example.com",
           password="correct horse", password2="correct horse")


@pytest.fixture()
def turnstile(monkeypatch):
    """Stub verify_turnstile_token; .result is what Cloudflare 'answers', .calls records
    the (token, secret) pairs it was asked about."""
    class Stub:
        result = {"success": True}
        calls = []
    stub = Stub()
    stub.calls = []

    def fake(token, secret):
        stub.calls.append((token, secret))
        return stub.result
    monkeypatch.setattr("alt2.auth.routes.verify_turnstile_token", fake)
    return stub


def register(client, **overrides):
    client.get("/auth/register")   # renders a page, which fills session['navtabs']
    data = {**NEW, "cf-turnstile-response": "tok123", **overrides}
    return client.post("/auth/register", data=data)


def users_named(sql, name):
    return sql("select username, email, email_verified from altcen_user where username=:n", n=name)


def test_register_page_renders(client):
    assert client.get("/auth/register").status_code == 200


@pytest.mark.writes
def test_register_creates_unverified_user_and_sends_welcome_mail(client, turnstile, sql, outbox):
    r = register(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/auth/login")
    assert users_named(sql, "carol") == [("carol", "carol@example.com", False)]
    assert len(outbox) == 1 and outbox[0][1]["recipients"] == ["carol@example.com"]
    # Cloudflare was asked about the token the browser posted
    assert turnstile.calls and turnstile.calls[0][0] == "tok123"


@pytest.mark.writes
def test_registered_password_works_for_login(client, turnstile):
    register(client)
    login(client, "carol", password="correct horse")
    assert session_user(client)["username"] == "carol"


@pytest.mark.writes
def test_register_fails_when_turnstile_fails(client, turnstile, sql, outbox):
    turnstile.result = {"success": False}
    r = register(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    assert users_named(sql, "carol") == []
    assert outbox == []


@pytest.mark.writes
@pytest.mark.parametrize("override", [
    dict(username="alice"),                      # taken
    dict(password2="something else"),            # passwords differ
    dict(email="not-an-email"),
    dict(username="")])
def test_register_rejects_bad_input(client, turnstile, sql, outbox, override):
    before = sql("select count(*) from altcen_user")
    r = register(client, **override)
    assert r.status_code == 200            # the form is shown again
    assert sql("select count(*) from altcen_user") == before
    assert outbox == []
    assert turnstile.calls == []           # no Cloudflare call for an invalid form


@pytest.mark.writes
def test_register_rejects_an_email_that_is_taken(client, turnstile, sql, outbox):
    register(client)
    r = register(client, username="dave")
    assert r.status_code == 200
    assert users_named(sql, "dave") == []
    assert len(outbox) == 1                # only carol's welcome mail


def test_logged_in_user_is_redirected_from_register(user_client):
    r = user_client.get("/auth/register")
    assert r.status_code == 302 and not r.headers["Location"].endswith("/auth/register")
