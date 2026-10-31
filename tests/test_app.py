"""App-wide behaviour: locale choice, error pages, security headers, the
loggedin-cookie refresh hook and the small helpers in util.py."""
import time

import pytest

from tests.conftest import login


def session_value(client, key):
    with client.session_transaction() as s:
        return s.get(key)


# --- locale ------------------------------------------------------------------------

@pytest.mark.parametrize("header,expected", [
    ("de", "de"), ("fr;q=0.9,de;q=0.8", "fr"), ("sv-SE,sv;q=0.9", "sv"),
    ("ja", "en"), ("", "en")])
def test_locale_comes_from_accept_language(client, header, expected):
    client.get("/", headers={"Accept-Language": header})
    assert session_value(client, "locale") == expected


def test_locale_is_kept_once_chosen(client):
    client.get("/", headers={"Accept-Language": "de"})
    client.get("/", headers={"Accept-Language": "fr"})
    assert session_value(client, "locale") == "de"


def test_legacy_swedish_locale_is_read_as_sv(client):
    client.get("/")
    with client.session_transaction() as s:
        s["locale"] = "se"
    client.get("/")
    assert session_value(client, "locale") == "sv"


def test_navbar_is_translated(client):
    body = client.get("/", headers={"Accept-Language": "de"}).get_data(as_text=True)
    assert "kanal" in body


@pytest.mark.parametrize("locale", ["en", "de", "es", "fr", "pt", "nl", "it", "sv"])
def test_every_supported_locale_renders_main_pages(client, locale):
    client.get("/", headers={"Accept-Language": locale})
    for path in ("/", "/channel/", "/about/", "/auth/login"):
        assert client.get(path).status_code == 200


# --- error pages -------------------------------------------------------------------

def test_404_uses_the_site_page(client):
    r = client.get("/no/such/page")
    assert r.status_code == 404
    assert "<html" in r.get_data(as_text=True).lower()


def test_400_uses_the_site_page(user_client):
    r = user_client.post("/playlist/add_video_playlist", data=dict(
        v="bad id!", playlist_title="x"))
    assert r.status_code == 400
    assert "<html" in r.get_data(as_text=True).lower()


def test_500_uses_the_site_page(client):
    client.get("/settings/update_site")
    r = client.post("/settings/update_site", data=dict(
        navtab1_value="video", navtab2_value="channel", navtab3_value="playlist",
        theme="light", autoplay="oops", playnext="True", looplist="True",
        locale="en"))
    assert r.status_code == 500
    assert "<html" in r.get_data(as_text=True).lower()


def test_403_for_someone_elses_playlist(client, sql):
    login(client, "admin")
    pid = sql("select id from playlist")[0][0]
    assert client.get(f"/playlist/edit/{pid}").status_code == 403


# --- transport and headers -----------------------------------------------------------

def test_http_requests_are_redirected_to_https(app):
    r = app.test_client().get("/", headers={"Host": "altcensored.com"})
    assert r.status_code == 302
    assert r.headers["Location"].startswith("https://")


def test_security_headers_are_present(client):
    h = client.get("/").headers
    assert "Content-Security-Policy" in h
    assert h["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" in h


def test_csp_nonce_matches_inline_scripts(client):
    r = client.get("/")
    csp = r.headers["Content-Security-Policy"]
    nonce = csp.split("'nonce-")[1].split("'")[0]
    assert f'nonce="{nonce}"' in r.get_data(as_text=True)


def test_session_cookie_flags(client):
    r = client.get("/")
    cookie = next(c for c in r.headers.getlist("Set-Cookie")
                  if c.startswith("session="))
    assert "HttpOnly" in cookie and "Secure" in cookie


# --- the loggedin cookie hook ------------------------------------------------------------

def loggedin_set(response):
    return any(c.startswith("loggedin=") for c in response.headers.getlist("Set-Cookie"))


def test_valid_cookie_is_not_reissued(user_client):
    assert not loggedin_set(user_client.get("/about/"))


def test_missing_cookie_is_reissued_on_html(user_client):
    user_client.delete_cookie("loggedin")
    assert loggedin_set(user_client.get("/about/"))


def test_tampered_cookie_is_reissued(user_client):
    user_client.set_cookie("loggedin", "9999999999.AAAA")
    assert loggedin_set(user_client.get("/about/"))


def test_cookie_close_to_expiry_is_reissued(user_client):
    from alt2 import util
    soon = int(time.time()) + 3600            # under the 12h refresh window
    user_client.set_cookie("loggedin", f"{soon}.{util._loggedin_sig(soon)}")
    assert loggedin_set(user_client.get("/about/"))


def test_non_html_responses_never_get_the_cookie(user_client):
    user_client.delete_cookie("loggedin")
    r = user_client.get("/api/video-sources/vid_ac_00003")
    assert r.mimetype == "application/json" or r.status_code != 200
    assert not loggedin_set(r)


def test_anonymous_visitors_never_get_the_cookie(client):
    assert not loggedin_set(client.get("/about/"))


# --- util helpers -----------------------------------------------------------------------

@pytest.mark.parametrize("value,ok", [
    ("dQw4w9WgXcQ", True), ("vid_ia_00002", True), ("a-b_c", True),
    ("", False), (None, False), (12, False), ("bad id!", False),
    ("x" * 25, False), ("a/b", False)])
def test_valid_video_id(value, ok):
    from alt2.util import valid_video_id
    assert valid_video_id(value) is ok


def test_str_to_bool():
    from alt2.util import str_to_bool
    assert str_to_bool("True") is True and str_to_bool("False") is False
    with pytest.raises(ValueError):
        str_to_bool("true")


@pytest.mark.parametrize("raw,expected", [
    ("/watch?v=abc", "/watch?v=abc"),
    ("https://altcensored.com/channel/?x=1", "/channel/?x=1"),
    ("http://altcensored.com", "/"),
    ("https://evil.test/steal", "/"),
    ("//evil.test/x", "/"),
    ("javascript:alert(1)", "/"),
    ("/\\evil.test", "/"),
    # urlsplit leaves these with no host and a path starting "//", which a browser
    # would follow as a protocol-relative redirect to another site
    ("////evil.test", "/"),
    ("http:////evil.test/x", "/"),
    ("", "/")])
def test_safe_next_only_returns_local_paths(app, raw, expected):
    from alt2.util import safe_next
    with app.test_request_context("/", base_url="https://altcensored.com",
                                  query_string={"original_url": raw}):
        assert safe_next() == expected


@pytest.fixture()
def flt(app):
    return app.jinja_env.filters


# the "or 'PT0S'" fallback never fires because 'PT' is truthy: 0 gives invalid 'PT'
ZERO_BUG = pytest.mark.xfail(strict=True, reason="iso8601duration(0) returns 'PT'")


@pytest.mark.parametrize("seconds,expected", [
    (3725, "PT1H2M5S"), pytest.param(0, "PT0S", marks=ZERO_BUG),
    (59, "PT59S"), ("x", ""), (None, "")])
def test_iso8601duration_filter(flt, seconds, expected):
    assert flt["iso8601duration"](seconds) == expected


@pytest.mark.parametrize("views,expected", [
    (None, 0), (999, 999), (1000, "1.0K"), (3725, "3.7K"), (15000, "15K"),
    (2_500_000, "2.5M"), (45_000_000, "45M"), (3_200_000_000, "3.2B")])
def test_viewdisplay_filter(flt, views, expected):
    assert flt["viewdisplay"](views) == expected


# lstrip("0") also eats the minutes digit: 5 seconds shows as ':05'
LSTRIP_BUG = pytest.mark.xfail(strict=True, reason="hourminsec(5) returns ':05'")


@pytest.mark.parametrize("secs,expected", [
    pytest.param(5, "0:05", marks=LSTRIP_BUG), (65, "1:05"),
    (600, "10:00"), (3600, "1:00:00"), (3725, "1:02:05")])
def test_hourminsec_filter(flt, secs, expected):
    assert flt["hourminsec"](secs) == expected


def test_commafy_and_spaceplus_filters(flt):
    assert flt["commafy"](1234567) == "1,234,567" and flt["commafy"](None) == 0
    assert flt["spaceplus"]("a b c") == "a+b+c"


def test_ia_fname_filter_matches_archive_org_naming(flt):
    assert flt["ia_fname"]("Café: it’s great!") == "Cafe_-_it_s_great"


# linkify cleans user-supplied descriptions: it must keep links and drop script
def test_linkify_turns_urls_into_links(flt):
    out = flt["linkify"]("see https://example.com/page now")
    assert 'href="https://example.com/page"' in out


@pytest.mark.parametrize("dirty", [
    "<script>alert(1)</script>hi", '<img src=x onerror="alert(1)">',
    '<a href="javascript:alert(1)" onclick="x()">go</a>'])
def test_linkify_strips_scripts_and_handlers(flt, dirty):
    out = flt["linkify"](dirty)
    assert "<script" not in out and "onerror" not in out
    assert "onclick" not in out and "javascript:" not in out


def test_nl2br_escapes_html_and_breaks_lines(flt, app):
    from jinja2 import Environment
    tpl = app.jinja_env.from_string("{{ t|nl2br }}")
    out = tpl.render(t="a<b>\nc\n\nd")
    assert "&lt;b&gt;" in out and "<br>" in out and out.count("<p>") == 2
