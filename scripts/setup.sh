#!/usr/bin/env bash
# One-time setup: a local Python environment with the rendering browser.
#   scripts/setup.sh              # core (Playwright + Chromium, Pillow, numpy, requests)
#   scripts/setup.sh --cutouts    # also background removal for product photos (rembg, ~400 MB)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$HERE"
command -v python3 >/dev/null || { echo "Python 3.10+ is required: https://www.python.org/downloads/"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip -q install --upgrade pip
.venv/bin/pip -q install playwright pillow numpy requests openpyxl
.venv/bin/playwright install chromium
if [ "${1:-}" = "--cutouts" ]; then .venv/bin/pip -q install "rembg[cpu]" scipy; fi
echo; echo "Testing with the example brand…"
( cd tools/graphic-designer && ../../.venv/bin/python render.py templates/meta-simple-hero.html --brand northpeak \
    --data data/northpeak-meta-1x1.json --out out/setup-test.png >/dev/null ) \
  && echo "OK: tools/graphic-designer/out/setup-test.png" || { echo "Setup finished but the test render failed; see the tutorial's troubleshooting section."; exit 1; }
echo; echo "Ready. Open this folder in Claude Code and ask for a brand kit or an ad. See docs/tutorial.md."
