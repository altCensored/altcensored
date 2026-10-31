"""The CSP must allow every origin the page itself loads.

Browsers enforce the policy, the test client does not, so a page can ship a
script, frame or stylesheet its own CSP blocks and every other test still passes
(Turnstile's iframe was blocked that way for months). This reads each page's HTML
and checks what it loads against the policy the same response sends.

Widgets that build their frames at runtime never show up in static HTML, so
KNOWN_WIDGETS lists the origins they need for a marker class."""
from html.parser import HTMLParser
from urllib.parse import urlsplit

import pytest

PAGES = ["/", "/about/", "/auth/login", "/auth/register", "/playlist/",
         "/watch?v=vid_ia_00002"]

# marker CSS class -> (directive, origin) the runtime widget needs
KNOWN_WIDGETS = {
    "cf-turnstile": ("frame-src", "https://challenges.cloudflare.com"),
}

SELF_HOST = "altcensored.com"


def parse_csp(header):
    policy = {}
    for part in header.split(";"):
        words = part.split()
        if words:
            policy[words[0]] = words[1:]
    return policy


def sources_for(policy, directive):
    return policy.get(directive, policy.get("default-src", []))


def allowed(url, sources):
    if url.startswith("data:"):
        return "data:" in sources
    u = urlsplit(url)
    if not u.netloc:                       # relative URL: same origin
        return "'self'" in sources or "*" in sources
    host = u.hostname
    for s in sources:
        if s == "*":
            return True
        if s == "'self'" and host == SELF_HOST:
            return True
        if s.startswith("*.") and host.endswith(s[1:]):
            return True
        if s == host:
            return True
    return False


class Loads(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.refs.append(("script-src", a["src"]))
        elif tag == "iframe" and a.get("src"):
            self.refs.append(("frame-src", a["src"]))
        elif tag == "link" and "stylesheet" in (a.get("rel") or "") and a.get("href"):
            self.refs.append(("style-src", a["href"]))
        elif tag == "img" and a.get("src"):
            self.refs.append(("img-src", a["src"]))
        elif tag in ("video", "audio", "source") and a.get("src"):
            self.refs.append(("media-src", a["src"]))
        for cls in (a.get("class") or "").split():
            if cls in KNOWN_WIDGETS:
                directive, origin = KNOWN_WIDGETS[cls]
                self.refs.append((directive, origin))


def violations(html, csp_header):
    policy = parse_csp(csp_header)
    parser = Loads()
    parser.feed(html)
    return sorted({(d, u) for d, u in parser.refs
                   if not allowed(u, sources_for(policy, d))})


@pytest.mark.parametrize("path", PAGES)
def test_page_loads_only_what_its_csp_allows(client, monkeypatch, path):
    import alt2.video
    monkeypatch.setattr(alt2.video, "get_ia_item", lambda vid: "https://ia.test/x")
    r = client.get(path)
    assert r.status_code == 200
    found = violations(r.get_data(as_text=True), r.headers["Content-Security-Policy"])
    assert found == [], f"{path} loads origins its own CSP blocks: {found}"


def test_the_check_would_have_caught_the_turnstile_regression(client):
    # the policy as shipped from 314a60e until challenges.cloudflare.com was added
    old = ("default-src 'self' altcensored.com *.altcensored.com; "
           "script-src 'self' *.cloudflare.com *.altcensored.com; "
           "frame-src 'self' altcensored.com *.altcensored.com archive.org *.archive.org")
    html = client.get("/auth/register").get_data(as_text=True)
    assert ("frame-src", "https://challenges.cloudflare.com") in violations(html, old)
