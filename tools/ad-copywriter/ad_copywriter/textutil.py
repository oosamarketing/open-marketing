"""Small text helpers shared by validation, exports and previews."""

from __future__ import annotations

import re
import unicodedata

BLOCK_SEPARATORS = {"...", "…"}  # literal three dots or the ellipsis character

_EMOJI_RE = re.compile(
    "^[\\s]*(?:"
    "[\U0001F300-\U0001FAFF]"  # symbols & pictographs, incl. supplemental
    "|[\U00002600-\U000027BF]"  # misc symbols, dingbats
    "|[\U0001F1E6-\U0001F1FF]"  # flags
    "|[\U00002B00-\U00002BFF]"  # arrows / stars
    "|[\U0000FE0F\U0000200D]"   # variation selector / ZWJ (part of sequences)
    ")"
)


def count_chars(text: str) -> int:
    """Character count as ad platforms count it: NFC-normalised code points.

    The oosamarketing.com tools count JavaScript ``.length`` (UTF-16 units), which
    is higher for emoji; Meta and Google count roughly by code point.
    """
    return len(unicodedata.normalize("NFC", text or ""))


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def split_blocks(text: str) -> list[str]:
    """Split primary text on separator lines (a line that is only ``...``).

    Blank lines around separators are dropped; block-internal newlines are kept.
    """
    blocks: list[str] = []
    current: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if line.strip() in BLOCK_SEPARATORS:
            blocks.append("\n".join(current).strip())
            current = []
        else:
            current.append(line)
    blocks.append("\n".join(current).strip())
    return [b for b in blocks if b]


def has_block_separator(text: str) -> bool:
    return any(line.strip() in BLOCK_SEPARATORS for line in (text or "").splitlines())


def truncate_fold(text: str, fold: int = 125, marker: str = "… See more") -> tuple[str, bool]:
    """Return (visible_text, truncated) the way Meta folds primary text in feed."""
    text = text or ""
    if count_chars(text) <= fold:
        return text, False
    cut = text[:fold].rstrip()
    # avoid cutting mid-word when there's a space to fall back to
    if " " in cut[-20:]:
        cut = cut[: cut.rfind(" ")]
    return cut + marker, True


def has_emoji_lead(text: str) -> bool:
    return bool(_EMOJI_RE.match(text or ""))


def is_all_caps(text: str) -> bool:
    letters = [c for c in (text or "") if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def slugify(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].strip("-") or "untitled"


_SHEET_BAD = re.compile(r"[\[\]:*?/\\]")


def safe_sheet_name(name: str, used: set[str] | None = None, max_len: int = 31) -> str:
    """Excel-safe sheet name: no ``[]:*?/\\``, at most 31 chars, unique within ``used``."""
    base = _SHEET_BAD.sub(" ", name or "Sheet").strip() or "Sheet"
    base = base[:max_len].strip()
    if used is None:
        return base
    candidate = base
    n = 2
    while candidate.lower() in {u.lower() for u in used}:
        suffix = f" ({n})"
        candidate = base[: max_len - len(suffix)].rstrip() + suffix
        n += 1
    used.add(candidate)
    return candidate


def domain_of(url: str | None) -> str:
    """``https://www.example.com/path`` -> ``example.com``."""
    if not url:
        return ""
    u = re.sub(r"^https?://", "", url.strip(), flags=re.I)
    u = u.split("/")[0].split("?")[0]
    return re.sub(r"^www\.", "", u, flags=re.I)
