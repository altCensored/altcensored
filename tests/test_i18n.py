"""Translation catalogs: every string the code asks for is in every locale,
translated, and the compiled .mo files match the .po sources.

Run `pybabel extract / update / compile` (see CLAUDE.md) when these fail."""
import ast
import re
from pathlib import Path

import pytest
from babel.messages.mofile import read_mo
from babel.messages.pofile import read_po

ROOT = Path(__file__).resolve().parent.parent / "alt2"
LOCALES = ["de", "es", "fr", "it", "nl", "pt", "sv"]
CALLS = {"_", "_l", "gettext", "lazy_gettext"}


def source_strings():
    """Literal first arguments of gettext-style calls in .py files and templates."""
    found = {}
    for py in ROOT.rglob("*.py"):
        if "translations" in py.parts:
            continue
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and node.args:
                f = node.func
                name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
                arg = node.args[0]
                if (name in CALLS and isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)):
                    found.setdefault(arg.value, f"{py.relative_to(ROOT)}:{node.lineno}")
    pattern = re.compile(r"""\b_l?\(\s*(['"])(.+?)\1\s*[,)]""")
    for html in ROOT.rglob("*.html"):
        for m in pattern.finditer(html.read_text(encoding="utf-8")):
            found.setdefault(m.group(2), str(html.relative_to(ROOT)))
    return found


def catalog(locale):
    with open(ROOT / "translations" / locale / "LC_MESSAGES" / "messages.po", "rb") as f:
        return read_po(f)


def test_the_scan_finds_the_strings_it_should():
    strings = source_strings()
    assert len(strings) > 40
    assert "Log In" in strings


# 31 flash messages (history, watch later, playlist errors, unsubscribe, ...) were
# added to the code but never extracted with pybabel, so every non-English
# visitor sees them in English. strict=True turns this green-to-red the moment
# they are translated, as a reminder to delete the marker.
@pytest.mark.xfail(strict=True, reason="31 strings used in code are in no catalog")
@pytest.mark.parametrize("locale", LOCALES)
def test_every_string_in_the_source_is_in_the_catalog(locale):
    cat = catalog(locale)
    missing = {s: where for s, where in source_strings().items()
               if s not in cat or not cat[s].string}
    assert not missing, f"not translated for {locale}: {missing}"


@pytest.mark.parametrize("locale", LOCALES)
def test_catalog_has_no_empty_or_fuzzy_entries(locale):
    cat = catalog(locale)
    empty = [m.id for m in cat if m.id and not m.string]
    fuzzy = [m.id for m in cat if m.fuzzy]
    assert not empty and not fuzzy, f"{locale}: empty={empty} fuzzy={fuzzy}"


@pytest.mark.parametrize("locale", LOCALES)
def test_compiled_catalog_matches_the_po_file(locale):
    po = {m.id: m.string for m in catalog(locale) if m.id and m.string}
    with open(ROOT / "translations" / locale / "LC_MESSAGES" / "messages.mo", "rb") as f:
        mo = {m.id: m.string for m in read_mo(f) if m.id and m.string}
    assert po == mo, "messages.mo is stale: run pybabel compile"


@pytest.mark.parametrize("locale", LOCALES)
def test_placeholders_survive_translation(locale):
    """A translator dropping %(name)s or {0} breaks the page at render time."""
    for m in catalog(locale):
        if not (m.id and isinstance(m.id, str) and m.string):
            continue
        want = sorted(re.findall(r"%\(\w+\)[sd]|\{\w*\}", m.id))
        got = sorted(re.findall(r"%\(\w+\)[sd]|\{\w*\}", m.string))
        assert want == got, f"{locale}: {m.id!r} -> {m.string!r}"
