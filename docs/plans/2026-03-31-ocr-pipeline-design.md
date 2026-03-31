# OCR Pipeline Design — Grile Medicina

**Date:** 2026-03-31
**Goal:** Extract all multiple-choice questions from ~19 scanned/text medical admission exam PDFs (UMFCD Bucharest, 2008-2025) into structured JSON for a quiz/study app and searchable reference database.

---

## File Inventory

| File | Pages | Strategy | Notes |
|------|-------|----------|-------|
| Biologie 2008 UMFCD .pdf | 106 | Mistral OCR | |
| Biologie 2009 UMFCD .pdf | 290 | PyMuPDF | Has embedded text |
| Biologie 2010 UMFCD.pdf | 364 | Mistral OCR | Higher res scan |
| Biologie 2010 UMFCD .pdf | 365 | Mistral OCR | Lower res, deduplicate with above |
| Biologie 2011 UMFCD .pdf | 90 | Mistral OCR | |
| Biologie 2012 UMFCD .pdf | 329 | PyMuPDF | Has embedded text |
| Biologie 2013 UMFCD .pdf | 305 | PyMuPDF | Has embedded text |
| Biologie 2014 UMFCD.pdf | 314 | PyMuPDF | Has embedded text |
| Biologie 2015 UMFCD.pdf | 391 | PyMuPDF | Has embedded text |
| Biologie 2015 UMFCD-.pdf | — | **Skip** | Same content (2-page-per-scan) |
| Biologie 2016 UMFCD.pdf | 142 | Mistral OCR | |
| Biologie 2016 UMFCD-.pdf | 98 | Mistral OCR | 2-page-per-scan, deduplicate with above |
| Biologie 2017 UMFCD.pdf | 304 | PyMuPDF | Has embedded text |
| Biologie 2017 UMFCD-.pdf | — | **Skip** | Same content (2-page-per-scan) |
| Biologie 2018 UMFCD nu exsita .pdf | — | **Skip** | 1-page placeholder |
| Biologie 2019 UMFCD.pdf | 243 | Mistral OCR | Has text metadata but only ~23 chars/page avg — effectively image-only |
| Biologie 2020 UMFCD.pdf | 353 | Mistral OCR | |
| Biologie 2020 UMFCD-.pdf | 350 | Mistral OCR | Deduplicate with above |
| Biologie 2021 UMFCD.pdf | 241 | Mistral OCR | |
| Biologie 2022 UMFCD.pdf | 221 | Mistral OCR | |
| BIOL 2025- .pdf | 246 | PyMuPDF | Has embedded text |
| Carte grile bio 2023 (1).pdf | 121 | Mistral OCR | |

**Totals:** ~7 PyMuPDF (free), ~12 Mistral OCR (~$3-6 batch), 3 skipped.

## Question Types

### Complement Simplu
- 5 answer choices labeled A-E
- Exactly one correct answer

### Complement Grupat
- 4 statements numbered 1-4
- Answer decoding rule:
  - A = statements 1,2,3 correct
  - B = statements 1,3 correct
  - C = statements 2,4 correct
  - D = only statement 4 correct
  - E = all correct or all false (ambiguous — store letter only, app interprets)

## Pipeline Architecture

```
INPUT (19 PDFs)
    │
    ├── PyMuPDF (8 text PDFs) → raw text
    ├── Mistral OCR batch (11 image PDFs) → markdown
    │
    ▼
Normalizer
    - Consistent markdown format
    - Fix diacritics (ş→ș, ţ→ț, cedilla→comma-below)
    - Normalize whitespace
    │
    ▼
Parser (regex-based)
    - Detect sections (TOC, chapters, general tests)
    - Extract questions + choices
    - Detect complement type (simplu vs grupat)
    - Extract answer keys
    - Match answers to questions
    │
    ▼
Validator
    - Expected ~60 questions per test
    - All questions have answers matched
    - Correct choice count (5 for simplu, 4 for grupat)
    - Flag anomalies for manual review
    │
    ▼
Deduplicator
    - Fuzzy match questions across duplicate files (2010, 2016, 2020)
    - Keep highest-confidence version
    │
    ▼
OUTPUT: grile.json
```

## JSON Schema

```json
{
  "version": "1.0",
  "generated_at": "ISO-8601 timestamp",
  "sources": [
    {
      "file": "Biologie 2014 UMFCD.pdf",
      "year": 2014,
      "subject": "biologie",
      "extraction_method": "pymupdf | mistral_ocr",
      "tests": [
        {
          "test_id": "2014_celula_1",
          "title": "Celula și Țesuturile",
          "author": "Șef de Lucrări Dr. Vasilica Bauşic",
          "topic": "celula",
          "type": "chapter_test | general_test",
          "questions": [
            {
              "id": "2014_celula_1_q1",
              "number": 1,
              "type": "complement_simplu",
              "text": "Question text here",
              "choices": {
                "A": "Choice A text",
                "B": "Choice B text",
                "C": "Choice C text",
                "D": "Choice D text",
                "E": "Choice E text"
              },
              "correct_answer": "C",
              "correct_statements": null,
              "page_ref": "pg.7"
            },
            {
              "id": "2014_celula_1_q36",
              "number": 36,
              "type": "complement_grupat",
              "text": "Question text here",
              "choices": {
                "1": "Statement 1",
                "2": "Statement 2",
                "3": "Statement 3",
                "4": "Statement 4"
              },
              "correct_answer": "B",
              "correct_statements": [1, 3],
              "page_ref": "pg.45"
            }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "complement_grupat_rules": {
      "A": "1,2,3 correct",
      "B": "1,3 correct",
      "C": "2,4 correct",
      "D": "only 4 correct",
      "E": "all correct or all false"
    },
    "total_questions": 0,
    "total_sources": 0
  }
}
```

### Schema Design Decisions

- **Hierarchical**: source → tests → questions. Preserves book organization, supports quiz (random pick) and search (filter by year/topic/type).
- **Deterministic IDs**: `{year}_{topic}_{test_num}_q{question_num}` for stable references and deduplication.
- **`correct_statements`**: Decoded from answer letter for A-D, `null` for E (ambiguous). App layer handles E interpretation.
- **`page_ref`**: From answer key as-is (refers to source textbook pages, not PDF pages).
- **Topic tagging**: Chapter questions tagged with chapter topic; general test questions tagged as "general". AI-based classification deferred to later.

## Project Structure

```
grile-medicina/
├── pdfs/                     # Source PDFs
├── extracted/                # Phase 1: raw text/markdown per PDF
│   ├── pymupdf/
│   └── mistral/
├── parsed/                   # Phase 2: one JSON per source file
├── output/                   # Final merged + deduplicated JSON
│   └── grile.json
├── scripts/
│   ├── extract_pymupdf.py
│   ├── extract_mistral.py
│   ├── normalize.py
│   ├── parse.py
│   ├── validate.py
│   ├── deduplicate.py
│   └── merge.py
├── docs/plans/
├── flake.nix
└── README.md
```

## Cost Estimate

- Mistral OCR batch API: ~2,675 pages × $1/1000 = **~$2.70-$5.40**
- Everything else: free (PyMuPDF, Python scripts)

## Future Work (Out of Scope)

- AI-based topic classification for general test questions
- Quiz app frontend
- Full-text search / embedding-based search
- Chimie/Fizică exam support (currently biologie only)
