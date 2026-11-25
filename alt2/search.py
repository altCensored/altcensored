"""Site search on the pg_search (BM25) indexes of the mv_* views.

The user's input is parsed here, as websearch_to_tsquery did before: words are ANDed, "quoted
phrases" match in order, -word excludes and `or` between two items makes either one enough. Each
word may match any of the view's text fields. Typo tolerance (pdb.fuzzy) is only used when the
caller asks for it (the fallback when the exact search finds no videos), and never on an ID field:
the literal tokenizer does not stop pdb.fuzzy, so a fuzzy ID query would match other IDs.
"""
import re
from dataclasses import dataclass, field, replace

from sqlalchemy import text

# (column expression, boost). The boosts keep the old tsvector weights: ts_rank weighs D at half
# of C, and mv_channel, mv_playlist and mv_altcen_user had every field at A.
VIDEO_FIELDS = [("mv_video.title", 1), ("mv_video.description", 1), ("mv_video.source_title", 1),
                ("mv_video.category", 0.5), ("(mv_video.tags::text)", 0.5)]
VIDEO_IDS = ["mv_video.extractor_data", "mv_video.source_extractor_data"]
CHANNEL_FIELDS = [("mv_channel.title", 1), ("mv_channel.description", 1), ("mv_channel.uploader_id", 1)]
CHANNEL_IDS = ["mv_channel.extractor_data"]
PLAYLIST_FIELDS = [("mv_playlist.title", 1), ("mv_playlist.description", 1)]
PLAYLIST_IDS = ["mv_playlist.hashid"]
USER_FIELDS = [("mv_altcen_user.username", 1), ("mv_altcen_user.description", 1)]

_TOKEN = re.compile(r'(-?)"([^"]*)"?|(\S+)')
_EDGE_PUNCT = re.compile(r"^[\W_]+|[\W_]+$")


@dataclass
class Term:
    text: str
    phrase: bool = False  # several words, matched in order
    exact: bool = False   # quoted: never fuzzy


@dataclass
class Query:
    groups: list = field(default_factory=list)    # ANDed; each group is a list of ORed Terms
    excluded: list = field(default_factory=list)  # Terms that must not match
    raw: str = ""                                 # the whole input, for the exact ID match

    @property
    def single_token(self):
        return bool(self.raw) and not any(c.isspace() for c in self.raw)


def parse(raw):
    """websearch-style input -> Query. Words with no letter or digit are dropped."""
    q = Query(raw=raw.strip())
    pending_or = False
    for neg, quoted, word in _TOKEN.findall(q.raw):
        if quoted or (neg and not word):
            words = quoted.split()
            if not words:
                continue
            term = Term(" ".join(words), phrase=len(words) > 1, exact=True)
        else:
            if word.lower() == "or":
                pending_or = bool(q.groups)
                continue
            neg = "-" if word.startswith("-") and len(word) > 1 else ""
            word = _EDGE_PUNCT.sub("", word[1:] if neg else word)    # "isreal," -> "isreal"
            if not any(c.isalnum() for c in word):
                continue
            term = Term(word)
        if neg:
            q.excluded.append(term)
        elif pending_or:
            q.groups[-1].append(term)
        else:
            q.groups.append([term])
        pending_or = False
    return q


def drop_stopwords(session, q):
    """Remove English stopwords (single unquoted words), as websearch_to_tsquery did: BM25 indexes
    them, so "the" would otherwise have to match. Groups left empty are removed."""
    words = sorted({t.text for g in q.groups for t in g if not t.phrase})
    if not words:
        return q
    stop = set(session.execute(
        text("SELECT w FROM unnest(CAST(:ws AS text[])) AS w "
             "WHERE ts_lexize('english_stem', lower(w)) = '{}'"),
        {"ws": words}).scalars())
    q.groups = [g2 for g2 in ([t for t in g if t.phrase or t.text not in stop] for g in q.groups) if g2]
    return q


def typo_distance(word):
    """Edits allowed for a word: none up to 4 letters, 1 up to 8, else 2 (pg_search's maximum)."""
    n = len(word)
    return 0 if n <= 4 else 1 if n <= 8 else 2


def has_fuzzy_words(q):
    return any(not t.exact and typo_distance(t.text) for g in q.groups for t in g)


# --- spelling correction from the site's own vocabulary -------------------------------------
# mv_search_words (ytac): every word of the mv_video titles, lowercase and unstemmed, with ndoc, the
# number of titles that contain it. A word is corrected to a nearby word found in at least
# CORRECTION_MIN_GAIN times as many titles. Measured on production (2026-11-25): 18 of 18 test typos
# corrected right (holocost, isreal, censorhsip, stroage, ...), none of 12 rare but correct words
# changed (plandemic, navalny, tartaria, mrna, ...).
CORRECTION_MIN_GAIN = 20
CORRECTION_MIN_LEN = 4
CORRECT_MAX_EXACT = 500     # searches with this many exact video matches are not second-guessed
_LETTERS = re.compile(r"[^\W\d_]+")


def edit_distance(a, b):
    """Levenshtein distance where swapping two adjacent letters is one edit (optimal string alignment)."""
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[-1]


def best_correction(word, own, candidates):
    """The correction for word (found in own titles) among candidates [(word, ndoc)]: within 1 edit for
    words of up to 5 letters, else 2; in CORRECTION_MIN_GAIN times as many titles; the closest, then
    the most common. None if there is none."""
    limit = 1 if len(word) <= 5 else 2
    floor = CORRECTION_MIN_GAIN * max(own, 1)
    ranked = sorted((d, -n, c) for c, n in candidates
                    if c != word and n >= floor and (d := edit_distance(word, c)) <= limit)
    return ranked[0][2] if ranked else None


def correct(session, q):
    """{word: correction} for the misspelt words of q: unquoted words of letters only, 4 or more."""
    fixes = {}
    words = {t.text.lower() for g in q.groups for t in g if not t.exact}
    words = [w for w in sorted(words) if len(w) >= CORRECTION_MIN_LEN and _LETTERS.fullmatch(w)]
    if not words:
        return fixes
    # pg_trgm's default 0.3 misses swapped letters (isreal/israel is 0.27); for this transaction only
    session.execute(text("SELECT set_config('pg_trgm.similarity_threshold', '0.2', true)"))
    for w in words:
        own = session.execute(text("SELECT ndoc FROM mv_search_words WHERE word = :w"), {"w": w}).scalar() or 0
        candidates = session.execute(
            text("SELECT word, ndoc FROM mv_search_words WHERE word % :w AND ndoc >= :floor "
                 "ORDER BY similarity(word, :w) DESC LIMIT 30"),
            {"w": w, "floor": CORRECTION_MIN_GAIN * max(own, 1)}).all()
        best = best_correction(w, own, candidates)
        if best:
            fixes[w] = best
    return fixes


def apply_corrections(q, fixes):
    """A copy of q with the corrected words replaced."""
    return replace(q, groups=[[replace(t, text=fixes.get(t.text.lower(), t.text)) if not t.exact else t
                               for t in g] for g in q.groups])


def corrected_text(term, fixes):
    """The user's input with the corrected words replaced, for "Showing results for ...". Quoted
    parts and -excluded words are never corrected, so they stay as typed."""
    parts = re.split(r'("[^"]*"?)', term)
    for i in range(0, len(parts), 2):           # the even parts are outside quotes
        for word, fix in fixes.items():
            parts[i] = re.sub(rf"(?<![\w-]){re.escape(word)}(?![\w-])", fix, parts[i], flags=re.IGNORECASE)
    return "".join(parts)


class _Params:
    def __init__(self):
        self.values = {}

    def add(self, value):
        name = f"s{len(self.values)}"
        self.values[name] = value
        return f":{name}"


def _match(col, term, boost, fuzzy, params):
    p = params.add(term.text)
    if term.phrase:
        return f"{col} ### {p}"
    n = typo_distance(term.text) if fuzzy and not term.exact else 0
    if n:
        # a transposition ("teh") counts as one edit
        p = f"CAST({p} AS pdb.fuzzy({n}, f, t))"
    if boost != 1:
        p = f"CAST({p} AS pdb.boost({boost}))"
    return f"{col} &&& {p}"


def _any_field(fields, term, fuzzy, params, boosts=True):
    return "(" + " OR ".join(_match(col, term, b if boosts else 1, fuzzy, params)
                             for col, b in fields) + ")"


def where(q, fields, ids=(), fuzzy=False):
    """The WHERE clause for q on one view, as a bound text() clause. Matches nothing when q has no
    words left."""
    params = _Params()
    if not q.groups:
        return text("false")
    parts = []
    for group in q.groups:
        alts = [_any_field(fields, t, fuzzy, params) for t in group]
        parts.append(alts[0] if len(alts) == 1 else "(" + " OR ".join(alts) + ")")
    for t in q.excluded:
        parts.append("NOT " + _any_field(fields, t, False, params, boosts=False))
    sql = " AND ".join(parts)
    if ids and q.single_token:
        p = params.add(q.raw)
        sql = "(" + " OR ".join(f"{col} === {p}" for col in ids) + f" OR ({sql}))"
    return text(sql).bindparams(**params.values)


def score(view):
    return text(f"pdb.score({view}.id) DESC")
