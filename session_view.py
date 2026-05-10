#!/usr/bin/env python3
"""Wrapper for session_view that loads static assets from the repo.
This file delegates to session_view_orig.py (definitions) while overriding
CSS/JS constants to read from separate files under static/.
"""
import sys
from pathlib import Path
import importlib.util

HERE = Path(__file__).parent
ORIG_PATH = HERE / "session_view_orig.py"
if not ORIG_PATH.exists():
    print("Error: session_view_orig.py not found", file=sys.stderr)
    sys.exit(1)

spec = importlib.util.spec_from_file_location("session_view_orig", str(ORIG_PATH))
orig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orig)


def _load_asset_text(relpath: str) -> str:
    p = HERE.joinpath(relpath)
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""

# Override large embedded strings with files under static/
orig.CSS = _load_asset_text("static/css/events.css") or getattr(orig, 'CSS', '')
orig.CSS_A11Y = _load_asset_text("static/css/events.a11y.css") or getattr(orig, 'CSS_A11Y', '')
orig.JS = _load_asset_text("static/js/events.js") or getattr(orig, 'JS', '')
orig.OVERVIEW_CSS = _load_asset_text("static/css/overview.css") or getattr(orig, 'OVERVIEW_CSS', '')
orig.OVERVIEW_JS = _load_asset_text("static/js/overview.js") or getattr(orig, 'OVERVIEW_JS', '')

# When executed as a script, call the original main
if __name__ == "__main__":
    orig.main()
