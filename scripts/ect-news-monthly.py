#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECT Monthly Rollup Generator

Reads all daily data from blog/bkk-council/data/ect-news/latest.json
(and any archived daily files) and produces a monthly summary:

    blog/bkk-council/data/ect-news/monthly/YYYY-MM.md   (human-readable)
    blog/bkk-council/data/ect-news/monthly/YYYY-MM.json (machine-readable)
    blog/bkk-council/data/ect-news/monthly/index.json   (list of months)

For each month the rollup contains:
- Total daily briefs · total pages audited · total matches
- Top 10 keyword frequencies (ranked)
- Important events (tier=STRICT) chronologically
- Monthly narrative (3-5 bullets)
- Links to daily details

Usage:
    python scripts/ect-news-monthly.py              # rollup current month
    python scripts/ect-news-monthly.py --month 2026-04   # specific month
    python scripts/ect-news-monthly.py --all        # rollup every month with data
"""
import sys
import io
import os
import json
import argparse
import datetime as dt
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "blog" / "bkk-council" / "data" / "ect-news"
MONTHLY_DIR = DATA_DIR / "monthly"
DAILY_ARCHIVE_DIR = DATA_DIR / "daily"  # optional: archived per-day snapshots
LATEST_JSON = DATA_DIR / "latest.json"

MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
DAILY_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def load_all_items():
    """Collect all daily items from latest.json + any archived daily files.
    Returns dict keyed by date iso string.
    """
    items_by_date = {}

    # Load from latest.json
    if LATEST_JSON.exists():
        try:
            data = json.loads(LATEST_JSON.read_text(encoding="utf-8"))
            for item in data.get("items", []):
                if item.get("date"):
                    items_by_date[item["date"]] = item
        except Exception as e:
            print(f"⚠️  failed to read latest.json: {e}")

    # Load from daily archive (one JSON per day, if maintained)
    for fp in DAILY_ARCHIVE_DIR.glob("*.json"):
        try:
            item = json.loads(fp.read_text(encoding="utf-8"))
            if item.get("date"):
                items_by_date[item["date"]] = item
        except Exception:
            pass

    return items_by_date


def archive_daily_snapshot(items_by_date):
    """Save each item as a standalone file in daily/ (for long-term archive
    that survives latest.json rotation to max 10 items)."""
    for date, item in items_by_date.items():
        fp = DAILY_ARCHIVE_DIR / f"{date}.json"
        if not fp.exists():
            fp.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")


def rollup_month(year_month, items_by_date):
    """Produce rollup for one month. year_month is 'YYYY-MM'."""
    year, month = year_month.split("-")
    month_int = int(month)
    month_items = {
        d: it for d, it in items_by_date.items()
        if d.startswith(year_month)
    }

    if not month_items:
        print(f"  ⚠️  no data for {year_month}")
        return None

    # Sort by date ascending (chronological)
    sorted_items = [month_items[d] for d in sorted(month_items.keys())]

    # Aggregate stats
    total_days = len(sorted_items)
    total_pages = sum(it.get("pdf_pages", 0) for it in sorted_items)
    total_findings = sum(it.get("finding_count", 0) for it in sorted_items)
    total_size_mb = sum(it.get("pdf_size_mb", 0) or 0 for it in sorted_items)

    # Keyword frequencies
    kw_counter = Counter()
    for it in sorted_items:
        for kw in it.get("matched_keywords", []):
            kw_counter[kw] += 1
    top_keywords = kw_counter.most_common(10)

    # Tier distribution
    tier_counter = Counter(it.get("tier", "none") for it in sorted_items)

    # Important events (STRICT tier)
    important_events = [
        it for it in sorted_items if it.get("tier") == "strict"
    ]

    # Build Markdown
    buddhist_year = int(year) + 543
    month_th = THAI_MONTHS[month_int]
    md_lines = [
        f"# 📰 ECT Monthly Rollup — {month_th} {buddhist_year}",
        "",
        f"**Source:** https://www.ect.go.th/ect_th/th/dailynews2569",
        f"**Generated:** {dt.datetime.now().isoformat()}",
        f"**Period:** {year_month}-01 to {year_month}-{str(max(int(d.split('-')[2]) for d in month_items.keys())).zfill(2)}",
        "",
        "---",
        "",
        "## 📊 สรุปสถิติรายเดือน",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| วันที่ครอบคลุม | {total_days} วัน |",
        f"| หน้า PDF รวม | {total_pages:,} หน้า |",
        f"| ข้อความที่เกี่ยวข้อง | {total_findings:,} หน้า |",
        f"| ขนาดข้อมูลรวม | {total_size_mb:.1f} MB |",
        f"| Strict tier (ส.ก. ตรง) | {tier_counter.get('strict', 0)} วัน |",
        f"| Broad tier (ขยาย) | {tier_counter.get('broad', 0)} วัน |",
        f"| Context tier (บริบท) | {tier_counter.get('context', 0)} วัน |",
        "",
        "## 🔑 Top 10 Keywords",
        "",
        "| Rank | Keyword | Frequency |",
        "|------|---------|-----------|",
    ]
    for i, (kw, cnt) in enumerate(top_keywords, 1):
        md_lines.append(f"| {i} | `{kw}` | {cnt} |")

    md_lines += [
        "",
        "## ⭐ เหตุการณ์สำคัญ (STRICT Tier)",
        "",
    ]
    if important_events:
        for ev in important_events:
            date = ev.get("date", "?")
            title = ev.get("title", "(ไม่มีชื่อ)")
            kw_list = ", ".join(ev.get("matched_keywords", [])[:5])
            md_lines.append(f"### 📅 {date}")
            md_lines.append(f"**Title:** {title}")
            md_lines.append(f"**Keywords:** {kw_list}")
            if ev.get("summary"):
                summary_clean = ev["summary"].replace("\n", " ").replace("|", "·")[:400]
                md_lines.append(f"**Summary:** {summary_clean}...")
            if ev.get("pdf_url"):
                md_lines.append(f"**PDF:** [{ev.get('pdf_pages', '?')} หน้า, {ev.get('pdf_size_mb', '?')} MB]({ev['pdf_url']})")
            md_lines.append("")
    else:
        md_lines.append("_ไม่มีเหตุการณ์ Strict tier ในเดือนนี้_")
        md_lines.append("")

    # Auto narrative (simple heuristic)
    md_lines += [
        "## 📝 Monthly Narrative",
        "",
    ]
    narrative_bullets = []
    if tier_counter.get("strict", 0) >= 1:
        narrative_bullets.append(
            f"- เดือนนี้มี **{tier_counter['strict']} วัน** ที่กกต. ปล่อยข่าว/ประกาศเกี่ยวข้องโดยตรงกับ ส.ก. / ผู้ว่าฯ กทม."
        )
    if top_keywords:
        top_kw_str = ", ".join(f"`{kw}` ({cnt})" for kw, cnt in top_keywords[:3])
        narrative_bullets.append(f"- คีย์เวิร์ดที่ปรากฏบ่อยที่สุด: {top_kw_str}")
    if total_days > 0:
        avg_pages = total_pages / total_days
        narrative_bullets.append(
            f"- เฉลี่ยเนื้อหา {avg_pages:.0f} หน้า/วัน, {total_findings/total_days:.1f} หน้าที่เกี่ยวข้อง/วัน"
        )
    if not narrative_bullets:
        narrative_bullets.append("- _ยังไม่มีข้อมูลเพียงพอสำหรับการสรุป_")
    md_lines += narrative_bullets

    md_lines += [
        "",
        "## 🗓️ Daily Briefs (ครบทั้งเดือน)",
        "",
        "| Date | Title | Tier | Keywords | Pages |",
        "|------|-------|------|----------|-------|",
    ]
    for it in sorted_items:
        date = it.get("date", "?")
        title = (it.get("title", "")[:80] + "...") if len(it.get("title", "")) > 80 else it.get("title", "")
        title = title.replace("|", "·")
        tier = it.get("tier", "-")
        kw_count = len(it.get("matched_keywords", []))
        pages = it.get("pdf_pages", "?")
        md_lines.append(f"| {date} | {title} | {tier} | {kw_count} | {pages} |")

    md_lines += [
        "",
        "---",
        "",
        f"*Generated by `scripts/ect-news-monthly.py` · part of ส.ก. Navigator ({REPO_ROOT.name})*",
    ]

    md_content = "\n".join(md_lines)

    # Machine-readable JSON
    json_payload = {
        "year_month": year_month,
        "year": int(year),
        "month": month_int,
        "month_th": month_th,
        "buddhist_year": buddhist_year,
        "total_days": total_days,
        "total_pages": total_pages,
        "total_findings": total_findings,
        "total_size_mb": round(total_size_mb, 2),
        "tier_distribution": dict(tier_counter),
        "top_keywords": [{"keyword": kw, "count": cnt} for kw, cnt in top_keywords],
        "important_events": important_events,
        "daily_briefs": sorted_items,
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).isoformat(),
    }

    return {"md": md_content, "json": json_payload, "days": total_days}


def write_rollup(year_month, rollup):
    if not rollup:
        return
    md_fp = MONTHLY_DIR / f"{year_month}.md"
    json_fp = MONTHLY_DIR / f"{year_month}.json"
    md_fp.write_text(rollup["md"], encoding="utf-8")
    json_fp.write_text(
        json.dumps(rollup["json"], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ {year_month}: {rollup['days']} days → {md_fp.name} + {json_fp.name}")


def update_monthly_index():
    """Refresh monthly/index.json with list of all rollup months."""
    months = sorted([fp.stem for fp in MONTHLY_DIR.glob("*.json") if fp.stem != "index"], reverse=True)
    index = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).isoformat(),
        "count": len(months),
        "months": months,
        "latest": months[0] if months else None,
    }
    (MONTHLY_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ index.json: {len(months)} months")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="Specific month 'YYYY-MM' (default: current month in TH time)")
    parser.add_argument("--all", action="store_true", help="Rollup every month that has data")
    args = parser.parse_args()

    print("=" * 70)
    print(f"  ECT MONTHLY ROLLUP — {dt.datetime.now().isoformat()}")
    print("=" * 70)

    items_by_date = load_all_items()
    if not items_by_date:
        print("❌ No daily data found. Run scripts/ect-news-agent.py first.")
        sys.exit(1)

    print(f"Loaded {len(items_by_date)} daily items")

    # Always archive daily snapshots first (grows with time)
    archive_daily_snapshot(items_by_date)
    print(f"✓ archived to {DAILY_ARCHIVE_DIR.name}/")

    if args.all:
        months = sorted(set(d[:7] for d in items_by_date.keys()))
        print(f"Rolling up {len(months)} months: {months}")
    elif args.month:
        months = [args.month]
    else:
        # Current month in TH time
        now_th = dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
        months = [now_th.strftime("%Y-%m")]

    for ym in months:
        rollup = rollup_month(ym, items_by_date)
        if rollup:
            write_rollup(ym, rollup)

    update_monthly_index()
    print("=" * 70)
    print("✅ Done.")


if __name__ == "__main__":
    main()
