"""
LAS-WEB-CARDS-20260430 — Apply Direct-Link Mapping to legal-links.js
Reads data/ocs-direct-links.json and updates LAW_CARD_MAP entries
in js/legal-links.js to include ocs_url alongside ocs keyword.

Also updates resolveLawRefCards() to prefer ocs_url over keyword search.

Usage: py -X utf8 scripts/apply-ocs-direct-links.py
Backup: js/legal-links.js.bak written before modification
"""
import json
import re
import sys
import io
import shutil
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).parent.parent
JSON_PATH = ROOT / "data" / "ocs-direct-links.json"
JS_PATH = ROOT / "js" / "legal-links.js"
BAK_PATH = ROOT / "js" / "legal-links.js.bak"


def thai_to_js_unicode(s):
    """Encode Thai chars as \\uXXXX, matching the format used in legal-links.js."""
    out = []
    for ch in s:
        if 0x0E00 <= ord(ch) <= 0x0E7F:  # Thai block
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    return "".join(out)


def patch_entry(js_text, key, ocs_url):
    """Find a LAW_CARD_MAP entry and inject ocs_url field next to existing ocs field.

    Tries plain-Thai key first, then JS \\u-escaped key.
    Returns (new_text, matched_form) or (js_text, None) if not found.
    """
    candidates = [key, thai_to_js_unicode(key)]
    for k in candidates:
        # Pattern: '<key>': { ocs: '<anything>', ...rest }
        # Inject:  '<key>': { ocs_url: '<url>', ocs: '<anything>', ...rest }
        # Use re.escape to handle special chars in key
        pattern = re.compile(
            r"('" + re.escape(k) + r"'\s*:\s*\{\s*)(ocs\s*:\s*')",
            re.UNICODE,
        )
        new_text, n = pattern.subn(
            r"\1ocs_url: '" + ocs_url + r"', \2",
            js_text,
            count=1,
        )
        if n == 1:
            return new_text, k
    return js_text, None


RESOLVER_OLD = """      } else if (entry.ocs) {
        card.href = OCS + '?q=' + encodeURIComponent(entry.ocs);
        if (sourceEl) sourceEl.textContent = '\\uD83D\\uDD17 \\u0E04\\u0E49\\u0E19\\u0E2B\\u0E32\\u0E15\\u0E31\\u0E27\\u0E1A\\u0E17\\u0E01\\u0E0E\\u0E2B\\u0E21\\u0E32\\u0E22 \\u2014 \\u0E2A\\u0E33\\u0E19\\u0E31\\u0E01\\u0E07\\u0E32\\u0E19\\u0E04\\u0E13\\u0E30\\u0E01\\u0E23\\u0E23\\u0E21\\u0E01\\u0E32\\u0E23\\u0E01\\u0E24\\u0E29\\u0E0E\\u0E35\\u0E01\\u0E32';
      }"""

RESOLVER_NEW = """      } else if (entry.ocs_url) {
        card.href = entry.ocs_url;
        card.target = '_blank';
        card.rel = 'noopener';
        if (sourceEl) sourceEl.textContent = '\\uD83D\\uDD17 \\u0E40\\u0E1B\\u0E34\\u0E14\\u0E15\\u0E31\\u0E27\\u0E1A\\u0E17\\u0E01\\u0E0E\\u0E2B\\u0E21\\u0E32\\u0E22 \\u2014 \\u0E2A\\u0E33\\u0E19\\u0E31\\u0E01\\u0E07\\u0E32\\u0E19\\u0E04\\u0E13\\u0E30\\u0E01\\u0E23\\u0E23\\u0E21\\u0E01\\u0E32\\u0E23\\u0E01\\u0E24\\u0E29\\u0E0E\\u0E35\\u0E01\\u0E32';
      } else if (entry.ocs) {
        card.href = OCS + '?q=' + encodeURIComponent(entry.ocs);
        card.target = '_blank';
        card.rel = 'noopener';
        if (sourceEl) sourceEl.textContent = '\\uD83D\\uDD17 \\u0E04\\u0E49\\u0E19\\u0E2B\\u0E32\\u0E15\\u0E31\\u0E27\\u0E1A\\u0E17\\u0E01\\u0E0E\\u0E2B\\u0E21\\u0E32\\u0E22 \\u2014 \\u0E2A\\u0E33\\u0E19\\u0E31\\u0E01\\u0E07\\u0E32\\u0E19\\u0E04\\u0E13\\u0E30\\u0E01\\u0E23\\u0E23\\u0E21\\u0E01\\u0E32\\u0E23\\u0E01\\u0E24\\u0E29\\u0E0E\\u0E35\\u0E01\\u0E32';
      }"""


def main():
    print(f"[READ] {JSON_PATH}")
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    print(f"       {len(data)} entries to apply")

    print(f"[READ] {JS_PATH}")
    js_text = JS_PATH.read_text(encoding="utf-8")
    original_size = len(js_text)
    print(f"       {original_size:,} bytes")

    # Backup
    shutil.copy2(JS_PATH, BAK_PATH)
    print(f"[BAK]  {BAK_PATH}")

    # Apply each entry
    print()
    applied = 0
    skipped = []
    for key, entry in data.items():
        url = entry["reference_url"]
        js_text, matched = patch_entry(js_text, key, url)
        if matched:
            form = "plain" if matched == key else "\\u-escape"
            print(f"[APPL] {key!r:35s} ({form})")
            applied += 1
        else:
            print(f"[SKIP] {key!r:35s} — pattern not found in JS")
            skipped.append(key)

    # Update resolver function
    print()
    if RESOLVER_OLD in js_text:
        js_text = js_text.replace(RESOLVER_OLD, RESOLVER_NEW, 1)
        print("[RESV] resolveLawRefCards() updated to prefer ocs_url")
    else:
        print("[WARN] resolver pattern not found exactly — manual check required")

    # Write back
    JS_PATH.write_text(js_text, encoding="utf-8")
    new_size = len(js_text)
    print()
    print(f"[WRITE] {JS_PATH}")
    print(f"        {original_size:,} -> {new_size:,} bytes (+{new_size - original_size})")
    print(f"        applied: {applied}/{len(data)}")
    if skipped:
        print(f"        SKIPPED: {skipped}")
        sys.exit(1)


if __name__ == "__main__":
    main()
