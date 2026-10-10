"""Synchronize the curated data.json with the browser-readable data.js file.

Run after editing data.json. This does NOT verify any dates or infer next-year deadlines.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
records = json.loads((root / "data.json").read_text(encoding="utf-8"))
assert isinstance(records["conferences"], list) and isinstance(records["awards"], list)
js = "/* Curated snapshot — verify dates against society sources. */\nwindow.RISE_DATA = " + json.dumps(records, ensure_ascii=False, indent=2) + ";\n"
(root / "data.js").write_text(js, encoding="utf-8")
print(f"Synced {len(records['conferences'])} conferences and {len(records['awards'])} awards")
