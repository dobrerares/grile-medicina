"""Post-processing cleanup for grile.json.

Fixes structural issues left by the parser:
1. Extracts inline CS choices from question text (splitting approach)
2. Extracts inline CG choices from question text (lettered/semicolon patterns)
3. Removes empty questions (no text + no choices)
4. Removes orphaned fragments (short texts that aren't real questions)
5. Fixes encoding residue (ã → ă)
6. Deduplicates questions with same number within a test
"""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# CS inline choice extraction (splitting approach)
# ---------------------------------------------------------------------------

# Splitters for CS: " - A. ", " - A ", "A. ", "A- ", etc.
CS_SPLIT_RES = [
    # " - A. " or " - A) " or " - A- " (dash + letter + punct)
    re.compile(r'\s*[-–]\s*([A-E])[\.\):\-]\s*'),
    # " - A " (dash + letter + space, no punct)
    re.compile(r'\s*[-–]\s*([A-E])\s+'),
    # "F. " / "F) " / "F- " (alternative label set, uppercase)
    re.compile(r'\s*([F-J])[\.\):\-]\s*'),
    # "f. " / "f) " / "f- " (lowercase labels)
    re.compile(r'\s*([f-j])[\.\):\-]\s*'),
    # "F " (alternative labels, space only)
    re.compile(r'[;.]\s*([F-J])\s+'),
    # "; A " or ": A " (semicolon/colon + letter + space)
    re.compile(r'[;:]\s*([A-E])\s+'),
    # "[;. ] A " (any punct or space + letter + space — most lenient)
    re.compile(r'[;.\s]\s*([A-E])\s+'),
    # Bullet separators: "• text" between choices
    re.compile(r'\s*([A-E])[-–]\s*'),
]

FGHIJ_TO_ABCDE = str.maketrans('FGHIJfghij', 'ABCDEABCDE')


def extract_cs_by_split(text):
    """Extract CS choices by splitting text at letter markers.
    Returns (stem, choices_dict) or None.
    """
    for splitter in CS_SPLIT_RES:
        parts = splitter.split(text)
        # A successful split gives: [stem, 'A', choice_a, 'B', choice_b, ...]
        # So we need at least 11 parts: stem + 5 * (letter, text)
        if len(parts) < 11:
            continue

        stem = parts[0].strip().rstrip(':;,')
        letters = [parts[i] for i in range(1, 11, 2)]
        texts = [parts[i].strip().rstrip('.;,') for i in range(2, 11, 2)]

        # Normalize F-J to A-E
        letters = [l.translate(FGHIJ_TO_ABCDE) for l in letters]

        # Validate: should be exactly A, B, C, D, E (in order)
        if letters != ['A', 'B', 'C', 'D', 'E']:
            continue

        # All choice texts must be non-empty
        if not stem or not all(len(t) > 0 for t in texts):
            continue

        choices = dict(zip(letters, texts))
        return stem, choices

    # Fallback: dash-only choices (no letter labels)
    # Pattern: "stem: - choice1 - choice2 - choice3 - choice4 - choice5"
    dash_parts = re.split(r'\s*[-–]\s+', text)
    if len(dash_parts) >= 6:
        stem = dash_parts[0].strip().rstrip(':;,')
        # Take last 5 parts as choices
        choice_texts = [p.strip().rstrip('.;,') for p in dash_parts[-5:]]
        if stem and all(len(t) > 0 for t in choice_texts):
            choices = dict(zip('ABCDE', choice_texts))
            return stem, choices

    return None


# ---------------------------------------------------------------------------
# CG inline choice extraction
# ---------------------------------------------------------------------------

# Splitters for CG with letter labels
CG_SPLIT_RES = [
    # "A. stmt; B. stmt; C. stmt; D. stmt"
    re.compile(r'\s*([A-D])[\.\):\-]\s*'),
    # "a. stmt b. stmt" (lowercase labels — require whitespace before)
    re.compile(r'(?:^|\s)([a-d])[\.\):\-]\s*'),
    # "A stmt; B stmt" (letter + space)
    re.compile(r'[;:]\s*([A-D])\s+'),
    # "a stmt b stmt" (lowercase, require whitespace before)
    re.compile(r'(?:^|\s)([a-d])\s+'),
]


def extract_cg_by_split(text):
    """Extract CG choices by splitting at letter/number markers."""
    # Try lettered patterns (A/B/C/D or a/b/c/d → mapped to 1/2/3/4)
    for splitter in CG_SPLIT_RES:
        parts = splitter.split(text)
        if len(parts) < 9:  # stem + 4*(letter, text)
            continue
        stem = parts[0].strip().rstrip(':;,')
        letters = [parts[i].upper() for i in range(1, 9, 2)]
        texts = [parts[i].strip().rstrip('.;,') for i in range(2, 9, 2)]
        if letters == ['A', 'B', 'C', 'D'] and stem and all(len(t) > 1 for t in texts):
            choices = {"1": texts[0], "2": texts[1], "3": texts[2], "4": texts[3]}
            return stem, choices

    # Try numbered pattern: "stem: 1 text 2 text 3 text 4 text"
    num_parts = re.split(r'\s+([1-4])\s+', text)
    if len(num_parts) >= 9:  # stem + 4*(num, text)
        stem = num_parts[0].strip().rstrip(':;,')
        nums = [num_parts[i] for i in range(1, 9, 2)]
        texts_n = [num_parts[i].strip().rstrip('.;,') for i in range(2, 9, 2)]
        if nums == ['1', '2', '3', '4'] and stem and all(len(t) > 1 for t in texts_n):
            return stem, {"1": texts_n[0], "2": texts_n[1], "3": texts_n[2], "4": texts_n[3]}

    # Try semicolon-only pattern (no letter labels)
    m = re.match(
        r'^(.*?[:?])\s*'
        r'([^;]+);\s*'
        r'([^;]+);\s*'
        r'([^;]+);\s*'
        r'([^;]+?)\.?\s*$',
        text, re.DOTALL
    )
    if m:
        stem = m.group(1).strip()
        stmts = [m.group(i).strip().rstrip('.;,') for i in range(2, 6)]
        if stem and all(len(s) > 2 for s in stmts):
            return stem, {"1": stmts[0], "2": stmts[1], "3": stmts[2], "4": stmts[3]}

    return None


# ---------------------------------------------------------------------------
# Fragment / orphan detection
# ---------------------------------------------------------------------------

def is_orphan_fragment(q):
    """Check if a question is an orphaned fragment (not a real standalone question).
    These are typically short text snippets that were part of a CG question's
    numbered statements but got split into separate entries by the parser.
    """
    text = q.get('text', '').strip()
    choices = q.get('choices', {})

    # Must have empty choices
    if choices and len(choices) > 0:
        return False

    stripped = text.rstrip('.;,')

    if not stripped:
        return True

    # Stem-only entries: text ends with ':' but has no choices — not usable
    if stripped.endswith(':') and len(stripped) < 150:
        return True

    # Stem-only without punctuation (e.g., "Care dintre afirmații sunt corecte")
    # These are truncated questions with no choices at all
    if len(stripped) < 150 and not stripped.endswith((':', '?', '.')):
        # No choice-like content (no A/B/C/D markers or semicolons)
        if not re.search(r'[A-E][\.\)\-]|[;].*[;]', stripped):
            return True

    # Starts with lowercase — continuation of another question
    if stripped[0:1].islower():
        return True

    # Very short text that doesn't look like a question
    if len(stripped) < 120 and not stripped.endswith((':', '?')):
        if len(stripped) < 40:
            return True
        if not re.match(
            r'^(Care|Ce |Cum |Unde|De ce|Când|Câte|Câți|Prin |Despre |'
            r'În |La |Din |Pentru |Referitor|Următ|Urmat|Nu |Una |Toate|'
            r'Hormon|Gland|Organ|Musc|Celul|Nerv|Arter|Vena|Ficat|'
            r'Pancreas|Tiroid|Hipofi|Sânge|Plasm|Limf|Afirmați|Efecte|'
            r'Alegeți|Selectați|Indicați)',
            text, re.IGNORECASE
        ):
            return True

    return False


# ---------------------------------------------------------------------------
# Encoding fixes
# ---------------------------------------------------------------------------

def fix_encoding(text):
    """Fix encoding residue in text."""
    return text.replace('ã', 'ă').replace('Ã', 'Ă')


def fix_encoding_in_question(q):
    """Fix encoding in all text fields of a question."""
    q['text'] = fix_encoding(q['text'])
    if q.get('choices'):
        q['choices'] = {k: fix_encoding(v) for k, v in q['choices'].items()}


# ---------------------------------------------------------------------------
# Main cleanup
# ---------------------------------------------------------------------------

def cleanup_test(test, stats):
    """Clean up a single test."""
    questions = test['questions']
    cleaned = []
    seen_numbers = {}

    for q in questions:
        # 1. Fix encoding
        text_has_ã = 'ã' in q.get('text', '')
        choices_have_ã = any('ã' in v for v in q.get('choices', {}).values())
        if text_has_ã or choices_have_ã:
            fix_encoding_in_question(q)
            stats['encoding_fixed'] += 1

        text = q.get('text', '')
        choices = q.get('choices', {})

        # 2. Remove empty questions (no text + no/empty choices)
        if len(text.strip()) == 0 and (not choices or all(v.strip() == '' for v in choices.values())):
            stats['empty_removed'] += 1
            continue

        # 3. Extract inline choices for questions with empty choices dict
        if not choices or len(choices) == 0:
            extracted = False
            if q['type'] == 'complement_simplu':
                result = extract_cs_by_split(text)
                if result:
                    q['text'] = result[0]
                    q['choices'] = result[1]
                    stats['cs_extracted'] += 1
                    extracted = True
            elif q['type'] == 'complement_grupat':
                result = extract_cg_by_split(text)
                if result:
                    q['text'] = result[0]
                    q['choices'] = result[1]
                    stats['cg_extracted'] += 1
                    extracted = True

            if not extracted:
                # Remove unfixable questions — they're not usable without choices
                if is_orphan_fragment(q):
                    stats['fragments_removed'] += 1
                else:
                    stats['broken_removed'] += 1
                continue

        # 4. Handle duplicate question numbers — renumber
        num = q['number']
        if num in seen_numbers:
            stats['dups_renumbered'] += 1
            max_num = max(seen_numbers.keys())
            new_num = max_num + 1
            q['number'] = new_num
            q['id'] = re.sub(r'_q\d+$', f'_q{new_num}', q['id'])
            seen_numbers[new_num] = q
        else:
            seen_numbers[num] = q

        cleaned.append(q)

    test['questions'] = cleaned


def main():
    project_root = Path(__file__).parent.parent
    input_file = project_root / "output" / "grile.json"

    if not input_file.exists():
        print(f"ERROR: {input_file} not found")
        sys.exit(1)

    print(f"Loading {input_file}...")
    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)

    stats = {
        'cs_extracted': 0,
        'cg_extracted': 0,
        'fragments_removed': 0,
        'broken_removed': 0,
        'empty_removed': 0,
        'encoding_fixed': 0,
        'dups_renumbered': 0,
    }

    total_before = sum(
        len(t['questions'])
        for s in data['sources']
        for t in s['tests']
    )

    for source in data['sources']:
        for test in source['tests']:
            cleanup_test(test, stats)

    total_after = sum(
        len(t['questions'])
        for s in data['sources']
        for t in s['tests']
    )

    # Update metadata
    data['metadata']['total_questions'] = total_after
    data['metadata']['cleanup_applied'] = True

    # Write back
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    removed = total_before - total_after
    print(f"\nCleanup complete:")
    print(f"  CS choices extracted from text:  {stats['cs_extracted']}")
    print(f"  CG choices extracted from text:  {stats['cg_extracted']}")
    print(f"  Fragments removed:               {stats['fragments_removed']}")
    print(f"  Broken/truncated removed:         {stats['broken_removed']}")
    print(f"  Empty questions removed:          {stats['empty_removed']}")
    print(f"  Encoding issues fixed:            {stats['encoding_fixed']}")
    print(f"  Duplicates renumbered:            {stats['dups_renumbered']}")
    print(f"  Questions: {total_before} -> {total_after} ({removed} removed)")


if __name__ == "__main__":
    main()
