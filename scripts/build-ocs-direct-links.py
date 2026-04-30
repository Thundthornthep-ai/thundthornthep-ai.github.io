"""
LAS-WEB-CARDS-20260430 — OCS Direct-Link Builder
Reads HuggingFace ocs-krisdika dataset (cached locally) and generates
direct-load URLs for the 14 OCS cards in js/legal-links.js LAW_CARD_MAP.

Output: data/ocs-direct-links.json
Usage:  py -X utf8 scripts/build-ocs-direct-links.py
"""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 14 OCS cards currently using ?q=keyword fallback in legal-links.js
# Tuple: (search_pattern, preferred_year, exclude_keywords, must_startswith)
# must_startswith forces document-type match: "พระราชบัญญัติ", "ประมวล", "รัฐธรรมนูญ"
# This prevents picking subordinate notifications (ประกาศ/พ.ร.ฎ./กฎกระทรวง) that
# reference the act but are not the act itself.
TARGETS = {
    "เครื่องสำอาง":          ("เครื่องสำอาง",                    "2558", ["ยกเลิก"],                "พระราชบัญญัติ"),
    "อาหาร":               ("อาหาร พ.ศ. 2522",                 None,   ["ยกเลิก"],                "พระราชบัญญัติ"),
    "โรงงาน":              ("โรงงาน",                          "2535", ["ยกเลิก", "ฉบับที่"],       "พระราชบัญญัติ"),
    "ที่ดิน":               ("ประมวลกฎหมายที่ดิน",                None,   ["แก้ไข", "ฉบับที่"],        "ประมวล"),
    "ภาษีที่ดิน":           ("ภาษีที่ดินและสิ่งปลูกสร้าง พ.ศ. 2562", None,   [],                       "พระราชบัญญัติ"),
    "EEC":                ("เขตพัฒนาพิเศษภาคตะวันออก พ.ศ. 2561", None,   [],                       "พระราชบัญญัติ"),
    "ธุรกรรมอิเล็กทรอนิกส์": ("ธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544", None,   [],                       "พระราชบัญญัติ"),
    "ป.ป.ช.":             ("ประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต", "2561", [], "พระราชบัญญัติ"),
    "จัดซื้อจัดจ้าง":        ("จัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ", "2560", [],                       "พระราชบัญญัติ"),
    "มหาชน":              ("บริษัทมหาชนจำกัด พ.ศ. 2535",      None,   ["ยกเลิก"],                "พระราชบัญญัติ"),
    "รัฐธรรมนูญ":           ("รัฐธรรมนูญแห่งราชอาณาจักรไทย",     "2560", ["แก้ไขเพิ่มเติม", "ชั่วคราว"], "รัฐธรรมนูญ"),
    "ละเมิดเจ้าหน้าที่":      ("ความรับผิดทางละเมิดของเจ้าหน้าที่ พ.ศ. 2539", None, [],              "พระราชบัญญัติ"),
    "ฮั้วประมูล":           ("ความผิดเกี่ยวกับการเสนอราคาต่อหน่วยงานของรัฐ พ.ศ. 2542", None, [],     "พระราชบัญญัติ"),
    "เช่าอสังหาฯ":          ("เช่าอสังหาริมทรัพย์เพื่อพาณิชยกรรมและอุตสาหกรรม พ.ศ. 2542", None, [],   "พระราชบัญญัติ"),
}


def load_latest_records():
    cache_root = Path.home() / ".cache/huggingface/hub/datasets--open-law-data-thailand--ocs-krisdika/snapshots"
    snapshot_dir = next(cache_root.iterdir())
    jsonl_files = sorted((snapshot_dir / "data").rglob("*.jsonl"))
    print(f"[INDEX] Reading {len(jsonl_files)} JSONL files from HF cache...")

    records = []
    for f in jsonl_files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if row.get("is_latest"):
                    records.append({
                        "title": row.get("title", ""),
                        "law_code": row.get("law_code", ""),
                        "reference_url": row.get("reference_url", ""),
                        "raw_enc_id": row.get("raw_enc_id", ""),
                        "year": row.get("year", ""),
                    })
            except json.JSONDecodeError:
                pass

    print(f"[INDEX] {len(records)} records with is_latest=True")
    return records


def find_best_match(records, pattern, preferred_year, exclude_keywords, must_startswith):
    candidates = [r for r in records
                  if pattern in r["title"]
                  and r["title"].startswith(must_startswith)]

    if exclude_keywords:
        candidates = [r for r in candidates
                      if not any(ex in r["title"] for ex in exclude_keywords)]

    if not candidates:
        return None, []

    # Strict year match wins (over startswith filter already applied)
    if preferred_year:
        year_match = [r for r in candidates if preferred_year in r["title"]]
        if year_match:
            return year_match[0], candidates

    # Otherwise: prefer shortest title (root act over amendments) then earliest year
    candidates.sort(key=lambda r: (len(r["title"]), int(r.get("year", "9999") or "9999")))
    return candidates[0], candidates


def main():
    records = load_latest_records()
    print()
    print("=" * 70)
    print("LAS-WEB-CARDS-20260430 — OCS Direct-Link Build")
    print("=" * 70)
    print()

    output = {}
    misses = []

    for key, (pattern, year, exclude, must_startswith) in TARGETS.items():
        best, all_matches = find_best_match(records, pattern, year, exclude, must_startswith)

        if best:
            output[key] = {
                "title": best["title"],
                "law_code": best["law_code"],
                "reference_url": best["reference_url"],
                "raw_enc_id": best["raw_enc_id"],
                "year": best["year"],
                "candidates_total": len(all_matches),
            }
            year_tag = f" [{year}]" if year else ""
            print(f"[OK]   {key!r}{year_tag}")
            print(f"       title    : {best['title'][:90]}")
            print(f"       law_code : {best['law_code']}")
            print(f"       year     : {best['year']}")
            print(f"       url      : {best['reference_url']}")
            if len(all_matches) > 1:
                print(f"       (chose 1 of {len(all_matches)} matches)")
        else:
            misses.append(key)
            print(f"[MISS] {key!r} — pattern {pattern!r} not found")
        print()

    print("=" * 70)
    print(f"SUMMARY: {len(output)}/{len(TARGETS)} mapped, {len(misses)} miss")
    if misses:
        print(f"MISSES: {misses}")
    print("=" * 70)

    # Write JSON output
    out_path = Path(__file__).parent.parent / "data" / "ocs-direct-links.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n[WRITE] {out_path}")
    print(f"        {out_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
