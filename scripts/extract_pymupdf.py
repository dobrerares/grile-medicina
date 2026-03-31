"""Extract text from PDFs with embedded text using PyMuPDF (fitz).

Writes one .md file per PDF to extracted/pymupdf/.
"""

import fitz  # PyMuPDF
from pathlib import Path


# PDFs known to have embedded text
PDFS_WITH_TEXT = [
    "Biologie 2009 UMFCD .pdf",
    "Biologie 2012 UMFCD .pdf",
    "Biologie 2013 UMFCD .pdf",
    "Biologie 2014 UMFCD.pdf",
    "Biologie 2015 UMFCD.pdf",
    "Biologie 2017 UMFCD.pdf",
]


def extract_pdf(pdf_path: Path, output_path: Path) -> dict:
    """Extract text from a PDF and write it as markdown with page markers.

    Returns a dict with stats: page_count, avg_chars, output_file.
    """
    doc = fitz.open(pdf_path)
    pages = []
    total_chars = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        pages.append(text)
        total_chars += len(text)

    doc.close()

    page_count = len(pages)
    avg_chars = total_chars / page_count if page_count > 0 else 0

    # Write output as markdown with page markers
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, page_text in enumerate(pages):
            if i > 0:
                f.write(f"\n<!-- PAGE {i + 1} -->\n\n")
            else:
                f.write(f"<!-- PAGE {i + 1} -->\n\n")
            f.write(page_text)

    return {
        "page_count": page_count,
        "avg_chars": avg_chars,
        "output_file": output_path.name,
    }


def main():
    project_root = Path(__file__).parent.parent
    pdfs_dir = project_root / "pdfs"
    output_dir = project_root / "extracted" / "pymupdf"
    output_dir.mkdir(parents=True, exist_ok=True)

    for pdf_name in PDFS_WITH_TEXT:
        pdf_path = pdfs_dir / pdf_name
        if not pdf_path.exists():
            print(f"ERROR: {pdf_name} not found at {pdf_path}")
            continue

        output_filename = pdf_path.stem + ".md"
        output_path = output_dir / output_filename

        stats = extract_pdf(pdf_path, output_path)

        # Quality check
        warning = ""
        if stats["avg_chars"] < 50:
            warning = " ⚠ WARNING: avg chars/page < 50, may need OCR instead"

        print(
            f"{pdf_name}: {stats['page_count']} pages, "
            f"avg {stats['avg_chars']:.0f} chars/page, "
            f"-> {stats['output_file']}{warning}"
        )


if __name__ == "__main__":
    main()
