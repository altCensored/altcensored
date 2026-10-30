"""Admin views. Every shell-out is recorded by the autouse ``shell`` fixture
and never run; mass_email and the bounce/email-list uploads write files and
send mail, so only their access gate is covered here."""
import json

import pytest

from tests import schema
from tests.conftest import flashes

GET_ROUTES = [
    "/admin/", "/admin/channel_table", "/admin/channel_data_all",
    "/admin/video_table", "/admin/video_data", "/admin/channel_table_new",
    "/admin/channel_table_new_data", "/admin/add_channel",
    "/admin/update_channel", "/admin/enable_channel", "/admin/disable_channel",
    "/admin/resync_channel", "/admin/remove_channel", "/admin/mirror_channel",
    "/admin/status_channel", "/admin/update_video", "/admin/system_commands",
    "/admin/scraper_status", "/admin/mass_email", "/admin/update_bounce",
    "/admin/add_email_list",
]


@pytest.mark.parametrize("path", GET_ROUTES)
def test_admin_routes_redirect_anonymous(client, shell, path):
    r = client.get(path)
    assert r.status_code == 302
    assert shell == []


@pytest.mark.parametrize("path", GET_ROUTES)
def test_admin_routes_redirect_regular_user(user_client, shell, path):
    assert user_client.get(path).status_code == 302
    assert shell == []


# data endpoints need DataTables parameters; page routes just render
PAGES = ["/admin/", "/admin/channel_table", "/admin/video_table",
         "/admin/channel_table_new", "/admin/add_channel",
         "/admin/update_channel", "/admin/enable_channel",
         "/admin/disable_channel", "/admin/resync_channel",
         "/admin/remove_channel", "/admin/mirror_channel",
         "/admin/status_channel", "/admin/update_video",
         "/admin/system_commands", "/admin/mass_email",
         "/admin/update_bounce", "/admin/add_email_list"]


@pytest.mark.parametrize("path", PAGES)
def test_admin_pages_render_for_admin(admin_client, shell, path):
    assert admin_client.get(path).status_code == 200
    assert shell == []


def test_scraper_status_only_records_commands(admin_client, shell):
    assert admin_client.get("/admin/scraper_status").status_code == 200
    assert len(shell) > 5 and all(isinstance(c, str) for c in shell)


def test_channel_data_all_lists_channels(admin_client):
    r = admin_client.get("/admin/channel_data_all?draw=1&start=0&length=10")
    assert r.status_code == 200
    assert int(r.get_json()["recordsTotal"]) == 2


def test_video_data_lists_videos(admin_client):
    r = admin_client.get("/admin/video_data?ytc_id=all&draw=1&start=0&length=10")
    assert r.status_code == 200
    # master lists the channel rows as well (Entity); the cutover fixes that
    assert int(r.get_json()["recordsTotal"]) == schema.VIDEO_DATA_ALL


def test_channel_table_new_data_hides_deleted(admin_client):
    r = admin_client.get("/admin/channel_table_new_data")
    assert r.status_code == 200
    assert "Alpha Channel" in r.get_data(as_text=True)
    assert "Beta Channel" not in r.get_data(as_text=True)


# --- writes through the database ---------------------------------------------

def flags(sql, channel):
    return sql(f"select {schema.CHANNEL_FLAGS} from source "
               f"where {schema.CHANNEL_WHERE}", c=channel)[0]


def test_seed_flags_baseline(sql):
    assert flags(sql, schema.ALPHA) == (True, False, False, False)


@pytest.mark.writes
def test_update_channel_sets_archive_type_and_delta(admin_client, sql):
    r = admin_client.post("/admin/update_channel", data=dict(
        channel_id=schema.ALPHA, delta="3", archive_type="partial",
        deleted="", viewcount="", subscribercount="", deleteddate=""))
    assert r.status_code == 302
    assert flags(sql, schema.ALPHA) == (False, True, False, False)
    assert sql(f"select delta from source where {schema.CHANNEL_WHERE}",
               c=schema.ALPHA)[0][0].days == 3
    assert ("success", f"{schema.ALPHA} Updated") in flashes(admin_client)


@pytest.mark.writes
@pytest.mark.parametrize("archive_type,expected", [
    ("none", (False, False, False)), ("full", (True, False, False)),
    ("latest", (False, False, True))])
def test_update_channel_archive_types(admin_client, sql, archive_type, expected):
    admin_client.post("/admin/update_channel", data=dict(
        channel_id=schema.ALPHA, delta="", archive_type=archive_type,
        deleted="", viewcount="", subscribercount="", deleteddate=""))
    assert flags(sql, schema.ALPHA)[:3] == expected


@pytest.mark.writes
def test_update_channel_undelete_clears_flag(admin_client, sql):
    admin_client.post("/admin/update_channel", data=dict(
        channel_id=schema.BETA, delta="", archive_type="",
        deleted="False", viewcount="", subscribercount="", deleteddate=""))
    assert flags(sql, schema.BETA)[3] is False


@pytest.mark.writes
def test_update_channel_unknown_id_reports_failure(admin_client):
    r = admin_client.post("/admin/update_channel", data=dict(
        channel_id="UCzzzzzzzzzzzzzzzzzzzzzz", delta="", archive_type="",
        deleted="", viewcount="", subscribercount="", deleteddate=""),
        follow_redirects=True)
    assert "NOT Updated" in r.get_data(as_text=True)


@pytest.mark.writes
def test_update_video_toggles_allow_and_deleted(admin_client, sql):
    q = (f"select allow, {schema.VIDEO_DELETED} from {schema.VIDEO_TABLE} "
         "where extractor_data='vid_live_0001'")
    assert sql(q) == [(True, False)]
    admin_client.post("/admin/update_video", data=dict(
        video_id="vid_live_0001", allow_action="False", deleted_action="True"))
    assert sql(q) == [(False, True)]


@pytest.mark.writes
def test_update_video_unknown_id_reports_failure(admin_client):
    r = admin_client.post("/admin/update_video", data=dict(
        video_id="nope_nope_00", allow_action="False", deleted_action=""))
    assert "allow NOT toggled" in r.get_data(as_text=True)


@pytest.mark.writes
def test_inline_table_update_via_json(admin_client, sql):
    pk = sql(f"select id from source where {schema.CHANNEL_WHERE}",
             c=schema.ALPHA)[0][0]
    r = admin_client.post("/admin/channel_table_new_data", json={
        "id": pk, "allow": "False", "delta": "9",
        schema.CHANNEL_POST_ARCHIVE: "False",
        schema.CHANNEL_POST_TITLE: "Renamed channel"})
    assert r.status_code == 204
    assert flags(sql, schema.ALPHA)[0] is False
    assert sql(f"select delta, {schema.CHANNEL_TITLE_COL} from source "
               f"where {schema.CHANNEL_WHERE}", c=schema.ALPHA)[0][1] \
        == "Renamed channel"


def test_inline_table_update_requires_id(admin_client):
    assert admin_client.post("/admin/channel_table_new_data",
                             json={"allow": "False"}).status_code == 400


# --- shell dispatch (recorded, never run) -------------------------------------

@pytest.mark.parametrize("route,verb", [
    ("enable_channel", "enable"), ("resync_channel", "resync"),
    ("remove_channel", "remove"), ("add_channel", schema.ADD_VERB)])
def test_channel_commands_are_dispatched(admin_client, shell, route, verb):
    admin_client.post(f"/admin/{route}", data=dict(
        channel_id=schema.ALPHA, delta="5"))
    assert len(shell) == 1
    assert verb in shell[0] and schema.channel_ref(schema.ALPHA) in shell[0]


@pytest.mark.parametrize("route", [
    "enable_channel", "resync_channel", "remove_channel", "add_channel",
    "disable_channel", "status_channel", "mirror_channel"])
def test_channel_commands_reject_bad_id(admin_client, shell, route):
    r = admin_client.post(f"/admin/{route}", data=dict(
        channel_id="x; rm -rf /", delta="5"))
    assert shell == []
    assert "Invalid channel ID" in r.get_data(as_text=True)


def test_add_channel_rejects_bad_delta(admin_client, shell):
    admin_client.post("/admin/add_channel", data=dict(
        channel_id=schema.ALPHA, delta="-1"))
    assert shell == []


@pytest.mark.parametrize("form", [
    dict(cmd_name="rm"),
    dict(cmd_name="systemctl", action_name="stop;reboot", subsys_name="nginx"),
    dict(cmd_name="systemctl", action_name="restart", subsys_name="sshd"),
    dict(cmd_name="find", param_name="a;b")])
def test_system_commands_rejects_unlisted(admin_client, shell, form):
    data = dict(sys_name="", cmd_name="", subsys_name="", action_name="",
                param_name="", find_run="false")
    data.update(form)
    admin_client.post("/admin/system_commands", data=data)
    assert shell == []


# --- public endpoints in the admin blueprint -----------------------------------

def test_unsubscribe_bad_token(client):
    assert client.get("/admin/confirm/garbage").status_code == 302


@pytest.mark.writes
def test_unsubscribe_flow(client, sql):
    from alt2.services.email import generate_confirmation_token
    token = generate_confirmation_token("alice@example.test")
    assert client.get(f"/admin/confirm/{token}").status_code == 200
    client.post(f"/admin/confirm/{token}", data=dict(submitvalue="no"))
    assert sql("select email_subscribed from altcen_user "
               "where username='alice'") == [(True,)]
    client.post(f"/admin/confirm/{token}", data=dict(submitvalue="yes"))
    assert sql("select email_subscribed, email_action from altcen_user "
               "where username='alice'") == [(False, "altc_unsub")]


@pytest.mark.parametrize("path", ["/admin/aws_bounce", "/admin/aws_complaint"])
def test_sns_endpoints_reject_unsigned(client, path):
    r = client.post(path, data=json.dumps(dict(
        Type="Notification", Message="{}", SigningCertURL="https://evil.test/x.pem")))
    assert r.status_code == 400
    assert client.post(path, data="not json").status_code == 200
