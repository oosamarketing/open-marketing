"""
ad_copywriter — deterministic tooling around agent-written ad copy.

The agent (Claude in Cowork / Claude Code, or the optional generator) writes the
copy. This package checks it against platform limits and the OOSA house style,
exports it (xlsx / csv / docx), and renders branded previews (HTML / PDF).

Modules use relative imports only, so the same files run here as
``ad_copywriter.*`` and vendored into another project under a different package name.
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
SPEC_PATH = DATA_DIR / "platform_spec.json"
SCHEMA_PATH = DATA_DIR / "copy_document.schema.json"
ASSETS_DIR = PACKAGE_DIR / "preview" / "assets"
TEMPLATES_DIR = PACKAGE_DIR / "preview" / "templates"

from .document import CopyDocument, CopySet, dump_document, load_document, new_document  # noqa: E402
from .spec import FieldSpec, PlatformSpec, get_platform, load_spec, platform_keys  # noqa: E402
from .validate import ValidationResult, apply_validation, validate_document  # noqa: E402

__all__ = [
    "__version__",
    "PACKAGE_DIR",
    "DATA_DIR",
    "SPEC_PATH",
    "SCHEMA_PATH",
    "ASSETS_DIR",
    "TEMPLATES_DIR",
    "CopyDocument",
    "CopySet",
    "FieldSpec",
    "PlatformSpec",
    "ValidationResult",
    "apply_validation",
    "dump_document",
    "get_platform",
    "load_document",
    "load_spec",
    "new_document",
    "platform_keys",
    "validate_document",
]
