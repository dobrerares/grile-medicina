"""Normalize extracted text: fix Romanian diacritics and clean up whitespace.

Reads from extracted/pymupdf/ (.md) and extracted/mistral/ (.json),
writes cleaned .md files to extracted/normalized/.
"""

import json
import re
from pathlib import Path

# Cedilla → comma-below mappings for Romanian diacritics
DIACRITICS_MAP = str.maketrans({
    "\u015f": "\u0219",  # ş → ș
    "\u0163": "\u021b",  # ţ → ț
    "\u015e": "\u0218",  # Ş → Ș
    "\u0162": "\u021a",  # Ţ → Ț
})


def fix_diacritics(text: str) -> str:
    """Replace cedilla variants with comma-below variants."""
    return text.translate(DIACRITICS_MAP)


def normalize_whitespace(text: str) -> str:
    """Collapse 4+ consecutive blank lines to 2, strip trailing whitespace."""
    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines)

    # Collapse 4+ consecutive newlines (i.e. 3+ blank lines) down to 3
    # (which gives 2 blank lines between content)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Ensure file ends with a single newline
    text = text.rstrip("\n") + "\n"

    return text


def normalize(text: str) -> str:
    """Apply all normalization steps."""
    text = fix_diacritics(text)
    text = normalize_whitespace(text)
    return text


def read_pymupdf(path: Path) -> str:
    """Read a PyMuPDF .md file as-is."""
    return path.read_text(encoding="utf-8")


def read_mistral(path: Path) -> str:
    """Read a Mistral JSON file, combining pages into markdown with page markers."""
    data = json.loads(path.read_text(encoding="utf-8"))
    pages = data.get("pages", [])

    parts = []
    for page in pages:
        page_num = page["index"] + 1  # Mistral uses 0-based index
        markdown = page.get("markdown", "")
        if parts:
            parts.append(f"\n<!-- PAGE {page_num} -->\n\n{markdown}")
        else:
            parts.append(f"<!-- PAGE {page_num} -->\n\n{markdown}")

    return "".join(parts)


def main():
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "extracted" / "normalized"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = []

    # Collect PyMuPDF sources
    pymupdf_dir = project_root / "extracted" / "pymupdf"
    if pymupdf_dir.exists():
        for md_file in sorted(pymupdf_dir.glob("*.md")):
            sources.append(("pymupdf", md_file))

    # Collect Mistral sources
    mistral_dir = project_root / "extracted" / "mistral"
    if mistral_dir.exists():
        for json_file in sorted(mistral_dir.glob("*.json")):
            sources.append(("mistral", json_file))

    if not sources:
        print("No source files found.")
        return

    for source_type, source_path in sources:
        if source_type == "pymupdf":
            raw_text = read_pymupdf(source_path)
            output_name = source_path.name  # already .md
        else:
            raw_text = read_mistral(source_path)
            output_name = source_path.stem + ".md"  # .json → .md

        normalized_text = normalize(raw_text)
        output_path = output_dir / output_name

        output_path.write_text(normalized_text, encoding="utf-8")

        # Count fixes applied
        cedilla_count = sum(
            raw_text.count(c) for c in "\u015f\u0163\u015e\u0162"
        )
        print(
            f"{source_type}/{source_path.name} -> {output_name}"
            f"  ({cedilla_count} diacritics fixed)"
        )


if __name__ == "__main__":
    main()
