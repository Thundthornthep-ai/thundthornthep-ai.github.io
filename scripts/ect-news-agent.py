#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECT Daily News Agent — ส.ก. Navigator

Scrapes https://www.ect.go.th/ect_th/th/dailynews2569 for latest daily news
PDFs, downloads them, extracts Thai text using pdfplumber, filters for BKK
council (ส.ก.) election keywords, and writes a JSON summary consumable by
the widget on blog/bkk-council/index.html.

Also renders pages with keyword matches as PNG images for the widget.

Usage:
    python scripts/ect-news-agent.py              # manual run
    python scripts/ect-news-agent.py --limit 3    # only process 3 latest
    python scripts/ect-news-agent.py --seed       # seed with hardcoded URLs (no scraping)

Output (all under blog/bkk-council/data/ect-news/):
    latest.json              — widget data
    pdfs/YYYY-MM-DD.pdf      — downloaded PDFs
    images/YYYY-MM-DD/*.png  — page snapshots for important pages

Dependencies: pdfplumber, requests, (optional) playwright for live scraping
"""
import sys
import io
import os
import re
import json
import argparse
import hashlib
import datetime as dt
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ============================================================
# Configuration
# ============================================================

# BKK SK keyword priority tiers (higher = more important)
KEYWORDS_STRICT = [
    "ผู้ว่าราชการกรุงเทพมหานคร",
    "สมาชิกสภากรุงเทพ",
    "สมาชิกสภากรุงเทพมหานคร",
    "สภากรุงเทพมหานคร",
    "ส.ก.",
    "สก. กทม",
    "เลือกตั้งกรุงเทพ",
    "เลือกตั้ง ส.ก.",
    "เลือกตั้งสมาชิกสภากรุงเทพ",
]

KEYWORDS_BROAD = [
    "วันเลือกตั้ง",
    "ค่าใช้จ่าย",
    "ชัชชาติ",
    "สภาเขต",
    "ผู้ว่าฯ กทม",
    "ผู้ว่า กทม",
    "กรุงเทพมหานคร",
]

KEYWORDS_CONTEXT = [
    "เลือกตั้ง",
    "เลือกตั้งท้องถิ่น",
    "ท้องถิ่น",
    "สมาชิกสภาท้องถิ่น",
    "ผู้บริหารท้องถิ่น",
    "กกต.",
]

# All keywords flat (for "important" flag)
IMPORTANT_KEYWORDS = set(KEYWORDS_STRICT + KEYWORDS_BROAD + KEYWORDS_CONTEXT)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "blog" / "bkk-council" / "data" / "ect-news"
PDF_DIR = DATA_DIR / "pdfs"
IMG_DIR = DATA_DIR / "images"
JSON_OUT = DATA_DIR / "latest.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# PDF URL discovery — scrape ect.go.th
# ============================================================

def discover_pdf_urls_playwright():
    """Use playwright to render the JS-heavy page and get PDF URLs.
    Returns list of (date_iso, pdf_url, size_mb).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("⚠️  playwright not installed. Install: pip install playwright && playwright install chromium")
        return []

    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Use domcontentloaded (faster, doesn't wait for analytics)
            page.goto("https://www.ect.go.th/ect_th/th/dailynews2569",
                      wait_until="domcontentloaded", timeout=45000)
            # Wait for at least one PDF card to appear
            try:
                page.wait_for_selector('a[href*=".pdf"]', timeout=15000)
            except Exception:
                print("  ⚠️  PDF cards didn't appear within 15s — page may have changed")
            # Small grace period for JS rendering
            page.wait_for_timeout(2000)
            # Find all PDF cards
            cards = page.evaluate("""() => {
                const cards = Array.from(document.querySelectorAll('.table-card-01, tr.table-card-01'));
                return cards.map(c => {
                    const link = c.querySelector('a[href*=".pdf"]');
                    return {
                        href: link ? link.href : '',
                        text: c.textContent.trim()
                    };
                }).filter(c => c.href);
            }""")
            browser.close()
    except Exception as e:
        print(f"  ⚠️  Playwright discovery failed: {e}")
        return []

    # Parse card texts like "สรุปข่าว วันที่ 10 เม.ย. 69.pdf ขนาดไฟล์ 28.43 MB ..."
    thai_months = {
        "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4,
        "พ.ค.": 5, "มิ.ย.": 6, "ก.ค.": 7, "ส.ค.": 8,
        "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
    }
    for c in cards:
        m = re.search(r"วันที่\s*(\d{1,2})\s*([ก-๙\.]+)\s*(\d{2,4})", c["text"])
        if not m:
            continue
        day, mon_th, year_buddhist = m.group(1), m.group(2), m.group(3)
        month = thai_months.get(mon_th)
        if not month:
            continue
        # Convert BE 2-digit year to CE
        year_buddhist = int(year_buddhist)
        if year_buddhist < 100:
            year_buddhist += 2500  # 69 → 2569
        ce_year = year_buddhist - 543
        date_iso = f"{ce_year:04d}-{month:02d}-{int(day):02d}"

        size_match = re.search(r"(\d+\.?\d*)\s*MB", c["text"])
        size = float(size_match.group(1)) if size_match else 0
        results.append((date_iso, c["href"], size))

    # Sort newest first
    results.sort(key=lambda x: x[0], reverse=True)
    return results


# Fallback: hardcoded URLs for 6-10 April 2026 (from manual discovery)
SEED_URLS = [
    ("2026-04-10", "https://www.ect.go.th/web-upload/1xff0d34e409a13ef56eea54c52a291126/m_document/2703/31662/file_download/6d26211f84e4ef33bb462ef3344b43df.pdf", 28.43),
    ("2026-04-09", "https://www.ect.go.th/web-upload/1xff0d34e409a13ef56eea54c52a291126/m_document/2703/31660/file_download/f689f0b3974be0bbe742e998f2b21253.pdf", 32.43),
    ("2026-04-08", "https://www.ect.go.th/web-upload/1xff0d34e409a13ef56eea54c52a291126/202604/m_document/2703/31653/file_download/b4220a7be10b98f0c333aacb11186a29.pdf", 19.64),
    ("2026-04-07", "https://www.ect.go.th/web-upload/1xff0d34e409a13ef56eea54c52a291126/m_document/2703/31648/file_download/6761427ed35c772ac9f79f16d90476d1.pdf", 16.38),
    ("2026-04-06", "https://www.ect.go.th/web-upload/1xff0d34e409a13ef56eea54c52a291126/m_document/2703/31464/file_download/44c414d8e477c3f4ab823e7d4af82372.pdf", 10.96),
]


# ============================================================
# PDF download + extract
# ============================================================

def download_pdf(url, target_path):
    """Download PDF with requests + browser User-Agent.
    ect.go.th rejects python-requests default UA with 403. Mimic Chrome.
    Returns True if downloaded (or exists).
    """
    if target_path.exists() and target_path.stat().st_size > 10000:
        return True
    try:
        import requests
    except ImportError:
        print("⚠️  requests not installed")
        return False
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,*/*;q=0.8",
        "Accept-Language": "th,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.ect.go.th/ect_th/th/dailynews2569",
    }
    try:
        r = requests.get(url, stream=True, timeout=180, headers=headers)
        r.raise_for_status()
        with open(target_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  ❌ download failed: {e}")
        # Clean up partial file
        if target_path.exists() and target_path.stat().st_size < 10000:
            try:
                target_path.unlink()
            except Exception:
                pass
        return False


def extract_sk_mentions(pdf_path):
    """Extract text page by page, return list of (page_num, important_keywords, text_snippet)."""
    import pdfplumber

    findings = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            matched = []
            for kw in IMPORTANT_KEYWORDS:
                if kw in text:
                    matched.append(kw)
            if matched:
                # Get the 3 most relevant paragraphs
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                matched_lines = []
                for line in lines:
                    if any(kw in line for kw in matched):
                        matched_lines.append(line)
                snippet = " | ".join(matched_lines[:5])[:800]
                findings.append({
                    "page": i,
                    "total_pages": total_pages,
                    "keywords": sorted(set(matched)),
                    "snippet": snippet,
                    "full_text": text[:3000],
                })
    return findings


def render_page_images(pdf_path, page_numbers, out_dir, max_pages=3):
    """Render specific pages as PNG images. Returns list of relative paths."""
    import pdfplumber

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    with pdfplumber.open(pdf_path) as pdf:
        for pn in page_numbers[:max_pages]:
            if pn < 1 or pn > len(pdf.pages):
                continue
            try:
                img = pdf.pages[pn - 1].to_image(resolution=120)
                out_path = out_dir / f"p{pn:03d}.png"
                img.save(out_path, format="PNG")
                rendered.append(out_path)
            except Exception as e:
                print(f"  ⚠️  render page {pn} failed: {e}")
    return rendered


# ============================================================
# Summary generation
# ============================================================

def summarize_findings(date_iso, pdf_url, findings, pdf_size_mb, pdf_pages):
    """Build a JSON-friendly summary item."""
    # Tier classification
    all_kw = set()
    for f in findings:
        all_kw.update(f["keywords"])
    tier = "none"
    if any(kw in all_kw for kw in KEYWORDS_STRICT):
        tier = "strict"
    elif any(kw in all_kw for kw in KEYWORDS_BROAD):
        tier = "broad"
    elif any(kw in all_kw for kw in KEYWORDS_CONTEXT):
        tier = "context"

    important = tier in ("strict", "broad")

    # Build title — if strict match exists, extract the most prominent headline
    title = f"สรุปข่าว กกต. ประจำวันที่ {date_iso}"
    summary_lines = []
    if findings:
        # Take the first strict-match finding as primary headline
        primary = None
        for f in findings:
            if any(kw in f["keywords"] for kw in KEYWORDS_STRICT):
                primary = f
                break
        if not primary:
            primary = findings[0]
        # Extract a clean headline-like line
        primary_lines = [l for l in primary["full_text"].split("\n") if l.strip() and len(l.strip()) > 15]
        if primary_lines:
            # Find line with SK keyword
            for line in primary_lines[:30]:
                if any(kw in line for kw in KEYWORDS_STRICT):
                    title = line.strip()[:200]
                    break
        # Build summary
        for f in findings[:3]:
            summary_lines.append(f"หน้า {f['page']}/{f['total_pages']}: {f['snippet'][:300]}")

    summary = "\n\n".join(summary_lines) if summary_lines else "ไม่มีข่าวที่เกี่ยวข้องกับ ส.ก. กทม. โดยตรงในวันนี้"

    # Matching keywords sorted by tier
    kw_sorted = []
    for kw in KEYWORDS_STRICT + KEYWORDS_BROAD + KEYWORDS_CONTEXT:
        if kw in all_kw:
            kw_sorted.append(kw)

    return {
        "date": date_iso,
        "title": title,
        "summary": summary,
        "tier": tier,
        "important": important,
        "matched_keywords": kw_sorted,
        "finding_count": len(findings),
        "pdf_url": pdf_url,
        "pdf_size_mb": pdf_size_mb,
        "pdf_pages": pdf_pages,
        "source_url": "https://www.ect.go.th/ect_th/th/dailynews2569",
    }


# ============================================================
# Main
# ============================================================

def process_one(date_iso, pdf_url, size_mb):
    """Process a single day's PDF. Returns dict or None."""
    import pdfplumber

    print(f"\n📅 {date_iso}")
    pdf_path = PDF_DIR / f"{date_iso}.pdf"

    if not download_pdf(pdf_url, pdf_path):
        return None

    print(f"  ✓ downloaded ({pdf_path.stat().st_size/1024/1024:.1f} MB)")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

    findings = extract_sk_mentions(pdf_path)
    print(f"  ✓ extracted — {len(findings)} pages with keyword matches")

    # Render important pages
    images_rel = []
    if findings:
        # Prioritize STRICT-matched pages first
        strict_pages = [f["page"] for f in findings if any(kw in f["keywords"] for kw in KEYWORDS_STRICT)]
        broad_pages = [f["page"] for f in findings if not any(kw in f["keywords"] for kw in KEYWORDS_STRICT)]
        pages_to_render = strict_pages + broad_pages
        img_out_dir = IMG_DIR / date_iso
        rendered = render_page_images(pdf_path, pages_to_render, img_out_dir, max_pages=3)
        images_rel = [
            f"data/ect-news/images/{date_iso}/{p.name}" for p in rendered
        ]
        print(f"  ✓ rendered {len(images_rel)} page images")

    item = summarize_findings(date_iso, pdf_url, findings, size_mb, total_pages)
    item["pdf_local"] = f"data/ect-news/pdfs/{date_iso}.pdf"
    item["images"] = images_rel
    return item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="Max PDFs to process")
    parser.add_argument("--seed", action="store_true", help="Use hardcoded seed URLs (no scraping)")
    args = parser.parse_args()

    print("=" * 70)
    print(f"  ECT DAILY NEWS AGENT — {dt.datetime.now().isoformat()}")
    print("=" * 70)

    if args.seed:
        urls = SEED_URLS[: args.limit]
        print(f"Using {len(urls)} seed URLs (no scraping)")
    else:
        print("Discovering latest PDFs via Playwright...")
        try:
            urls = discover_pdf_urls_playwright()
        except Exception as e:
            print(f"⚠️  discovery crashed: {e}")
            urls = []
        if not urls:
            print("⚠️  discovery returned empty, falling back to seed URLs")
            urls = SEED_URLS
        urls = urls[: args.limit]
        print(f"Using {len(urls)} PDFs")

    items = []
    for date_iso, pdf_url, size_mb in urls:
        try:
            item = process_one(date_iso, pdf_url, size_mb)
            if item:
                items.append(item)
        except Exception as e:
            print(f"  ❌ error: {e}")
            import traceback
            traceback.print_exc()

    # SAFEGUARD: Don't overwrite latest.json if new data is empty.
    # This protects against network failures silently clearing the widget.
    if len(items) == 0:
        print("\n⚠️  No items produced — KEEPING existing latest.json unchanged")
        print("   (This prevents a failed run from clearing the widget)")
        if JSON_OUT.exists():
            print(f"   Existing: {JSON_OUT}")
        print("=" * 70)
        sys.exit(0)

    # SAFEGUARD: If existing JSON has more items and new run has fewer,
    # preserve the old data (merge rather than replace).
    existing_items = []
    if JSON_OUT.exists():
        try:
            existing = json.loads(JSON_OUT.read_text(encoding="utf-8"))
            existing_items = existing.get("items", [])
        except Exception:
            pass
    # Merge: new items take priority, fill up to 10 total
    existing_by_date = {it["date"]: it for it in existing_items}
    for it in items:
        existing_by_date[it["date"]] = it  # new overwrites old for same date
    merged = sorted(existing_by_date.values(), key=lambda x: x["date"], reverse=True)[:10]

    # Write latest.json
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
    payload = {
        "lastUpdated": now.isoformat(),
        "lastUpdatedHuman": now.strftime("%d %b %Y %H:%M น. (เวลาไทย)"),
        "source": "https://www.ect.go.th/ect_th/th/dailynews2569",
        "itemCount": len(merged),
        "items": merged,
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 Wrote {JSON_OUT} ({len(merged)} items — merged from {len(existing_items)} existing + {len(items)} new)")
    print("=" * 70)


if __name__ == "__main__":
    main()
