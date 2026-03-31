# OCR Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python pipeline that extracts all multiple-choice questions from ~19 medical exam PDFs into a single structured JSON file.

**Architecture:** Two-phase pipeline — Phase 1 extracts raw text (PyMuPDF for text PDFs, Mistral OCR API for scanned PDFs). Phase 2 parses, validates, deduplicates, and merges into the final `output/grile.json`. Each step is a standalone script that reads from a known directory and writes to the next.

**Tech Stack:** Python 3.12, PyMuPDF (fitz), mistralai SDK, rapidfuzz (for deduplication). All managed via a Nix flake.

**Design doc:** `docs/plans/2026-03-31-ocr-pipeline-design.md`

---

### Task 1: Project scaffolding and Nix flake

**Files:**
- Create: `flake.nix`
- Create: `scripts/__init__.py` (empty)
- Move PDFs into `pdfs/` directory
- Create: `extracted/pymupdf/.gitkeep`, `extracted/mistral/.gitkeep`, `parsed/.gitkeep`, `output/.gitkeep`

**Step 1: Create directory structure**

```bash
mkdir -p pdfs extracted/pymupdf extracted/mistral parsed output scripts
touch scripts/__init__.py
touch extracted/pymupdf/.gitkeep extracted/mistral/.gitkeep parsed/.gitkeep output/.gitkeep
```

**Step 2: Move PDFs**

```bash
mv *.pdf pdfs/
```

**Step 3: Create flake.nix**

```nix
{
  description = "Grile Medicina OCR Pipeline";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
        pythonPkgs = python.pkgs;
      in {
        devShells.default = pkgs.mkShell {
          packages = [
            (python.withPackages (ps: [
              ps.pymupdf
              ps.pip
            ]))
          ];

          shellHook = ''
            # Create venv for pip-only packages (mistralai, rapidfuzz)
            if [ ! -d .venv ]; then
              python -m venv .venv --system-site-packages
              .venv/bin/pip install mistralai rapidfuzz
            fi
            source .venv/bin/activate
          '';
        };
      });
}
```

**Step 4: Verify the environment**

```bash
nix develop
python -c "import fitz; print('PyMuPDF OK')"
python -c "from mistralai import Mistral; print('Mistral SDK OK')"
python -c "from rapidfuzz import fuzz; print('rapidfuzz OK')"
```

**Step 5: Create .gitignore**

```
.venv/
__pycache__/
extracted/pymupdf/*.md
extracted/mistral/*.json
parsed/*.json
output/*.json
pdfs/*.pdf
*.pyc
.env
```

Note: PDFs are gitignored (too large). The extracted/parsed/output files are regenerable.

**Step 6: Create .env.example**

```
MISTRAL_API_KEY=your-key-here
```

**Step 7: Commit**

```bash
git init
git add flake.nix flake.lock scripts/__init__.py .gitignore .env.example \
  extracted/pymupdf/.gitkeep extracted/mistral/.gitkeep parsed/.gitkeep output/.gitkeep \
  docs/plans/
git commit -m "chore: scaffold project structure and nix flake"
```

---

### Task 2: PyMuPDF text extraction script

**Files:**
- Create: `scripts/extract_pymupdf.py`
- Test: manual inspection of output files

This script extracts text from PDFs that have embedded text and writes one `.md` file per PDF to `extracted/pymupdf/`.

**Step 1: Create `scripts/extract_pymupdf.py`**

```python
#!/usr/bin/env python3
"""Extract text from PDFs with embedded text using PyMuPDF."""

import fitz
import os
import sys
from pathlib import Path

# PDFs known to have embedded text (verified by analysis)
TEXT_PDFS = [
    "Biologie 2009 UMFCD .pdf",
    "Biologie 2012 UMFCD .pdf",
    "Biologie 2013 UMFCD .pdf",
    "Biologie 2014 UMFCD.pdf",
    "Biologie 2015 UMFCD.pdf",
    "Biologie 2017 UMFCD.pdf",
    "BIOL 2025- .pdf",
]

# Minimum chars per page to consider text extraction successful
MIN_CHARS_PER_PAGE = 50


def extract_pdf(pdf_path: Path, output_dir: Path) -> dict:
    """Extract text from a single PDF. Returns stats dict."""
    doc = fitz.open(str(pdf_path))
    pages = []
    total_chars = 0

    for i in range(len(doc)):
        text = doc[i].get_text()
        pages.append(text)
        total_chars += len(text.strip())

    doc.close()

    avg_chars = total_chars / len(pages) if pages else 0
    stem = pdf_path.stem

    if avg_chars < MIN_CHARS_PER_PAGE:
        print(f"  WARNING: {stem} has only {avg_chars:.0f} avg chars/page — may need OCR instead")
        return {"file": pdf_path.name, "pages": len(pages), "avg_chars": avg_chars, "status": "low_quality"}

    # Write output as markdown with page markers
    output_path = output_dir / f"{stem}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        for i, text in enumerate(pages):
            f.write(f"\n\n<!-- PAGE {i+1} -->\n\n")
            f.write(text)

    print(f"  OK: {stem} — {len(pages)} pages, {avg_chars:.0f} avg chars/page → {output_path.name}")
    return {"file": pdf_path.name, "pages": len(pages), "avg_chars": avg_chars, "status": "ok"}


def main():
    project_root = Path(__file__).parent.parent
    pdf_dir = project_root / "pdfs"
    output_dir = project_root / "extracted" / "pymupdf"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_dir.exists():
        print(f"ERROR: {pdf_dir} does not exist. Move PDFs there first.")
        sys.exit(1)

    results = []
    for filename in TEXT_PDFS:
        pdf_path = pdf_dir / filename
        if not pdf_path.exists():
            print(f"  SKIP: {filename} not found")
            continue
        result = extract_pdf(pdf_path, output_dir)
        results.append(result)

    print(f"\nDone. Extracted {len([r for r in results if r['status'] == 'ok'])} / {len(results)} PDFs.")
    low_quality = [r for r in results if r["status"] == "low_quality"]
    if low_quality:
        print(f"Low quality (need OCR): {[r['file'] for r in low_quality]}")


if __name__ == "__main__":
    main()
```

**Step 2: Run and verify**

```bash
python scripts/extract_pymupdf.py
```

Expected: 7 `.md` files created in `extracted/pymupdf/`. Check one manually:

```bash
head -100 extracted/pymupdf/"Biologie 2014 UMFCD.md"
```

Verify questions, choices, and diacritics are readable.

**Step 3: Commit**

```bash
git add scripts/extract_pymupdf.py
git commit -m "feat: add PyMuPDF text extraction script"
```

---

### Task 3: Mistral OCR extraction script

**Files:**
- Create: `scripts/extract_mistral.py`
- Test: run on one small PDF first, then all

This script sends image-only PDFs to the Mistral OCR API. PDFs over 50MB are split into chunks first. Output is one JSON file per PDF in `extracted/mistral/` containing the per-page markdown from Mistral's response.

**Step 1: Create `scripts/extract_mistral.py`**

```python
#!/usr/bin/env python3
"""Extract text from scanned PDFs using Mistral OCR API."""

import base64
import json
import os
import sys
import time
from pathlib import Path

import fitz
from mistralai import Mistral

# PDFs that need OCR (image-only or low-quality text)
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

MAX_FILE_SIZE_MB = 45  # Stay under Mistral's 50MB limit
MAX_PAGES_PER_CHUNK = 200  # Stay under Mistral's 1000 page limit


def split_pdf(pdf_path: Path, max_size_mb: float, max_pages: int) -> list[Path]:
    """Split a PDF into chunks if it exceeds size/page limits. Returns list of paths."""
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    if file_size_mb <= max_size_mb and total_pages <= max_pages:
        doc.close()
        return [pdf_path]

    # Split into chunks
    chunks = []
    pages_per_chunk = min(max_pages, max(10, total_pages // max(1, int(file_size_mb / max_size_mb))))

    for start in range(0, total_pages, pages_per_chunk):
        end = min(start + pages_per_chunk, total_pages)
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

        chunk_path = pdf_path.parent / f"{pdf_path.stem}_chunk_{start}_{end}.pdf"
        chunk_doc.save(str(chunk_path))
        chunk_doc.close()
        chunks.append(chunk_path)
        print(f"    Split: pages {start+1}-{end} → {chunk_path.name}")

    doc.close()
    return chunks


def ocr_pdf(client: Mistral, pdf_path: Path) -> list[dict]:
    """Send a PDF to Mistral OCR and return per-page results."""
    with open(pdf_path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    result = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64}",
        },
    )

    return [{"index": p.index, "markdown": p.markdown} for p in result.pages]


def process_pdf(client: Mistral, pdf_path: Path, output_dir: Path) -> dict:
    """Process a single PDF (splitting if needed) and save results."""
    stem = pdf_path.stem
    output_path = output_dir / f"{stem}.json"

    if output_path.exists():
        print(f"  SKIP (already exists): {output_path.name}")
        return {"file": pdf_path.name, "status": "skipped"}

    print(f"  Processing: {pdf_path.name}")
    chunks = split_pdf(pdf_path, MAX_FILE_SIZE_MB, MAX_PAGES_PER_CHUNK)

    all_pages = []
    page_offset = 0

    for i, chunk_path in enumerate(chunks):
        print(f"    OCR chunk {i+1}/{len(chunks)}: {chunk_path.name}")
        try:
            pages = ocr_pdf(client, chunk_path)
            # Adjust page indices for chunks
            for p in pages:
                p["index"] = p["index"] + page_offset
            all_pages.extend(pages)
            page_offset += len(pages)
        except Exception as e:
            print(f"    ERROR on chunk {i+1}: {e}")
            return {"file": pdf_path.name, "status": "error", "error": str(e)}
        finally:
            # Clean up temp chunk files
            if chunk_path != pdf_path:
                chunk_path.unlink()

        # Rate limit: pause between chunks
        if i < len(chunks) - 1:
            time.sleep(2)

    # Save results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"file": pdf_path.name, "pages": all_pages}, f, ensure_ascii=False, indent=2)

    print(f"  OK: {stem} — {len(all_pages)} pages → {output_path.name}")
    return {"file": pdf_path.name, "pages": len(all_pages), "status": "ok"}


def main():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: Set MISTRAL_API_KEY environment variable")
        print("  export MISTRAL_API_KEY=your-key-here")
        sys.exit(1)

    client = Mistral(api_key=api_key)

    project_root = Path(__file__).parent.parent
    pdf_dir = project_root / "pdfs"
    output_dir = project_root / "extracted" / "mistral"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Optional: process a single file for testing
    if len(sys.argv) > 1:
        target = sys.argv[1]
        matching = [f for f in OCR_PDFS if target in f]
        if not matching:
            print(f"No matching PDF for '{target}'. Available: {OCR_PDFS}")
            sys.exit(1)
        pdfs_to_process = matching
    else:
        pdfs_to_process = OCR_PDFS

    results = []
    for filename in pdfs_to_process:
        pdf_path = pdf_dir / filename
        if not pdf_path.exists():
            print(f"  SKIP: {filename} not found")
            continue
        result = process_pdf(client, pdf_path, output_dir)
        results.append(result)
        # Pause between files to be nice to the API
        time.sleep(1)

    ok = len([r for r in results if r["status"] == "ok"])
    print(f"\nDone. OCR'd {ok} / {len(results)} PDFs.")


if __name__ == "__main__":
    main()
```

**Step 2: Test with the smallest image PDF first**

```bash
export MISTRAL_API_KEY=your-key-here
python scripts/extract_mistral.py "2011"
```

Expected: `extracted/mistral/Biologie 2011 UMFCD .json` created (90 pages). Inspect the output:

```bash
python -c "
import json
with open('extracted/mistral/Biologie 2011 UMFCD .json') as f:
    data = json.load(f)
print(f'Pages: {len(data[\"pages\"])}')
print('First page markdown:')
print(data['pages'][0]['markdown'][:500])
"
```

Verify Romanian diacritics and question structure are preserved.

**Step 3: Run on all image PDFs**

```bash
python scripts/extract_mistral.py
```

This will take a while (~20-40 minutes for all files). The script skips already-processed files, so it's safe to re-run if interrupted.

**Step 4: Commit**

```bash
git add scripts/extract_mistral.py .env.example
git commit -m "feat: add Mistral OCR extraction script with PDF splitting"
```

---

### Task 4: Text normalizer

**Files:**
- Create: `scripts/normalize.py`
- Test: run on extracted files, diff before/after

The normalizer reads all extracted text (from both pymupdf and mistral), fixes diacritics, normalizes whitespace, and writes cleaned `.md` files to a common location.

**Step 1: Create `scripts/normalize.py`**

```python
#!/usr/bin/env python3
"""Normalize extracted text: fix diacritics, whitespace, encoding issues."""

import json
import re
from pathlib import Path

# Romanian diacritics: cedilla variants → comma-below variants
DIACRITIC_MAP = {
    "ş": "ș",  # s-cedilla → s-comma-below
    "Ş": "Ș",
    "ţ": "ț",  # t-cedilla → t-comma-below
    "Ţ": "Ț",
}


def fix_diacritics(text: str) -> str:
    """Replace cedilla variants with correct comma-below variants."""
    for old, new in DIACRITIC_MAP.items():
        text = text.replace(old, new)
    return text


def normalize_whitespace(text: str) -> str:
    """Clean up excessive whitespace while preserving structure."""
    # Replace multiple blank lines with max 2
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Remove trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text


def normalize_text(text: str) -> str:
    """Apply all normalization steps."""
    text = fix_diacritics(text)
    text = normalize_whitespace(text)
    return text


def process_pymupdf(input_dir: Path, output_dir: Path):
    """Normalize PyMuPDF extracted files."""
    for md_file in sorted(input_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        normalized = normalize_text(text)
        out_path = output_dir / md_file.name
        out_path.write_text(normalized, encoding="utf-8")
        print(f"  PyMuPDF: {md_file.name} → {out_path.name}")


def process_mistral(input_dir: Path, output_dir: Path):
    """Normalize Mistral OCR JSON → markdown files."""
    for json_file in sorted(input_dir.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        pages = data.get("pages", [])
        parts = []
        for page in pages:
            idx = page["index"]
            md = page["markdown"]
            parts.append(f"\n\n<!-- PAGE {idx + 1} -->\n\n{md}")

        text = "\n".join(parts)
        normalized = normalize_text(text)

        out_path = output_dir / f"{json_file.stem}.md"
        out_path.write_text(normalized, encoding="utf-8")
        print(f"  Mistral: {json_file.name} → {out_path.name}")


def main():
    project_root = Path(__file__).parent.parent
    pymupdf_dir = project_root / "extracted" / "pymupdf"
    mistral_dir = project_root / "extracted" / "mistral"
    output_dir = project_root / "extracted" / "normalized"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Normalizing PyMuPDF files...")
    process_pymupdf(pymupdf_dir, output_dir)

    print("Normalizing Mistral OCR files...")
    process_mistral(mistral_dir, output_dir)

    count = len(list(output_dir.glob("*.md")))
    print(f"\nDone. {count} normalized files in {output_dir}")


if __name__ == "__main__":
    main()
```

**Step 2: Run**

```bash
python scripts/normalize.py
```

**Step 3: Spot-check diacritics fix**

```bash
# Should find no cedilla variants in normalized output
grep -rP '[şţŞŢ]' extracted/normalized/ | head -5
```

Expected: no matches (all converted to comma-below).

**Step 4: Commit**

```bash
git add scripts/normalize.py
git commit -m "feat: add text normalizer for diacritics and whitespace"
```

---

### Task 5: Question parser

**Files:**
- Create: `scripts/parse.py`
- Test: run on 2014 (best-structured text PDF) first, validate output manually

This is the core script. It reads normalized markdown and extracts structured questions, section headers, answer keys, and matches them together. Outputs one JSON per source file to `parsed/`.

**Step 1: Create `scripts/parse.py`**

The parser works in passes:
1. Split the document into test sections (by chapter/topic headers)
2. Within each section, extract questions (complement simplu, then complement grupat)
3. Find answer key sections and extract answer mappings
4. Match answers to questions

Key regex patterns observed from the text samples:

```
Question:     r"^(\d{1,3})\.\s*(.+)"              # "1. Question text" or "1.Question text"
Choice A-E:   r"^([A-E])[.)]\s*(.+)"               # "A) text" or "A. text" or "A.text"
Choice 1-4:   r"^(\d)[.)]\s*(.+)"                   # "1. text" or "1) text"
Section:      r"(COMPLEMENT\s+SIMPLU|COMPLEMENT\s+GRUPAT|COMPLEMENT\s+MULTIPLU)"
Answer key:   r"RĂSPUNSURI"
Answer line:  r"^(\d{1,3})\.\s*([A-E])"             # "1. C (pg.7)" or "1.C(pg.7)"
Topic header: r"(CELULA|SISTEMUL NERVOS|ANALIZATOR|GLAND|DIGESTIA|CIRCULAȚI|RESPIRAȚI|EXCREȚI|METABOLIS|REPRODUC|MIȘCAR|SISTEMUL OSOS|SISTEMUL MUSCULAR)"
```

```python
#!/usr/bin/env python3
"""Parse normalized text into structured question JSON."""

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Question:
    number: int
    type: str  # "complement_simplu" or "complement_grupat"
    text: str
    choices: dict[str, str] = field(default_factory=dict)
    correct_answer: Optional[str] = None
    correct_statements: Optional[list[int]] = None
    page_ref: Optional[str] = None


@dataclass
class Test:
    title: str
    author: Optional[str]
    topic: str
    test_type: str  # "chapter_test" or "general_test"
    questions: list[Question] = field(default_factory=list)


GRUPAT_DECODE = {
    "A": [1, 2, 3],
    "B": [1, 3],
    "C": [2, 4],
    "D": [4],
    "E": None,  # ambiguous
}

# Topic keywords → normalized topic name
TOPIC_MAP = {
    "CELUL": "celula",
    "ȚESUT": "celula",
    "TESUT": "celula",
    "SISTEMUL NERVOS": "sistemul_nervos",
    "ANALIZATOR": "analizatorii",
    "GLAND": "glande_endocrine",
    "ENDOCRIN": "glande_endocrine",
    "MIȘCAR": "miscarea",
    "MISCAR": "miscarea",
    "SISTEMUL OSOS": "sistemul_osos",
    "SISTEMUL MUSCULAR": "sistemul_muscular",
    "DIGESTIA": "digestia",
    "ABSORBȚI": "digestia",
    "ABSORBTIA": "digestia",
    "CIRCULAȚI": "circulatia",
    "CIRCULATIA": "circulatia",
    "RESPIRAȚI": "respiratia",
    "RESPIRATIA": "respiratia",
    "EXCREȚI": "excretia",
    "EXCRETIA": "excretia",
    "METABOLIS": "metabolismul",
    "REPRODUC": "reproducerea",
}


def detect_topic(text: str) -> str:
    """Detect topic from header text."""
    upper = text.upper()
    for keyword, topic in TOPIC_MAP.items():
        if keyword in upper:
            return topic
    return "general"


def extract_year(filename: str) -> int:
    """Extract year from filename like 'Biologie 2014 UMFCD.pdf'."""
    match = re.search(r"20\d{2}", filename)
    return int(match.group()) if match else 0


def parse_questions(lines: list[str]) -> list[Question]:
    """Parse a block of question text into Question objects."""
    questions = []
    current_q = None
    current_complement = "complement_simplu"
    collecting_text = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect complement type switch
        if re.search(r"COMPLEMENT\s+(GRUPAT|MULTIPLU)", line, re.IGNORECASE):
            current_complement = "complement_grupat"
            i += 1
            continue
        if re.search(r"COMPLEMENT\s+SIMPLU", line, re.IGNORECASE):
            current_complement = "complement_simplu"
            i += 1
            continue

        # Match question number: "1. Question text" or "1.Question text"
        q_match = re.match(r"^(\d{1,3})\.\s*(.+)", line)
        if q_match:
            num = int(q_match.group(1))
            text = q_match.group(2).strip()

            # Heuristic: if this looks like an answer choice (starts with A-E after number),
            # it's probably a continuation, not a new question
            if re.match(r"^[A-E][.)]\s", text):
                # This is a choice line that happened to start at a new line
                pass
            else:
                # Check if it's really a new question (number should be sequential-ish)
                if current_q is None or num != current_q.number:
                    if current_q:
                        questions.append(current_q)
                    current_q = Question(number=num, type=current_complement, text=text)
                    i += 1
                    continue

        # Match choices for complement simplu: A-E
        if current_q and current_q.type == "complement_simplu":
            choice_match = re.match(r"^([A-E])[.)]\s*(.*)", line)
            if choice_match:
                letter = choice_match.group(1)
                choice_text = choice_match.group(2).strip()
                current_q.choices[letter] = choice_text
                i += 1
                continue

        # Match choices for complement grupat: 1-4
        if current_q and current_q.type == "complement_grupat":
            stmt_match = re.match(r"^([1-4])[.)]\s*(.*)", line)
            if stmt_match:
                num_choice = stmt_match.group(1)
                choice_text = stmt_match.group(2).strip()
                current_q.choices[num_choice] = choice_text
                i += 1
                continue

        # Continuation of current question text or choice
        if current_q and line and not re.match(r"^(RĂSPUNSURI|COMPLEMENT|Întrebări)", line):
            # Append to the last thing we were building
            if current_q.choices:
                # Append to the last choice
                last_key = list(current_q.choices.keys())[-1]
                current_q.choices[last_key] += " " + line
            else:
                # Append to question text
                current_q.text += " " + line

        i += 1

    if current_q:
        questions.append(current_q)

    return questions


def parse_answers(lines: list[str]) -> dict[int, tuple[str, str]]:
    """Parse answer key lines. Returns {question_num: (letter, page_ref)}."""
    answers = {}
    for line in lines:
        line = line.strip()
        # Match patterns like: "1. C (pg.7)" or "1.C(pg.7)" or "1. C, pag. 7"
        m = re.match(
            r"^(\d{1,3})\.\s*([A-E])\s*[,.]?\s*\(?((?:pg|pag)\.?\s*[^)]*)\)?",
            line,
        )
        if m:
            num = int(m.group(1))
            letter = m.group(2)
            page_ref = m.group(3).strip().rstrip(",.)") if m.group(3) else None
            answers[num] = (letter, page_ref)
            continue

        # Simpler pattern: "1. C" or "1.C"
        m2 = re.match(r"^(\d{1,3})\.\s*([A-E])\b", line)
        if m2:
            num = int(m2.group(1))
            letter = m2.group(2)
            answers[num] = (letter, None)

    return answers


def split_into_sections(text: str) -> list[dict]:
    """Split document text into logical sections (chapters, tests, answer keys)."""
    lines = text.split("\n")
    sections = []
    current_section = {"type": "unknown", "title": "", "author": None, "lines": []}

    for line in lines:
        stripped = line.strip()

        # Detect answer key sections
        if re.match(r"^RĂSPUNSURI\s*:?\s*$", stripped, re.IGNORECASE):
            if current_section["lines"]:
                sections.append(current_section)
            current_section = {"type": "answers", "title": stripped, "author": None, "lines": []}
            continue

        # Detect chapter/topic headers (usually preceded by author line)
        if re.match(r"^Întrebări\s+realizate\s+de\s+", stripped):
            if current_section["lines"]:
                sections.append(current_section)
            author = re.sub(r"^Întrebări\s+realizate\s+de\s+", "", stripped).strip()
            current_section = {"type": "questions", "title": "", "author": author, "lines": []}
            continue

        # Detect topic headers
        topic = detect_topic(stripped)
        if topic != "general" and len(stripped) < 100 and not re.match(r"^\d", stripped):
            current_section["title"] = stripped
            current_section["topic"] = topic
            continue

        current_section["lines"].append(line)

    if current_section["lines"]:
        sections.append(current_section)

    return sections


def parse_file(md_path: Path, year: int) -> dict:
    """Parse a single normalized markdown file into structured data."""
    text = md_path.read_text(encoding="utf-8")
    sections = split_into_sections(text)

    tests = []
    current_test = None
    test_counter = 0

    for section in sections:
        if section["type"] == "questions":
            test_counter += 1
            topic = section.get("topic", "general")
            questions = parse_questions(section["lines"])

            test_id = f"{year}_{topic}_{test_counter}"
            current_test = {
                "test_id": test_id,
                "title": section.get("title", ""),
                "author": section.get("author"),
                "topic": topic,
                "type": "chapter_test" if topic != "general" else "general_test",
                "questions": [asdict(q) for q in questions],
            }
            tests.append(current_test)

        elif section["type"] == "answers" and current_test:
            answers = parse_answers(section["lines"])
            # Match answers to questions in the most recent test
            for q in current_test["questions"]:
                num = q["number"]
                if num in answers:
                    letter, page_ref = answers[num]
                    q["correct_answer"] = letter
                    q["page_ref"] = page_ref
                    if q["type"] == "complement_grupat":
                        q["correct_statements"] = GRUPAT_DECODE.get(letter)

    # Generate question IDs
    for test in tests:
        for q in test["questions"]:
            q["id"] = f"{test['test_id']}_q{q['number']}"

    return {
        "file": md_path.stem,
        "year": year,
        "subject": "biologie",
        "extraction_method": "pymupdf" if "pymupdf" in str(md_path) else "mistral_ocr",
        "tests": tests,
    }


def main():
    project_root = Path(__file__).parent.parent
    normalized_dir = project_root / "extracted" / "normalized"
    output_dir = project_root / "parsed"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not normalized_dir.exists():
        print(f"ERROR: {normalized_dir} does not exist. Run normalize.py first.")
        sys.exit(1)

    for md_file in sorted(normalized_dir.glob("*.md")):
        year = extract_year(md_file.name)
        print(f"Parsing: {md_file.name} (year={year})")

        try:
            result = parse_file(md_file, year)
            out_path = output_dir / f"{md_file.stem}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            total_q = sum(len(t["questions"]) for t in result["tests"])
            total_answered = sum(
                1 for t in result["tests"] for q in t["questions"] if q.get("correct_answer")
            )
            print(f"  → {len(result['tests'])} tests, {total_q} questions, {total_answered} with answers")
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone. Parsed files in {output_dir}")


if __name__ == "__main__":
    main()
```

**Step 2: Test on the best-structured file first**

```bash
python scripts/parse.py
# Then inspect 2014 output specifically:
python -c "
import json
with open('parsed/Biologie 2014 UMFCD.json') as f:
    data = json.load(f)
for t in data['tests']:
    answered = sum(1 for q in t['questions'] if q.get('correct_answer'))
    print(f\"{t['test_id']}: {t['title']} — {len(t['questions'])} questions, {answered} answered, topic={t['topic']}\")
    if t['questions']:
        q = t['questions'][0]
        print(f'  Sample: Q{q[\"number\"]}: {q[\"text\"][:80]}...')
        print(f'  Choices: {list(q[\"choices\"].keys())}')
        print(f'  Answer: {q.get(\"correct_answer\")}')
"
```

Expected: Multiple tests organized by topic, questions with matched answers.

**Step 3: Review and iterate**

The parser will likely need tuning for edge cases across different years. Common issues to watch for:
- Questions that span multiple lines (text continuation)
- Inconsistent numbering (some books restart numbering per chapter, others don't)
- Answer key format variations (some use parentheses, some don't)
- Pages where PyMuPDF extraction splits words oddly

After reviewing output from all files, adjust regex patterns in the parser.

**Step 4: Commit**

```bash
git add scripts/parse.py
git commit -m "feat: add regex-based question parser"
```

---

### Task 6: Validator

**Files:**
- Create: `scripts/validate.py`
- Test: run on all parsed JSONs

The validator checks parsed output for common issues and produces a report.

**Step 1: Create `scripts/validate.py`**

```python
#!/usr/bin/env python3
"""Validate parsed question JSON files for completeness and consistency."""

import json
import sys
from pathlib import Path


def validate_question(q: dict, test_id: str) -> list[str]:
    """Validate a single question. Returns list of issues."""
    issues = []
    qid = q.get("id", f"q{q['number']}")

    if not q.get("text") or len(q["text"]) < 5:
        issues.append(f"{test_id}/{qid}: question text too short or empty")

    if q["type"] == "complement_simplu":
        expected_keys = {"A", "B", "C", "D", "E"}
        actual_keys = set(q.get("choices", {}).keys())
        if actual_keys != expected_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            issues.append(f"{test_id}/{qid}: CS choices mismatch — missing={missing}, extra={extra}")

    elif q["type"] == "complement_grupat":
        expected_keys = {"1", "2", "3", "4"}
        actual_keys = set(q.get("choices", {}).keys())
        if actual_keys != expected_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            issues.append(f"{test_id}/{qid}: CG choices mismatch — missing={missing}, extra={extra}")

    if not q.get("correct_answer"):
        issues.append(f"{test_id}/{qid}: no answer matched")
    elif q["correct_answer"] not in "ABCDE":
        issues.append(f"{test_id}/{qid}: invalid answer '{q['correct_answer']}'")

    # Check for empty choices
    for key, val in q.get("choices", {}).items():
        if not val or len(val.strip()) < 2:
            issues.append(f"{test_id}/{qid}: choice {key} is empty or too short")

    return issues


def validate_test(test: dict) -> list[str]:
    """Validate a test section."""
    issues = []
    test_id = test.get("test_id", "unknown")

    if not test.get("questions"):
        issues.append(f"{test_id}: no questions found")
        return issues

    q_count = len(test["questions"])
    if q_count < 10:
        issues.append(f"{test_id}: only {q_count} questions (expected ~60)")

    # Check for duplicate question numbers
    numbers = [q["number"] for q in test["questions"]]
    dupes = [n for n in numbers if numbers.count(n) > 1]
    if dupes:
        issues.append(f"{test_id}: duplicate question numbers: {set(dupes)}")

    for q in test["questions"]:
        issues.extend(validate_question(q, test_id))

    return issues


def validate_file(json_path: Path) -> list[str]:
    """Validate a parsed JSON file."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    issues = []
    for test in data.get("tests", []):
        issues.extend(validate_test(test))

    return issues


def main():
    project_root = Path(__file__).parent.parent
    parsed_dir = project_root / "parsed"

    if not parsed_dir.exists():
        print(f"ERROR: {parsed_dir} does not exist. Run parse.py first.")
        sys.exit(1)

    total_issues = 0
    total_questions = 0
    total_answered = 0

    for json_file in sorted(parsed_dir.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        issues = validate_file(json_file)
        q_count = sum(len(t["questions"]) for t in data.get("tests", []))
        a_count = sum(
            1 for t in data.get("tests", []) for q in t["questions"] if q.get("correct_answer")
        )
        total_questions += q_count
        total_answered += a_count

        status = "PASS" if not issues else f"WARN ({len(issues)} issues)"
        print(f"{status}: {json_file.name} — {q_count} questions, {a_count} answered")

        if issues:
            for issue in issues[:10]:  # Show first 10
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
            total_issues += len(issues)

    print(f"\n{'='*60}")
    print(f"Total: {total_questions} questions, {total_answered} with answers")
    print(f"Issues: {total_issues}")
    if total_questions > 0:
        print(f"Answer coverage: {total_answered/total_questions*100:.1f}%")


if __name__ == "__main__":
    main()
```

**Step 2: Run**

```bash
python scripts/validate.py
```

Review the output. Use the issues to go back and fix the parser (Task 5) iteratively.

**Step 3: Commit**

```bash
git add scripts/validate.py
git commit -m "feat: add validation script for parsed questions"
```

---

### Task 7: Deduplicator

**Files:**
- Create: `scripts/deduplicate.py`
- Test: run on duplicate pairs (2010, 2016, 2020)

Uses fuzzy string matching to identify and merge duplicate questions across files that cover the same exam year.

**Step 1: Create `scripts/deduplicate.py`**

```python
#!/usr/bin/env python3
"""Deduplicate questions across files from the same year."""

import json
import sys
from pathlib import Path
from rapidfuzz import fuzz

# Files known to be duplicates of each other
DUPLICATE_GROUPS = [
    ["Biologie 2010 UMFCD", "Biologie 2010 UMFCD "],
    ["Biologie 2016 UMFCD", "Biologie 2016 UMFCD-"],
    ["Biologie 2020 UMFCD", "Biologie 2020 UMFCD-"],
]

SIMILARITY_THRESHOLD = 85  # fuzzy match ratio threshold


def questions_match(q1: dict, q2: dict) -> bool:
    """Check if two questions are duplicates using fuzzy text matching."""
    ratio = fuzz.ratio(q1["text"], q2["text"])
    return ratio >= SIMILARITY_THRESHOLD


def deduplicate_group(files: list[dict]) -> dict:
    """Given multiple parsed files for the same year, merge into one, preferring higher quality."""
    if len(files) == 1:
        return files[0]

    # Use the file with the most answered questions as the primary
    files.sort(
        key=lambda f: sum(
            1 for t in f["tests"] for q in t["questions"] if q.get("correct_answer")
        ),
        reverse=True,
    )

    primary = files[0]
    # Collect all questions from primary
    primary_questions = [q for t in primary["tests"] for q in t["questions"]]

    for secondary in files[1:]:
        for test in secondary["tests"]:
            for q in test["questions"]:
                # Check if this question already exists in primary
                is_dup = any(questions_match(q, pq) for pq in primary_questions)
                if not is_dup:
                    # New question — find or create a matching test in primary
                    matching_test = None
                    for pt in primary["tests"]:
                        if pt.get("topic") == test.get("topic"):
                            matching_test = pt
                            break
                    if matching_test is None:
                        matching_test = {
                            "test_id": test["test_id"] + "_merged",
                            "title": test["title"],
                            "author": test.get("author"),
                            "topic": test.get("topic", "general"),
                            "type": test.get("type", "general_test"),
                            "questions": [],
                        }
                        primary["tests"].append(matching_test)
                    matching_test["questions"].append(q)
                    primary_questions.append(q)

    return primary


def main():
    project_root = Path(__file__).parent.parent
    parsed_dir = project_root / "parsed"
    output_dir = project_root / "parsed" / "deduped"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all parsed files
    all_files = {}
    for json_file in sorted(parsed_dir.glob("*.json")):
        if json_file.parent.name == "deduped":
            continue
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        all_files[json_file.stem] = data

    # Process duplicate groups
    processed_stems = set()
    for group in DUPLICATE_GROUPS:
        group_files = []
        for stem in group:
            if stem in all_files:
                group_files.append(all_files[stem])
                processed_stems.add(stem)

        if len(group_files) > 1:
            merged = deduplicate_group(group_files)
            total_q = sum(len(t["questions"]) for t in merged["tests"])
            print(f"Merged {[g for g in group]}: {total_q} questions (from {len(group_files)} files)")
            out_path = output_dir / f"{group[0]}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
        elif group_files:
            # Only one file found, just copy it
            out_path = output_dir / f"{group[0]}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(group_files[0], f, ensure_ascii=False, indent=2)
            processed_stems.add(group[0])

    # Copy non-duplicate files as-is
    for stem, data in all_files.items():
        if stem not in processed_stems:
            out_path = output_dir / f"{stem}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    count = len(list(output_dir.glob("*.json")))
    print(f"\nDone. {count} deduplicated files in {output_dir}")


if __name__ == "__main__":
    main()
```

**Step 2: Run**

```bash
python scripts/deduplicate.py
```

**Step 3: Commit**

```bash
git add scripts/deduplicate.py
git commit -m "feat: add fuzzy deduplication for same-year PDFs"
```

---

### Task 8: Merger — final output

**Files:**
- Create: `scripts/merge.py`
- Test: inspect final `output/grile.json`

Combines all deduplicated JSONs into the final output file.

**Step 1: Create `scripts/merge.py`**

```python
#!/usr/bin/env python3
"""Merge all deduplicated parsed JSONs into final output."""

import json
from datetime import datetime, timezone
from pathlib import Path


GRUPAT_RULES = {
    "A": "1,2,3 correct",
    "B": "1,3 correct",
    "C": "2,4 correct",
    "D": "only 4 correct",
    "E": "all correct or all false",
}


def main():
    project_root = Path(__file__).parent.parent
    deduped_dir = project_root / "parsed" / "deduped"
    output_path = project_root / "output" / "grile.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sources = []
    total_questions = 0

    for json_file in sorted(deduped_dir.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        sources.append(data)
        q_count = sum(len(t["questions"]) for t in data.get("tests", []))
        total_questions += q_count
        print(f"  {json_file.name}: {q_count} questions")

    output = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "metadata": {
            "complement_grupat_rules": GRUPAT_RULES,
            "total_questions": total_questions,
            "total_sources": len(sources),
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {total_questions} questions from {len(sources)} sources → {output_path}")


if __name__ == "__main__":
    main()
```

**Step 2: Run**

```bash
python scripts/merge.py
```

**Step 3: Verify final output**

```bash
python -c "
import json
with open('output/grile.json') as f:
    data = json.load(f)
print(f'Version: {data[\"version\"]}')
print(f'Sources: {data[\"metadata\"][\"total_sources\"]}')
print(f'Total questions: {data[\"metadata\"][\"total_questions\"]}')
for src in data['sources']:
    q = sum(len(t['questions']) for t in src['tests'])
    a = sum(1 for t in src['tests'] for q_ in t['questions'] if q_.get('correct_answer'))
    print(f'  {src[\"year\"]} ({src[\"file\"]}): {q} questions, {a} answered')
"
```

**Step 4: Commit**

```bash
git add scripts/merge.py
git commit -m "feat: add merge script for final grile.json output"
```

---

### Task 9: End-to-end test run and parser iteration

**Files:**
- Modify: `scripts/parse.py` (as needed based on validation results)

**Step 1: Run the full pipeline**

```bash
python scripts/extract_pymupdf.py
# python scripts/extract_mistral.py  # (already done in Task 3)
python scripts/normalize.py
python scripts/parse.py
python scripts/validate.py
```

**Step 2: Review validation output**

Look at the issues report. Common things that will need fixing:
- Questions with missing choices (parser didn't catch multi-line choices)
- Answer keys that didn't match (format variations between years)
- Questions miscategorized as simplu vs grupat

**Step 3: Fix parser, re-run, repeat**

Iterate on `parse.py` until the validator reports acceptable results. Target: >90% of questions have matched answers, <5% have missing choices.

**Step 4: Run dedup and merge**

```bash
python scripts/deduplicate.py
python scripts/merge.py
python -c "
import json
with open('output/grile.json') as f:
    data = json.load(f)
print(f'Final: {data[\"metadata\"][\"total_questions\"]} questions from {data[\"metadata\"][\"total_sources\"]} sources')
"
```

**Step 5: Commit final state**

```bash
git add scripts/
git commit -m "feat: complete pipeline — end-to-end extraction, parsing, validation, dedup, merge"
```
