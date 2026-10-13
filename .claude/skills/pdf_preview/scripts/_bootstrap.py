"""Make ``ad_copywriter`` importable when the scripts run straight from the skill folder.

Resolution order: already installed (pip) → ``AD_COPYWRITER_ROOT`` env → walk up from this file looking for
``ad_copywriter/__init__.py`` (the skill inside its own repo) or ``tools/ad-copywriter/`` (the skill copied
into the Open Marketing hub).
"""

from __future__ import annotations

import os
import pathlib
import sys


def _find_root(start: pathlib.Path, depth: int = 6) -> str | None:
    p = start
    for _ in range(depth):
        for root in (p, p / "tools" / "ad-copywriter"):
            if (root / "ad_copywriter" / "__init__.py").exists():
                return str(root)
        p = p.parent
    return None


try:
    import ad_copywriter  # noqa: F401
except ImportError:
    _root = os.environ.get("AD_COPYWRITER_ROOT") or _find_root(pathlib.Path(__file__).resolve().parent)
    if not _root:
        sys.exit(
            "These scripts need the ad-copywriter tool: its ad_copywriter Python package was not found (not installed, "
            "no tools/ad-copywriter next to this skill, AD_COPYWRITER_ROOT not set). The tool is not included in this "
            "folder. Without it, write and check the copy by hand from the skill's references/ and say that it was "
            "not machine-validated."
        )
    sys.path.insert(0, _root)
