"""Extract text from image-only PDFs using Mistral OCR API.

Sends PDFs as base64 to Mistral's OCR endpoint. Handles PDF splitting
for files over 45MB (Mistral limit is 50MB). Outputs one JSON file per
PDF to extracted/mistral/.

Usage:
    python scripts/extract_mistral.py              # process all OCR PDFs
    python scripts/extract_mistral.py "2011"       # process PDFs matching "2011"

Requires MISTRAL_API_KEY environment variable.
"""

import base64
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import fitz  # PyMuPDF
from mistralai import Mistral

# PDFs known to be image-only (need OCR)
OCR_PDFS = [
    "Biologie 2008 UMFCD .pdf",
    "Biologie 2010 UMFCD.pdf",
    "Biologie 2010 UMFCD .pdf",
    "Biologie 2011 UMFCD .pdf",
    "Biologie 2016 UMFCD.pdf",
    "Biologie 2016 UMFCD-.pdf",
    "Biologie 2019 UMFCD.pdf",
    "Biologie 2020 UMFCD.pdf",
    "Biologie 2020 UMFCD-.pdf",
    "Biologie 2021 UMFCD.pdf",
    "Biologie 2022 UMFCD.pdf",
    "Carte grile bio 2023 (1).pdf",
]

MAX_FILE_SIZE_MB = 45
PAGES_PER_CHUNK = 100
MODEL = "mistral-ocr-latest"


def pdf_to_base64(pdf_path: Path) -> str:
    """Read a PDF file and return its base64 encoding."""
    with open(pdf_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def split_pdf(pdf_path: Path, pages_per_chunk: int = PAGES_PER_CHUNK) -> list[Path]:
    """Split a PDF into chunks of pages_per_chunk pages each.

    Returns a list of paths to temporary chunk files (caller must clean up).
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    chunk_paths = []

    for start in range(0, total_pages, pages_per_chunk):
        end = min(start + pages_per_chunk, total_pages)
        chunk_doc = fitz.open()  # new empty PDF
        chunk_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

        # Write to a temp file
        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf", prefix=f"chunk_{start}_", delete=False
        )
        chunk_doc.save(tmp.name)
        chunk_doc.close()
        tmp.close()

        chunk_paths.append(Path(tmp.name))
        print(f"  Split: pages {start + 1}-{end} -> {tmp.name}")

    doc.close()
    return chunk_paths


def ocr_pdf(client: Mistral, pdf_path: Path) -> list[dict]:
    """Send a single PDF to Mistral OCR and return list of page dicts.

    Each dict has 'index' (int) and 'markdown' (str).
    """
    b64 = pdf_to_base64(pdf_path)
    response = client.ocr.process(
        model=MODEL,
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64}",
        },
    )
    return [{"index": page.index, "markdown": page.markdown} for page in response.pages]


def process_pdf(client: Mistral, pdf_path: Path, output_path: Path) -> dict:
    """OCR a single PDF, handling splitting if needed.

    Returns a dict with stats: page_count, output_file.
    """
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"  Size: {file_size_mb:.1f} MB")

    if file_size_mb <= MAX_FILE_SIZE_MB:
        # Small enough to send directly
        pages = ocr_pdf(client, pdf_path)
    else:
        # Split into chunks, OCR each, combine
        print(f"  File exceeds {MAX_FILE_SIZE_MB}MB, splitting...")
        chunk_paths = split_pdf(pdf_path)
        pages = []
        page_offset = 0

        try:
            for i, chunk_path in enumerate(chunk_paths):
                if i > 0:
                    print("  Waiting 2s between chunks (rate limit)...")
                    time.sleep(2)

                print(f"  OCR chunk {i + 1}/{len(chunk_paths)}...")
                chunk_pages = ocr_pdf(client, chunk_path)

                # Re-index pages to be continuous across chunks
                for page in chunk_pages:
                    pages.append({
                        "index": page_offset + page["index"],
                        "markdown": page["markdown"],
                    })
                page_offset += len(chunk_pages)
        finally:
            # Clean up temp files
            for chunk_path in chunk_paths:
                try:
                    chunk_path.unlink()
                except OSError:
                    pass

    # Write output JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {"file": pdf_path.name, "pages": pages}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "page_count": len(pages),
        "output_file": output_path.name,
    }


def main():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY environment variable not set")
        sys.exit(1)

    client = Mistral(api_key=api_key)

    project_root = Path(__file__).parent.parent
    pdfs_dir = project_root / "pdfs"
    output_dir = project_root / "extracted" / "mistral"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter PDFs if a search term is provided
    pdfs_to_process = OCR_PDFS
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        pdfs_to_process = [p for p in OCR_PDFS if search_term in p]
        if not pdfs_to_process:
            print(f"No PDFs matching '{search_term}' found in OCR_PDFS list")
            sys.exit(1)
        print(f"Filtering to {len(pdfs_to_process)} PDF(s) matching '{search_term}'")

    processed = 0
    skipped = 0
    errors = 0

    for i, pdf_name in enumerate(pdfs_to_process):
        pdf_path = pdfs_dir / pdf_name
        output_path = output_dir / (pdf_path.stem + ".json")

        print(f"\n[{i + 1}/{len(pdfs_to_process)}] {pdf_name}")

        # Skip if already processed
        if output_path.exists():
            print(f"  SKIP: {output_path.name} already exists")
            skipped += 1
            continue

        if not pdf_path.exists():
            print(f"  ERROR: PDF not found at {pdf_path}")
            errors += 1
            continue

        # Rate limit between files
        if processed > 0:
            print("  Waiting 1s between files (rate limit)...")
            time.sleep(1)

        try:
            stats = process_pdf(client, pdf_path, output_path)
            print(f"  OK: {stats['page_count']} pages -> {stats['output_file']}")
            processed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

    print(f"\nDone: {processed} processed, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
