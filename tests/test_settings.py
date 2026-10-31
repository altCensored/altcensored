"""Site settings (anonymous, session only) and user settings (persisted)."""
import pytest

from tests.conftest import flashes, login


def site_form(**over):
    data = dict(navtab1_value="video", navtab2_value="channel",
                navtab3_value="playlist", theme="light", autoplay="True",
                playnext="True", looplist="True", locale="en")
    data.update(over)
    return data


def user_form(**over):
    data = dict(email="alice@example.test", username="alice", description="",
                public="False", email_subscribed="True", featured_playlist="")
    data.update(over)
    return data


@pytest.fixture(autouse=True)
def no_email_side_effects(monkeypatch):
    """validate_email may query DNS and send_confirm_email goes to AWS."""
    import alt2.settings
    sent = []
    monkeypatch.setattr(alt2.settings, "validate_user_email", lambda e: None)
    monkeypatch.setattr(alt2.settings, "send_confirm_email", sent.append)
    return sent


def test_settings_index_and_site_page_render(client):
    assert client.get("/settings/").status_code == 200
    assert client.get("/settings/update_site").status_code == 200


def test_update_site_sets_session_for_anonymous(client):
    client.get("/settings/update_site")   # the form load creates the session keys
    r = client.post("/settings/update_site",
                    data=site_form(theme="dark", autoplay="False"))
    assert r.status_code == 302
    with client.session_transaction() as s:
        assert s["theme"] == "dark"
        assert s["autoplay"] is False
        assert s["locale"] == "en"


def test_update_site_switches_locale_and_translates_navtabs(client):
    client.get("/settings/update_site")
    client.post("/settings/update_site", data=site_form(locale="de"))
    with client.session_transaction() as s:
        assert s["locale"] == "de"
        assert s["navtabs"]["navtab2"] == "kanal"
        # the index always stores the English key
        assert s["navtabs_index"]["navtab2"] == "channel"


def test_update_site_rejects_unsupported_locale(client):
    assert client.post("/settings/update_site",
                       data=site_form(locale="xx")).status_code == 400


def test_update_site_bad_boolean_is_a_500_not_a_400(client):
    # str_to_bool raises ValueError; nothing turns it into a 400 (known gap)
    client.get("/settings/update_site")
    r = client.post("/settings/update_site", data=site_form(playnext="maybe"))
    assert r.status_code == 500


@pytest.mark.writes
def test_update_site_persists_for_logged_in_user(user_client, sql):
    user_client.post("/settings/update_site",
                     data=site_form(theme="dark", locale="de", autoplay="False"))
    settings, navtabs = sql("select settings, navtabs from altcen_user "
                            "where username='alice'")[0]
    assert settings["theme"] == "dark" and settings["locale"] == "de"
    assert settings["autoplay"] is False
    assert navtabs == ["video", "kanal", "playlist"]


def test_user_settings_require_login(client):
    r = client.post("/settings/update_user", data=user_form())
    assert r.status_code == 302


def test_user_settings_page_lists_public_playlists(user_client):
    r = user_client.get("/settings/update_user")
    assert r.status_code == 200
    assert "Alice list" in r.get_data(as_text=True)


@pytest.mark.writes
def test_update_user_saves_fields_and_session(user_client, sql):
    r = user_client.post("/settings/update_user", data=user_form(
        username="alice2", description="hello", public="True",
        email_subscribed="False"))
    assert r.status_code == 302
    assert sql("select username, description, public, email_subscribed "
               "from altcen_user where email='alice@example.test'") \
        == [("alice2", "hello", True, False)]
    with user_client.session_transaction() as s:
        assert s["user"]["username"] == "alice2"


@pytest.mark.writes
def test_update_user_rejects_taken_username(user_client, sql):
    user_client.post("/settings/update_user", data=user_form(username="ADMIN"))
    assert ("error", "Username exists") in flashes(user_client)
    assert sql("select username from altcen_user where id=2") == [("alice",)]


@pytest.mark.writes
def test_update_user_rejects_taken_email(user_client, sql):
    user_client.post("/settings/update_user",
                     data=user_form(email="admin@example.test"))
    assert ("error", "Email exists") in flashes(user_client)
    assert sql("select email from altcen_user where id=2") \
        == [("alice@example.test",)]


@pytest.mark.writes
def test_update_user_email_change_unverifies_and_mails(
        user_client, sql, no_email_side_effects):
    user_client.post("/settings/update_user",
                     data=user_form(email="alice.new@example.test"))
    assert sql("select email, email_verified from altcen_user where id=2") \
        == [("alice.new@example.test", False)]
    assert no_email_side_effects == ["alice.new@example.test"]


@pytest.mark.writes
def test_confirm_link_in_the_email_change_mail_verifies_the_new_address(
        user_client, sql, monkeypatch):
    # The autouse fixture replaces send_confirm_email; use the real one and capture
    # one level lower (the AWS call), so the mailed link is what gets followed.
    import re
    import alt2.settings
    import alt2.services.email as mail
    mails = []
    monkeypatch.setattr(mail, "send_all_mass_email",
                        lambda *a, **k: mails.append((a, k)))
    monkeypatch.setattr(alt2.settings, "send_confirm_email", mail.send_confirm_email)
    user_client.post("/settings/update_user",
                     data=user_form(email="alice.new@example.test"))
    assert mails and mails[0][0][0] == "alice.new@example.test"
    html = mails[0][0][3]
    path = re.search(r"/auth/confirm_email/[^\"'\s<]+", html).group(0)
    assert user_client.get(path).status_code == 302
    assert sql("select email, email_verified from altcen_user where id=2") \
        == [("alice.new@example.test", True)]


@pytest.mark.writes
def test_update_user_rejects_profanity(user_client, sql):
    user_client.post("/settings/update_user", data=user_form(description="fuck"))
    assert ("error", "Profanity forbidden") in flashes(user_client)
    assert sql("select description from altcen_user where id=2") == [("",)]


@pytest.mark.writes
def test_featured_playlist_requires_a_featured_video(user_client, sql):
    user_client.post("/settings/update_user",
                     data=user_form(featured_playlist="Alice list"))
    assert sql("select featured_playlist from altcen_user where id=2") \
        == [(None,)]
    assert any("no featured video" in m for _, m in flashes(user_client))


@pytest.mark.writes
def test_featured_playlist_is_stored_with_video(client, sql):
    from sqlalchemy import text
    with client.application.app_context():
        from alt2.database import db_session
        db_session.execute(text("update playlist set featured_video_id="
                                "'vid_ia_00002'"))
        db_session.commit()
    login(client, "alice")
    client.post("/settings/update_user",
                data=user_form(featured_playlist="Alice list"))
    fp = sql("select featured_playlist from altcen_user where id=2")[0][0]
    assert fp["pl_title"] == "Alice list"
    assert fp["extractor_data"] == "vid_ia_00002"
    # the page that reads it back must still render
    assert client.get("/settings/update_user").status_code == 200
