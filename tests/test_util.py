"""Pure helpers in alt2.util: loggedin cookie signing and locale mapping."""
import time


def test_loggedin_cookie_roundtrip(app):
    from alt2 import util
    assert util.loggedin_cookie_valid(util.make_loggedin_cookie())


def test_loggedin_cookie_rejects_tampering(app):
    from alt2 import util
    expires, _, sig = util.make_loggedin_cookie().partition(".")
    assert not util.loggedin_cookie_valid(f"{int(expires) + 1}.{sig}")
    assert not util.loggedin_cookie_valid(f"{expires}.{sig[::-1]}")
    assert not util.loggedin_cookie_valid("")
    assert not util.loggedin_cookie_valid("a" * 64)       # old unsigned format


def test_loggedin_cookie_rejects_expired(app):
    from alt2 import util
    past = int(time.time()) - 10
    assert not util.loggedin_cookie_valid(f"{past}.{util._loggedin_sig(past)}")


def test_swedish_uses_legacy_se_column(app):
    from alt2 import util
    from alt2.models import Translation
    assert util.translation_column("sv") is Translation.se
    assert util.translation_column("de") is Translation.de
