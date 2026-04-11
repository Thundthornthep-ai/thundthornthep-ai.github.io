#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECT News — Notification Delivery (Notion + Gmail)

Reads the latest daily brief from latest.json and pushes it to:
  1. Notion database (if NOTION_TOKEN + NOTION_DATABASE_ID are set)
  2. Gmail (if GMAIL_USER + GMAIL_APP_PASSWORD are set)

All credentials are read from environment variables (or .env file).
**Never hardcode API keys in this file.**

Usage:
    python scripts/ect-news-notify.py                    # send latest brief
    python scripts/ect-news-notify.py --date 2026-04-10  # specific date
    python scripts/ect-news-notify.py --channel notion   # only Notion
    python scripts/ect-news-notify.py --channel gmail    # only Gmail
    python scripts/ect-news-notify.py --dry-run          # render, don't send

Environment variables (set via .env or PowerShell $env:*):
    NOTION_TOKEN            — Internal integration secret
    NOTION_DATABASE_ID      — Target database ID (32 chars, no dashes)
    GMAIL_USER              — Sender email (e.g., khuntae@gmail.com)
    GMAIL_APP_PASSWORD      — App password (Google Account → Security → App passwords)
    GMAIL_RECIPIENTS        — Comma-separated list (default: GMAIL_USER)

Setup:
    1. Copy .env.example → .env in repo root
    2. Fill in the four vars above
    3. .env is gitignored — safe to commit .env.example only
"""
import sys
import io
import os
import json
import argparse
import datetime as dt
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
LATEST_JSON = REPO_ROOT / "blog" / "bkk-council" / "data" / "ect-news" / "latest.json"
DAILY_DIR = REPO_ROOT / "blog" / "bkk-council" / "data" / "ect-news" / "daily"


def load_env():
    """Lightweight .env loader (no python-dotenv dependency)."""
    env_fp = REPO_ROOT / ".env"
    if env_fp.exists():
        for line in env_fp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


def get_item(date=None):
    """Load item for given date (or most recent)."""
    if date:
        fp = DAILY_DIR / f"{date}.json"
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
    # Fallback: load latest from main file
    if LATEST_JSON.exists():
        data = json.loads(LATEST_JSON.read_text(encoding="utf-8"))
        items = data.get("items", [])
        if date:
            for it in items:
                if it.get("date") == date:
                    return it
        return items[0] if items else None
    return None


# ============================================================
# Notion delivery
# ============================================================

def push_to_notion(item, dry_run=False):
    """Create a new page in the Notion database with the daily brief."""
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not db_id:
        print("  ⚠️  Notion: NOTION_TOKEN or NOTION_DATABASE_ID not set — skipping")
        return False

    try:
        import requests
    except ImportError:
        print("  ❌ Notion: requests not installed")
        return False

    # Notion database schema expected (create manually once):
    #   Title (title)             — news headline
    #   Date (date)               — ISO date
    #   Tier (select)             — strict/broad/context/none
    #   Important (checkbox)      — bool
    #   Keywords (multi_select)   — matched keywords
    #   Summary (rich_text)       — first 2000 chars
    #   PDF URL (url)             — ect.go.th link
    #   Pages (number)            — total PDF pages
    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Title": {
                "title": [{"text": {"content": item.get("title", "(ไม่มีชื่อ)")[:200]}}]
            },
            "Date": {
                "date": {"start": item.get("date")}
            },
            "Tier": {
                "select": {"name": item.get("tier", "none")}
            },
            "Important": {
                "checkbox": bool(item.get("important", False))
            },
            "Keywords": {
                "multi_select": [
                    {"name": kw[:100]} for kw in item.get("matched_keywords", [])[:10]
                ]
            },
            "Summary": {
                "rich_text": [{"text": {"content": item.get("summary", "")[:2000]}}]
            },
            "PDF URL": {
                "url": item.get("pdf_url", "") or None
            },
            "Pages": {
                "number": item.get("pdf_pages", 0) or 0
            },
        },
    }

    if dry_run:
        print("  [dry-run] Notion payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:800])
        return True

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    try:
        r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30)
        if r.ok:
            print(f"  ✅ Notion: created page for {item['date']}")
            return True
        else:
            print(f"  ❌ Notion: {r.status_code} {r.text[:300]}")
            return False
    except Exception as e:
        print(f"  ❌ Notion: {e}")
        return False


# ============================================================
# Gmail delivery
# ============================================================

def push_to_gmail(item, dry_run=False):
    """Send the daily brief via Gmail SMTP (app password)."""
    user = os.environ.get("GMAIL_USER")
    app_pw = os.environ.get("GMAIL_APP_PASSWORD")
    recipients_raw = os.environ.get("GMAIL_RECIPIENTS", user or "")

    if not user or not app_pw:
        print("  ⚠️  Gmail: GMAIL_USER or GMAIL_APP_PASSWORD not set — skipping")
        return False

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        print("  ⚠️  Gmail: no recipients")
        return False

    # Build email body
    imp_badge = "⭐ สำคัญ" if item.get("important") else ""
    tier_label = {
        "strict": "🔴 ส.ก. ตรง",
        "broad": "🟡 ขยาย",
        "context": "⚪ บริบท",
    }.get(item.get("tier", "none"), "")

    subject = f"[ECT News] {item.get('date')} — {imp_badge} {item.get('title', '')[:60]}"

    html_lines = [
        "<html><body style=\"font-family:'Sarabun',Arial,sans-serif;line-height:1.6;color:#222;\">",
        f"<h2 style=\"color:#1B2A4A;\">📰 ECT Daily News Brief — {item.get('date')}</h2>",
        f"<p><strong>Tier:</strong> {tier_label}  |  <strong>{imp_badge}</strong></p>",
        f"<h3>{item.get('title', '(ไม่มีชื่อ)')}</h3>",
        "<p><strong>Matched keywords:</strong></p>",
        "<p>" + " · ".join(
            f"<code style='background:#F3F4F6;padding:2px 6px;border-radius:3px;'>{kw}</code>"
            for kw in item.get("matched_keywords", [])[:10]
        ) + "</p>",
        "<h3>Summary</h3>",
        f"<pre style=\"white-space:pre-wrap;background:#F9FAFB;padding:12px;border-left:3px solid #C9A96E;\">{item.get('summary', '(no summary)')[:3000]}</pre>",
    ]
    if item.get("pdf_url"):
        html_lines.append(
            f"<p>📄 <a href=\"{item['pdf_url']}\">PDF ต้นฉบับ</a> "
            f"({item.get('pdf_pages', '?')} หน้า · {item.get('pdf_size_mb', '?')} MB)</p>"
        )
    html_lines.append(f"<p>🔍 พบ {item.get('finding_count', 0)} หน้าที่เกี่ยวข้อง</p>")
    html_lines.append(
        "<hr><p style='font-size:11px;color:#9CA3AF;'>"
        "Generated by scripts/ect-news-notify.py · ส.ก. Navigator · "
        "<a href='https://thundthornthep-ai.github.io/blog/bkk-council/'>View widget</a>"
        "</p></body></html>"
    )
    html_body = "\n".join(html_lines)

    if dry_run:
        print(f"  [dry-run] Gmail to {recipients}")
        print(f"  Subject: {subject}")
        print(f"  Body (first 500 chars): {html_body[:500]}")
        return True

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(user, app_pw)
            server.send_message(msg)
        print(f"  ✅ Gmail: sent to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        print(f"  ❌ Gmail: {e}")
        return False


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Specific date YYYY-MM-DD (default: latest)")
    parser.add_argument("--channel", choices=["notion", "gmail", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Render only, don't send")
    args = parser.parse_args()

    print("=" * 70)
    print(f"  ECT NEWS NOTIFY — {dt.datetime.now().isoformat()}")
    print("=" * 70)

    load_env()

    item = get_item(args.date)
    if not item:
        print("❌ No data found. Run scripts/ect-news-agent.py first.")
        sys.exit(1)

    print(f"Item: {item.get('date')} — {item.get('title', '(untitled)')[:80]}")
    print(f"Tier: {item.get('tier')}  |  Important: {item.get('important')}")
    print()

    results = {}
    if args.channel in ("notion", "all"):
        print("→ Notion")
        results["notion"] = push_to_notion(item, dry_run=args.dry_run)
    if args.channel in ("gmail", "all"):
        print("→ Gmail")
        results["gmail"] = push_to_gmail(item, dry_run=args.dry_run)

    print()
    print("=" * 70)
    success = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"  RESULT: {success}/{total} channels succeeded")
    print("=" * 70)


if __name__ == "__main__":
    main()
