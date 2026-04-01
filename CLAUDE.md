# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Pipeline that extracts multiple-choice biology questions from Romanian medical exam PDFs (UMFCD, 2008–2025) into a single structured JSON. Current coverage: **99.13%** (22,029/22,222 answers). Remaining 193 gaps are SOURCE_GAP (answer keys absent from source PDFs).

## Environment

```bash
nix develop          # Python 3.12 + PyMuPDF; auto-creates .venv with mistralai + rapidfuzz
```

Mistral OCR requires `MISTRAL_API_KEY` in `.env` (see `.env.example`).

## Pipeline commands

Run inside `nix develop` (or prefix with `nix develop --command bash -c "..."`):

```bash
# 1. Extract text from PDFs (only needed when adding new PDFs)
python scripts/extract_pymupdf.py          # text-embedded PDFs → extracted/pymupdf/*.md
python scripts/extract_mistral.py          # image-only PDFs → extracted/mistral/*.json (needs API key)
python scripts/extract_mistral.py "2011"   # filter by filename substring

# 2. Normalize extracted text (fix diacritics ş→ș ţ→ț, collapse whitespace)
python scripts/normalize.py                # → extracted/normalized/*.md

# 3. Parse, patch, dedup, merge (the standard rebuild)
python scripts/parse.py                    # normalized .md → parsed/*.json
python scripts/patch_answers.py            # apply manual corrections from patches/*.json
python scripts/deduplicate.py              # fuzzy-merge duplicate-year PDFs → parsed/deduped/
python scripts/merge.py                    # combine all → output/grile.json

# Validate structural correctness and answer coverage
python scripts/validate.py
```

The typical iteration loop after changing `parse.py` or adding patches:
```bash
python scripts/parse.py && python scripts/patch_answers.py && python scripts/deduplicate.py && python scripts/merge.py
```

## Architecture

### Data flow

```
pdfs/*.pdf
  ├─[text-embedded]─ extract_pymupdf ─→ extracted/pymupdf/*.md
  └─[image-only]──── extract_mistral ─→ extracted/mistral/*.json
                              ↓
                     normalize.py ─→ extracted/normalized/*.md
                              ↓
                     parse.py (regex state machine, ~1500 lines)
                              ↓
                     parsed/*.json (one per source PDF)
                              ↓
                     patch_answers.py (applies patches/*.json)
                              ↓
                     deduplicate.py (merges 2010/2016/2020 variant PDFs via rapidfuzz)
                              ↓
                     parsed/deduped/*.json
                              ↓
                     merge.py ─→ output/grile.json
```

### Parser (parse.py)

The core component. A regex-based state machine that processes normalized markdown line-by-line, detecting:
- **Test boundaries** — headers like "TEST 3", "CELULA", "CAPITOLUL 1. SISTEMUL NERVOS"
- **Question types** — `complement_simplu` (5 choices A–E) and `complement_grupat` (4 numbered statements)
- **Answer keys** — tables/lines at the end of each test mapping question numbers to letters
- **Topics** — 11 categories detected from headers (celula, sistemul_nervos, circulatia, etc.)

Key internal functions:
- `finalize_test()` orchestrates: finalize_question → fix Q0 renumbering → fix page-concat numbers → finalize_answers → apply deferred answers
- `_fix_q0_renumbering()` — fixes page-break OCR artifacts where "30." splits into page number + "0."
- `_fix_page_concat_numbers()` — fixes OCR merging page number with question number (e.g., "527" → "57")
- `_answer_dicts` — stored on test objects for re-matching after question renumbering

### Question types

**complement_simplu (CS):** 5 choices (A–E), single correct letter.

**complement_grupat (CG):** 4 numbered statements, answer decoded as:
- A = statements 1,2,3 correct
- B = statements 1,3 correct
- C = statements 2,4 correct
- D = only statement 4 correct
- E = all statements 1,2,3,4 correct

### Patch system

Manual answer corrections live in `patches/*.json`:
```json
{
  "target": "Biologie 2011 UMFCD.json",
  "patches": [
    {"test_title": "TESTUL NR.4", "question_number": 19, "correct_answer": "C"},
    {"test_title": "...", "question_number": 1, "correct_answer": "B", "force": true}
  ]
}
```
`force: true` overrides existing (wrong) answers. Without it, patches only fill blanks.

### Deduplication

Some years have two PDF scans (e.g., "Biologie 2016 UMFCD.pdf" and "Biologie 2016 UMFCD-.pdf"). `deduplicate.py` uses rapidfuzz (threshold 85) to fuzzy-match questions and merge answers from the better-covered variant.

## Output schema (output/grile.json)

```json
{
  "version": "1.0",
  "generated_at": "...",
  "sources": [
    {
      "file": "Biologie 2009 UMFCD",
      "year": 2009,
      "tests": [
        {
          "test_id": "2009_celula_1",
          "title": "CELULE, ȚESUTURI...",
          "topic": "celula",
          "questions": [
            {
              "id": "2009_celula_1_q1",
              "number": 1,
              "type": "complement_simplu",
              "text": "...",
              "choices": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."},
              "correct_answer": "A",
              "correct_statements": null,
              "page_ref": "pag. 5"
            }
          ]
        }
      ]
    }
  ],
  "metadata": { "total_questions": 22222, "complement_grupat_rules": {...} }
}
```

## Remaining gaps

See `MISSING_ANSWERS.md` for the full list of 193 unanswered questions with test names, question numbers, and text previews. All are SOURCE_GAP (answer keys missing from source PDFs).
