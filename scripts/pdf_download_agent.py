#!/usr/bin/env python3
"""
PDF Download Agent for Thai Law Dataset
========================================
Downloads all PDF law files from HuggingFace dataset:
  open-law-data-thailand/ocs-krisdika

Usage:
    pip install datasets huggingface_hub requests tqdm
    python pdf_download_agent.py [--output-dir thai_law_pdfs] [--workers 4] [--delay 0.5]
"""

import argparse
import csv
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pdf_download_agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# PDF magic bytes signature
PDF_MAGIC = b"%PDF"


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Remove characters that are unsafe in filenames."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = name.strip(". ")
    return name[:max_len] if name else "unknown"


def is_valid_pdf(data: bytes) -> bool:
    """Return True if bytes start with the PDF magic signature."""
    return data[:4] == PDF_MAGIC


def download_pdf(
    session: requests.Session,
    url: str,
    dest: Path,
    retries: int = 3,
    timeout: int = 60,
) -> bool:
    """
    Download a single PDF from *url* and save to *dest*.

    Returns True on success, False on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout, stream=True)
            response.raise_for_status()

            data = response.content
            if not is_valid_pdf(data):
                logger.warning("Not a valid PDF (bad magic bytes): %s", url)
                return False

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return True

        except requests.RequestException as exc:
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential back-off

    return False


def get_pdf_url(row: dict) -> str | None:
    """
    Inspect common field names that may contain a PDF URL.

    Adjust this list after inspecting dataset[0] if the field name differs.
    """
    for field in ("pdf_url", "url", "link", "file_url", "source_url", "document_url"):
        value = row.get(field)
        if isinstance(value, str) and value.startswith("http"):
            return value
    return None


def get_title(row: dict) -> str:
    """Return a sanitised title string suitable for use in a filename."""
    for field in ("title", "name", "law_name", "short_title", "id"):
        value = row.get(field)
        if value:
            return sanitize_filename(str(value))
    return "unknown"


def load_dataset_lazy():
    """Load the HuggingFace dataset and print schema info."""
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        logger.error("Package 'datasets' not installed. Run: pip install datasets")
        raise

    logger.info("Loading dataset open-law-data-thailand/ocs-krisdika …")
    dataset = load_dataset("open-law-data-thailand/ocs-krisdika", split="train")

    logger.info("Dataset features: %s", dataset.features)
    logger.info("Total records: %d", len(dataset))
    logger.info("First record sample: %s", dataset[0])

    return dataset


def write_csv_header(csv_path: Path) -> None:
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "title", "url", "filename", "status", "timestamp"])


def append_csv_row(csv_path: Path, row: list) -> None:
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def process_row(
    args_tuple,
):
    """Worker function used by the thread pool."""
    (
        idx,
        row,
        output_dir,
        csv_path,
        delay,
        session,
    ) = args_tuple

    url = get_pdf_url(row)
    title = get_title(row)
    filename = f"{idx:05d}_{title}.pdf"
    dest = output_dir / filename

    # --- Resume: skip already-downloaded files ---
    if dest.exists() and dest.stat().st_size > 0:
        logger.debug("Skipping (already exists): %s", filename)
        append_csv_row(csv_path, [idx, title, url or "", filename, "skipped", datetime.utcnow().isoformat()])
        return True, idx

    if not url:
        logger.warning("No PDF URL found for record %d (title=%s)", idx, title)
        append_csv_row(csv_path, [idx, title, "", filename, "no_url", datetime.utcnow().isoformat()])
        return False, idx

    # --- Rate limiting ---
    if delay > 0:
        time.sleep(delay)

    success = download_pdf(session, url, dest)
    status = "ok" if success else "failed"
    append_csv_row(csv_path, [idx, title, url, filename, status, datetime.utcnow().isoformat()])

    if success:
        logger.info("[%d] Downloaded: %s", idx, filename)
    else:
        logger.error("[%d] Failed: %s  url=%s", idx, filename, url)

    return success, idx


def run(output_dir: Path, workers: int, delay: float) -> None:
    dataset = load_dataset_lazy()

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "download_log.csv"
    write_csv_header(csv_path)

    session = requests.Session()
    session.headers.update({"User-Agent": "pdf-download-agent/1.0 (Thai law research)"})

    total = len(dataset)
    success_count = 0
    fail_count = 0

    task_args = [
        (idx, dataset[idx], output_dir, csv_path, delay, session)
        for idx in range(total)
    ]

    logger.info("Starting download: %d records, %d workers, %.1fs delay", total, workers, delay)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_row, args): args[0] for args in task_args}

        with tqdm(total=total, desc="Downloading PDFs", unit="file") as pbar:
            for future in as_completed(futures):
                ok, idx = future.result()
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
                pbar.update(1)
                pbar.set_postfix(ok=success_count, fail=fail_count)

    logger.info(
        "Done. Success: %d | Failed: %d | Total: %d",
        success_count,
        fail_count,
        total,
    )
    logger.info("Log saved to: %s", csv_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download all PDF law files from open-law-data-thailand/ocs-krisdika"
    )
    parser.add_argument(
        "--output-dir",
        default="thai_law_pdfs",
        help="Directory to save downloaded PDFs (default: thai_law_pdfs)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel download threads (default: 4)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between requests per worker (default: 0.5)",
    )
    args = parser.parse_args()

    run(
        output_dir=Path(args.output_dir),
        workers=args.workers,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
