"""Parse normalized .md files into structured JSON with questions, choices, and answers.

Reads from extracted/normalized/*.md, outputs one JSON per source file to parsed/.
Uses a line-by-line state machine approach.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NORMALIZED_DIR = ROOT / "extracted" / "normalized"
PARSED_DIR = ROOT / "parsed"

# ---------------------------------------------------------------------------
# Complement grupat answer decoding
# ---------------------------------------------------------------------------
GRUPAT_DECODE = {
    "A": [1, 2, 3],
    "B": [1, 3],
    "C": [2, 4],
    "D": [4],
    "E": None,  # all correct or all false
}

# ---------------------------------------------------------------------------
# Topic detection from header text
# ---------------------------------------------------------------------------
TOPIC_PATTERNS = [
    (r"CELUL|ȚESUT|TESUT|TESUTUR", "celula"),
    (r"SISTEM(?:UL)?\s*NERVOS|NERVOS", "sistemul_nervos"),
    (r"ANALIZATOR", "analizatorii"),
    (r"GLAND|ENDOCRIN", "glande_endocrine"),
    (r"MIȘCAR|MISCAR|OSOS|MUSCUL|OSTEO|LOCOMOTOR", "miscarea"),
    (r"DIGEST|ABSORB", "digestia"),
    (r"CIRCUL", "circulatia"),
    (r"RESPIR", "respiratia"),
    (r"EXCRE", "excretia"),
    (r"METABOLIS", "metabolismul"),
    (r"REPRODUC|GENITAL", "reproducerea"),
    (r"ALCĂTUIR|ALCATUIR|ORGANISM", "celula"),  # 2013 opening chapter
]


def detect_topic(header: str) -> str:
    """Detect topic slug from a header string."""
    upper = header.upper()
    for pattern, topic in TOPIC_PATTERNS:
        if re.search(pattern, upper):
            return topic
    return "unknown"


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Page marker (inserted by normalizer)
RE_PAGE_MARKER = re.compile(r"^\s*<!--\s*PAGE\s+\d+\s*-->\s*$")

# Standalone page number (one or more digits alone on a line)
RE_PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")

# Complement type header variants — very permissive
RE_COMPLEMENT_HEADER = re.compile(
    r"^\s*(?:ÎNTREBĂRI\s+TIP\s+)?COMPLE\s*M\s*E?\s*N?\s*T\s+"
    r"(S\s*I\s*M\s*P\s*L\s*U|S\s*I\s*M\s*P\s*T\s*U|U\s*N\s*I\s*C|T\s*J\s*N\s*I\s*C|"
    r"G\s*R\s*U\s*P\s*A\s*T|M\s*U\s*L\s*T\s*I\s*P\s*L\s*U|"
    r"C\s*O\s*M\s*P\s*U\s*S|M\s*U\s*L\s*T\s*U\s*P\s*L\s*U)",
    re.IGNORECASE,
)

# RĂSPUNSURI / RASPUNSURI header
RE_RASPUNSURI = re.compile(
    r"^\s*\|?\s*(?:Lista\s+)?R[ĂAÃăÅÄåäÂÁâáĀā]spunsuri(?:lor)?\b", re.IGNORECASE
)
# OCR-corrupted variants from PyMuPDF (2012): nASpUNSURI, NASpUNSURI, nAspuNSURr, etc.
RE_RASPUNSURI_OCR = re.compile(
    r"^\s*[nN][aA][sS][pP][uUtT][nNvV][sS][uU][rR][iIlr]\s*:?\s*$", re.IGNORECASE
)
# Space-separated OCR (2013): "r ă sp u n su r i"
RE_RASPUNSURI_SPACED = re.compile(
    r"^\s*r\s+[ăa]\s*sp\s*u\s*n\s*su\s*r\s*i\s*$", re.IGNORECASE
)
# Misspelled OCR (2020): "Råspunsurl"
RE_RASPUNSURI_MISSPELL = re.compile(
    r"^\s*R[åăa]spunsur[li]\s*$", re.IGNORECASE
)
# Truncated OCR (2010): "SPUNSURI" (missing "RĂ" prefix)
# Also (2023): "ĂSPUNSURI" (missing "R" prefix)
# Also (2012): "Rtrspunsuri" (severely corrupted diacritical)
RE_RASPUNSURI_TRUNCATED = re.compile(
    r"^\s*(?:SPUNSURI|[ĂAă]SPUNSURI|R\s*tr\s*spunsuri)\s*:?\s*$", re.IGNORECASE
)

# Author line
RE_AUTHOR = re.compile(
    r"^\s*[ȊÎîiI]ntreb[ăa]ri\s+realizate\s+de\s+(.+)",
    re.IGNORECASE,
)

# Question number at start of line
RE_QUESTION_START = re.compile(r"^\s*(\d{1,3})\s*[.\)]\s*(.*)$")

# Choice for complement simplu: A. / A) / a. / a) (letters A-E)
RE_CHOICE_SIMPLU = re.compile(r"^\s*([A-Ea-e])\s*[.\)]\s*(.*)$")

# Choice for complement grupat: 1. / 1) / 1.text (digits 1-4)
RE_CHOICE_GRUPAT = re.compile(r"^\s*([1-4])\s*[-.\)]\s*(.*)$")

# Test header: TEST 1 / TEST1 / TESTÓ / TEST GENERAL etc.
RE_TEST_HEADER = re.compile(r"^\s*TEST(?:UL|ELE)?\s*(?:NR\s*\.?\s*)?[OÓ]?\s*(\d+)(?:\s+[ȘS]I\s+(\d+))?\s*$", re.IGNORECASE)
RE_TEST_GENERAL_HEADER = re.compile(
    r"^\s*TEST(?:UL)?\s+GENERAL\s*(?:NR\.?\s*)?(\d*)\s*$", re.IGNORECASE
)
RE_TESTE_GENERALE = re.compile(r"^\s*(?:\d+\s*\.\s*)?TESTE\s+GENERAL", re.IGNORECASE)
RE_TESTE_PE_CAPITOLE = re.compile(r"^\s*(?:\d+\s*\.\s*|L\s+)?TESTE\s+RECAPITULATIV", re.IGNORECASE)

# CUPRINS
RE_CUPRINS = re.compile(r"^\s*CUPRINS\s*$", re.IGNORECASE)

# Topic headers: lines matching known topic keywords
RE_TOPIC_HEADER = re.compile(
    r"^\s*((?:CELUL|ȚESUT|TESUT|SISTEM|NERVOS|ANALIZATOR|GLAND|ENDOCRIN|"
    r"MIȘCAR|MISCAR|OSOS|MUSCUL|OSTEO|DIGEST|ABSORB|CIRCUL|RESPIR|EXCRE|"
    r"METABOLIS|REPRODUC|GENITAL|ALCĂTUIR|ALCATUIR|FUNCȚIA|APARATUL|"
    r"TEST\s*GLAND)[^\n]*)",
    re.IGNORECASE,
)

# Answer line patterns
RE_ANSWER_LINE = re.compile(
    r"^\s*(\d{1,3})\s*[-–.\s,)]+\s*([A-Ea-e])\s*[-–.\s,)/]*\s*(.*)?$"
)
RE_ANSWER_NOSEP = re.compile(
    r"^\s*(\d{1,3})\s*([A-Ea-e])\s*[-–.\s,)/]*\s*(.*)?$"
)
RE_ANSWER_CONTINUATION = re.compile(
    r"^\s*(?:pag|pg|fig|\.fig|\.pag|\(pag|\(pg)", re.IGNORECASE
)

# Inline answer pattern for multi-column lines: "1 C pg. 11 9 D pg. 15"
# Also handles "1-A 30-D" and "1) C 31) D" formats
RE_ANSWER_INLINE = re.compile(r"(\d{1,3})\s*[-.)]*\s*([A-Ea-e])(?:\s*(?:[-–/]?\s*(?:pag|pg|p)\.?\s*[\d,.\s\-–]+)?)")

# Pattern to strip "Răspunsuri complement simplu/grupat" prefix and get remainder
RE_RASPUNSURI_PREFIX = re.compile(
    r"^\s*R[ĂAÃă]spunsuri\s+(?:complement\s+\w+\s*)?",
    re.IGNORECASE,
)


def classify_complement(text: str) -> str:
    """Classify a complement header match as simplu or grupat."""
    collapsed = re.sub(r"\s+", "", text).upper()
    if collapsed in ("SIMPLU", "SIMPTU", "UNIC", "TJNIC"):
        return "complement_simplu"
    return "complement_grupat"


def extract_year(filename: str) -> int | None:
    m = re.search(r"(20\d{2})", filename)
    return int(m.group(1)) if m else None


def extract_subject(filename: str) -> str:
    lower = filename.lower()
    if "biologie" in lower or "bio" in lower:
        return "biologie"
    return "unknown"


def is_topic_header_line(line: str) -> bool:
    """Check if a line looks like a chapter topic header.

    Must be a short, predominantly uppercase line that starts with a known topic
    keyword. Rejects lines that look like question text or choices.
    """
    stripped = line.strip()
    if not stripped or len(stripped) < 4:
        return False
    if not RE_TOPIC_HEADER.match(stripped):
        return False
    # Reject if it looks like a question or choice (starts with digit or letter+dot)
    if re.match(r"^\d+\s*[.\)]", stripped):
        return False
    if re.match(r"^[A-Ea-e]\s*[.\)]", stripped):
        return False
    # Reject long lines that are likely body text (topic headers are usually short)
    if len(stripped) > 80:
        return False
    # Reject if mostly lowercase (real headers are mostly uppercase)
    upper_chars = sum(1 for c in stripped if c.isupper())
    alpha_chars = sum(1 for c in stripped if c.isalpha())
    if alpha_chars > 0 and upper_chars / alpha_chars < 0.4:
        return False
    return True


def is_complement_header(line: str) -> tuple[bool, str | None]:
    """Check if a line is a complement type header."""
    stripped = line.strip()

    # Strip Roman numeral prefixes: "I. ...", "II. ..."
    stripped_no_roman = re.sub(r"^[IVX]+\.\s*", "", stripped)

    # Try the main regex on both original and Roman-stripped
    for candidate in (stripped, stripped_no_roman):
        m = RE_COMPLEMENT_HEADER.match(candidate)
        if m:
            return True, classify_complement(m.group(1))

    # Collapsed form matching
    base = stripped.rstrip(":. ")
    collapsed = re.sub(r"\s+", "", base.lower())
    CS_COLLAPSED = {
        "complementsimplu", "complementsimptu", "complementunic", "complementtjnic",
        "compementsimplu", "compementsimptu",
        # Truncated OCR: COMPLEMENT SIN, COMPLEMENT SIMPLIC, COMPLEMENTE
        "complementsin", "complementsimplic", "complemente",
        # Truncated OCR (2023): OMPLEMENT SIMPLU (missing "C")
        "omplementsimplu", "omplementsimptu",
        # Also: COMPLEMENTSIMPLII (OCR for SIMPLU→SIMPLII)
        "complementsimplii",
    }
    CG_COLLAPSED = {
        "complementgrupat", "complementmultiplu", "complementcompus",
        "complementmultuplu", "complementgruni",
        "compementgrupat", "compementmultiplu", "compementcompus",
        # Truncated OCR: COMPLEMENT GR, COMPLEMENT GRUPA
        "complementgr", "complementgrupa",
        # Truncated OCR (2023): OMPLEMENT GRUPAT (missing "C")
        "omplementgrupat", "omplementmultiplu", "omplementcompus",
    }
    if collapsed in CS_COLLAPSED | CG_COLLAPSED:
        if collapsed in CS_COLLAPSED:
            return True, "complement_simplu"
        return True, "complement_grupat"
    # Bare "COMPLEMENT" or "OMPLEMENT" with no type — default to simplu
    if collapsed in ("complement", "complement(", "omplement", "omplement("):
        return True, "complement_simplu"

    # "Grile tip complement simplu/grupat" format
    m_grile = re.match(
        r"(?:grile\s+tip\s+)?complement\s+(simplu|grupat|multiplu|compus)",
        stripped, re.IGNORECASE,
    )
    if m_grile:
        return True, classify_complement(m_grile.group(1))

    # "Întrebări tip complement simplu/grupat" with any prefix
    m_intreb = re.match(
        r".*[îiÎI]ntreb[ăa]ri\s+tip\s+complement\s+(simplu|simptu|grupat|multiplu)",
        stripped, re.IGNORECASE,
    )
    if m_intreb:
        return True, classify_complement(m_intreb.group(1))

    # Descriptive sentences implying complement type (but not preface explanations)
    low = stripped.lower()
    if re.search(r"un\s+singur\s+r[ăa]spuns\s+corect", low):
        # Reject preface lines like "Pentru complement simplu – un singur răspuns corect"
        if not re.search(r"pentru\s+complement", low):
            return True, "complement_simplu"
    if re.search(r"ale[gț]e[tț]i\s+un\s+singur\s+r[ăa]spuns", low):
        return True, "complement_simplu"

    return False, None


def parse_page_ref(text: str) -> str | None:
    if not text:
        return None
    text = text.strip().rstrip(".")
    text = text.strip("()")
    text = text.strip()
    return text if text else None


def fix_ocr_answer_line(line: str) -> str:
    """Apply OCR corrections to an answer line.

    Common OCR errors in 2012:
    - '8' used instead of 'B' in answer letter position
    - '4' used instead of 'A' in answer letter position
    - 'l' or 't' used instead of '1' in answer numbers
    - 's' used instead of '5' in answer numbers
    - 'I l' or 'll' used instead of '11'
    - 'ps.' or 'pe.' instead of 'pg.'
    """
    # Pre-fix: "I l" at start of line → "11" (uppercase I + space + lowercase l)
    line = re.sub(r"^(\s*)I\s+l(?=\s*[.\-,)\s])", r"\g<1>11", line)
    # Pre-fix: "N l" at start → "N1" (digit + space + lowercase l → digit + 1)
    # 2013 OCR: "1 l.D, p. 28" → "11.D, p. 28", "2 l.C" → "21.C"
    line = re.sub(r"^(\s*\d)\s+l(?=\s*[.\-,)\s])", r"\g<1>1", line)
    # Pre-fix: "t " at start of line → "1 " (lowercase t used instead of 1)
    # 2013 OCR: "t C (pag. 44)" → "1 C (pag. 44)" (for Q1)
    line = re.sub(r"^(\s*)t(?=\s+[A-Ea-e]\s*[(\s.,])", r"\g<1>1", line)

    # Fix answer number OCR: replace l/t/s in number positions
    # Pattern: line starts with digits possibly mixed with l/t/s
    m = re.match(r"^(\s*)([\dltsoOI]+)\s*([.\-,)\s])\s*(.*)$", line)
    if m:
        prefix, raw_num, sep, rest = m.groups()
        fixed_num = raw_num.replace("l", "1").replace("t", "1").replace("s", "5").replace("o", "0").replace("O", "0").replace("I", "1")
        try:
            int(fixed_num)
            line = f"{prefix}{fixed_num}{sep}{rest}"
        except ValueError:
            pass

    # Fix '8' -> 'B' in answer letter position
    # Pattern: after number+separator, '8' followed by space, paren, dot, or end of line
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)8(\s*[(\s.])", r"\1B\2", line)
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)8(p[gaes])", r"\1B \2", line)
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)8\s*$", r"\1B", line)

    # Fix '4' -> 'A' in answer letter position (when no valid letter follows number)
    # Only apply when '4' is alone (not part of a number like "14" or followed by digits)
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)4(\s*[(\s.])", r"\1A\2", line)
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)4(p[gaes])", r"\1A \2", line)
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)4\s*$", r"\1A", line)

    return line


def parse_answer_lines(lines: list[str]) -> dict[int, tuple[str, str | None]]:
    """Parse answer key lines into {question_number: (letter, page_ref)}."""
    answers = {}

    # Pre-process: expand table rows into individual answer entries
    expanded_lines = []
    for line in lines:
        raw = line.strip()
        if "|" in raw:
            # Split table row into cells, each potentially an answer entry
            cells = [c.strip() for c in raw.split("|") if c.strip()]
            for cell in cells:
                # Skip table headers / non-answer cells
                if is_complement_header(cell)[0]:
                    continue
                if RE_RASPUNSURI.match(cell):
                    # Extract inline answers from "RASPUNSURI: 1) B (pag 100)"
                    remainder = RE_RASPUNSURI_PREFIX.sub("", cell).strip()
                    if remainder and RE_ANSWER_INLINE.search(remainder):
                        expanded_lines.append(remainder)
                    continue
                if is_topic_header_line(cell):
                    continue
                expanded_lines.append(cell)
        else:
            expanded_lines.append(raw)

    i = 0
    answer_offset = 0  # Offset for renumbered answer sub-sections

    while i < len(expanded_lines):
        line = fix_ocr_answer_line(expanded_lines[i])
        stripped = line.strip()
        i += 1

        if not stripped:
            continue

        # Skip page markers (but NOT standalone page numbers — they might be
        # split answer numbers like "10" or "31")
        if RE_PAGE_MARKER.match(stripped):
            continue

        # Skip complement section headers and topic headers within answers
        # But extract inline answers after colon (e.g. "Complement simplu: 31. E/pag.84")
        is_ch, _ = is_complement_header(stripped)
        if is_ch:
            # Detect renumbered sub-sections: if next answers restart at 1,
            # offset by the max answer number seen so far (e.g. grupat answers
            # numbered 1-30 should map to Q31-60 when simplu had 1-30)
            # Guard: only apply offset if pre-restart answers are dense (>30%
            # of range filled).  Sparse answers are likely false positives from
            # question text being mis-parsed as answer lines.
            if answers:
                max_num = max(answers.keys())
                for _peek in range(i, min(i + 5, len(expanded_lines))):
                    _peek_s = expanded_lines[_peek].strip()
                    if not _peek_s:
                        continue
                    _m_peek = RE_ANSWER_LINE.match(_peek_s) or RE_ANSWER_NOSEP.match(_peek_s)
                    if _m_peek:
                        _peek_num = int(_m_peek.group(1))
                        if _peek_num == 1 and len(answers) >= max_num * 0.3:
                            answer_offset = max_num
                    break
            colon_pos = stripped.find(":")
            if colon_pos > 0:
                after_colon = stripped[colon_pos + 1:].strip()
                if after_colon and (RE_ANSWER_LINE.match(after_colon) or
                                    RE_ANSWER_NOSEP.match(after_colon) or
                                    RE_ANSWER_INLINE.search(after_colon)):
                    expanded_lines.insert(i, after_colon)
            continue
        if RE_RASPUNSURI.match(stripped):
            continue
        if is_topic_header_line(stripped):
            continue

        # Skip pure continuation lines (handled as part of previous answer)
        if RE_ANSWER_CONTINUATION.match(stripped):
            continue

        # Check for lines with two answer entries separated by whitespace
        parts = re.split(r"\s{4,}", stripped)
        if len(parts) >= 2:
            parsed_both = True
            temp_answers = {}
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                m = RE_ANSWER_LINE.match(part) or RE_ANSWER_NOSEP.match(part)
                if m:
                    num = int(m.group(1)) + answer_offset
                    letter = m.group(2).upper()
                    pref = parse_page_ref(m.group(3)) if m.group(3) else None
                    temp_answers[num] = (letter, pref)
                else:
                    parsed_both = False
                    break
            if parsed_both and len(temp_answers) >= 2:
                answers.update(temp_answers)
                continue

        # Fallback: use findall for multi-column lines like "1 C pg. 11 9 D pg. 15"
        inline_matches = RE_ANSWER_INLINE.findall(stripped)
        if len(inline_matches) >= 2:
            for num_str, letter in inline_matches:
                answers[int(num_str) + answer_offset] = (letter.upper(), None)
            continue

        # Try standard answer line
        m = RE_ANSWER_LINE.match(stripped)
        if not m:
            m = RE_ANSWER_NOSEP.match(stripped)
        if m:
            num = int(m.group(1)) + answer_offset
            letter = m.group(2).upper()
            page_text = m.group(3) if m.group(3) else ""

            # Collect continuation lines
            while i < len(expanded_lines):
                next_line = expanded_lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                if RE_PAGE_MARKER.match(next_line) or RE_PAGE_NUMBER.match(next_line):
                    i += 1
                    continue
                if RE_ANSWER_CONTINUATION.match(next_line) or (
                    next_line.startswith(("pag", "pg", "fig", "("))
                    and not RE_ANSWER_LINE.match(next_line)
                    and not RE_ANSWER_NOSEP.match(next_line)
                ):
                    page_text += " " + next_line
                    i += 1
                    continue
                break

            pref = parse_page_ref(page_text)
            answers[num] = (letter, pref)
            continue

        # Handle OCR-damaged lines like "ll.B( Pag.7)"
        m_ocr = re.match(r"^\s*([lI]{1,2}|[lI]\d|\d[lI])\s*[-.)\s,]+\s*([A-Ea-e])", stripped)
        if m_ocr:
            raw_num = m_ocr.group(1)
            num_str = raw_num.replace("l", "1").replace("I", "1")
            try:
                num = int(num_str) + answer_offset
                letter = m_ocr.group(2).upper()
                rest = stripped[m_ocr.end():]
                pref = parse_page_ref(rest)
                answers[num] = (letter, pref)
            except ValueError:
                pass
            continue

        # Handle split answers: number on one line (e.g. "10." or "10"),
        # letter on the next line (e.g. "D (pag. 43)" or "B (pg 118)")
        # Also handles BATCH fragmentation (2009): all numbers on consecutive
        # lines, then all letters on consecutive lines.
        m_num_only = re.match(r"^\s*(\d{1,3})\s*[.\s)]*\s*$", stripped)
        if m_num_only:
            first_num = int(m_num_only.group(1)) + answer_offset

            # Peek ahead: is the next non-empty line also a bare number?
            _peek_batch = False
            for _pb in range(i, min(i + 3, len(expanded_lines))):
                _pb_s = expanded_lines[_pb].strip()
                if not _pb_s or RE_PAGE_MARKER.match(_pb_s):
                    continue
                if re.match(r"^\s*\d{1,3}\s*[.\s)]*\s*$", _pb_s):
                    _peek_batch = True
                break

            if _peek_batch:
                # Batch mode: collect all consecutive bare numbers, then
                # matching bare letters. Handles 2009 fragmented OCR where
                # numbers and letters are on separate consecutive lines.
                bare_nums = [first_num]
                while i < len(expanded_lines):
                    ns = expanded_lines[i].strip()
                    if not ns or RE_PAGE_MARKER.match(ns):
                        i += 1
                        continue
                    nm = re.match(r"^\s*(\d{1,3})\s*[.\s)]*\s*$", ns)
                    if nm:
                        bare_nums.append(int(nm.group(1)) + answer_offset)
                        i += 1
                        continue
                    break

                # Collect bare letter lines (letter + paren/page ref)
                bare_letters = []
                while i < len(expanded_lines) and len(bare_letters) < len(bare_nums):
                    ns = expanded_lines[i].strip()
                    if not ns or RE_PAGE_MARKER.match(ns):
                        i += 1
                        continue
                    # Match bare letter: optionally preceded by bullet/dot
                    ml = re.match(r"^\s*[•.\s]*([A-Ea-e])\s*[(\s,.]", ns)
                    if ml:
                        bare_letters.append(ml.group(1).upper())
                        i += 1
                        continue
                    # Skip page ref continuations: ".71)", "17)", ";-7i)"
                    if re.match(r"^\s*[.;,]+\s*\d", ns) or re.match(r"^\s*\d+\s*[,)]\s*$", ns):
                        i += 1
                        continue
                    break

                # Pair numbers with letters
                for j in range(min(len(bare_nums), len(bare_letters))):
                    answers[bare_nums[j]] = (bare_letters[j], None)
                continue

            # Single bare number: look ahead for letter on next line
            num = first_num
            while i < len(expanded_lines):
                next_stripped = expanded_lines[i].strip()
                if not next_stripped:
                    i += 1
                    continue
                if RE_PAGE_MARKER.match(next_stripped) or RE_PAGE_NUMBER.match(next_stripped):
                    i += 1
                    continue
                # Try to match a letter at the start
                m_letter = re.match(r"^\s*([A-Ea-e])\s*[-.\s,)]*\s*(.*)?$", next_stripped)
                if m_letter:
                    letter = m_letter.group(1).upper()
                    page_text = m_letter.group(2) if m_letter.group(2) else ""
                    i += 1

                    # Collect continuation lines
                    while i < len(expanded_lines):
                        cont = expanded_lines[i].strip()
                        if not cont:
                            i += 1
                            continue
                        if RE_PAGE_MARKER.match(cont) or RE_PAGE_NUMBER.match(cont):
                            i += 1
                            continue
                        if RE_ANSWER_CONTINUATION.match(cont) or (
                            cont.startswith(("pag", "pg", "fig", "("))
                            and not RE_ANSWER_LINE.match(cont)
                            and not RE_ANSWER_NOSEP.match(cont)
                        ):
                            page_text += " " + cont
                            i += 1
                            continue
                        break

                    pref = parse_page_ref(page_text)
                    answers[num] = (letter, pref)
                break
            continue

        # Numberless answer line: bare letter followed by comma + page ref
        # Used in OCR-corrupted sections (e.g. 2023) where question numbers
        # are missing: "E, pg 108" meaning sequential answer
        m_bare = re.match(
            r"^\s*([A-Ea-e])\s*,\s*((?:pg|pag|p\.)\s*.*)$", stripped, re.IGNORECASE
        )
        if m_bare:
            next_num = (max(answers.keys()) + 1) if answers else (1 + answer_offset)
            letter = m_bare.group(1).upper()
            pref = parse_page_ref(m_bare.group(2))
            answers[next_num] = (letter, pref)
            continue

    return answers


def is_skippable_line(stripped: str) -> bool:
    """Check if a line should be skipped as non-content."""
    if stripped.startswith(("ISBN", "BIOLOGIE", "MODALITATEA", "LA INTREB",
                            "ALEGETI", "RASPUNDETI", "RĂSPUNDEȚI",
                            "EDITURA", "SUB REDACT")):
        return True
    if re.match(r"^\s*(?:Lucrarea|Au fost|Lucr[aă]ri|No[tț]iuni|Editura|acredit|"
                r"activitate|COORDONAT|Disciplina|Coordonat|Manual de|"
                r"[Îî]nv[aă][tț][aă]m[aâ]nt|pentru admit|Prep\. Univ|"
                r"Drd\. Dr|în conformitate|stabilirea|"
                r"educafie|FURNIZOR|Colegiul|\*c|I,N INTN|"
                r"A - dac|B - dac|C - dac|D - dac|E - dac|"
                r"ALEGETI|SINGIIR)", stripped, re.IGNORECASE):
        return True
    return False


def parse_file(filepath: Path) -> dict:
    """Parse a single normalized .md file into structured JSON."""

    filename = filepath.stem.strip()
    year = extract_year(filename)
    subject = extract_subject(filename)

    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    tests = []
    current_test = None
    current_complement = None
    current_question = None
    current_author = None
    current_topic_title = None
    current_topic = None
    in_answers = False
    answer_lines_buffer = []
    deferred_answers = {}  # Embedded answers to apply at test finalization
    in_general_tests = False
    test_counter = {}
    # Flag: we've seen a new topic/author and expect a new test at next complement header
    pending_new_section = False
    # Flag: a topic header changed — used to split tests when questions restart
    # at 1 without an explicit complement header (e.g. 2020 MIȘCAREA (2))
    pending_topic_change = False
    # Flag: complement_simplu section uses numbered choices (1-5) instead of A-E
    numbered_simplu_choices = False

    def finalize_question():
        nonlocal current_question
        if current_question and current_test:
            current_question["text"] = current_question["text"].strip()
            # Discard zero-choice "questions" that are actually answer lines
            # or OCR artifacts. Patterns:
            #   "Apg.6", "Bp.80", "E (pag 21)", "A p. 103", "Cp. 80, 104"
            if not current_question["choices"]:
                txt = current_question["text"]
                if re.search(r"^[A-Ea-e]\s*[(\s]*p(?:a)?(?:g|\.)", txt):
                    current_question = None
                    return
                # Very short text starting with a letter — likely stray answer
                if len(txt) < 15 and re.match(r"^[A-Ea-e]\b", txt):
                    current_question = None
                    return
                # OCR-corrupted answer lines: text is only answer entry + page ref
                # e.g. "C @ag92) 2t. C @a992)", "8 (pag 88)"
                # Pattern: starts with single letter/digit, followed by page ref
                if len(txt) < 60 and re.match(
                    r"^[A-Ea-e0-9]\s*[\[({@]", txt
                ):
                    current_question = None
                    return
            current_test["questions"].append(current_question)
        current_question = None

    def finalize_answers():
        nonlocal in_answers, answer_lines_buffer
        if in_answers and answer_lines_buffer and current_test:
            answers = parse_answer_lines(answer_lines_buffer)
            if answers:
                # Count how many answers match the current test
                matched = sum(
                    1 for q in current_test["questions"]
                    if q["number"] in answers
                )
                total_answers = len(answers)
                total_questions = len(current_test["questions"])

                # If fewer than 40% of answers match current test AND there are
                # recent tests with more matching questions, try those instead.
                if matched < total_answers * 0.4 and total_questions < total_answers * 0.5:
                    best_test = current_test
                    best_matched = matched
                    for prev_test in reversed(tests[-5:]):
                        prev_matched = sum(
                            1 for q in prev_test["questions"]
                            if q["number"] in answers and not q.get("correct_answer")
                        )
                        if prev_matched > best_matched:
                            best_matched = prev_matched
                            best_test = prev_test
                    if best_test is not current_test:
                        for q in best_test["questions"]:
                            qnum = q["number"]
                            if qnum in answers and not q.get("correct_answer"):
                                letter, pref = answers[qnum]
                                q["correct_answer"] = letter
                                q["page_ref"] = pref
                                if q["type"] == "complement_grupat":
                                    q["correct_statements"] = GRUPAT_DECODE.get(letter)
                    # Also assign to current test for any matches
                    for q in current_test["questions"]:
                        qnum = q["number"]
                        if qnum in answers and not q.get("correct_answer"):
                            letter, pref = answers[qnum]
                            q["correct_answer"] = letter
                            q["page_ref"] = pref
                            if q["type"] == "complement_grupat":
                                q["correct_statements"] = GRUPAT_DECODE.get(letter)
                else:
                    # Normal case: assign all answers to current test
                    for q in current_test["questions"]:
                        qnum = q["number"]
                        if qnum in answers:
                            letter, pref = answers[qnum]
                            q["correct_answer"] = letter
                            q["page_ref"] = pref
                            if q["type"] == "complement_grupat":
                                q["correct_statements"] = GRUPAT_DECODE.get(letter)
                # Store answer dict for potential re-matching after Q0 renumbering
                if not hasattr(current_test, "_answer_dicts"):
                    current_test["_answer_dicts"] = []
                current_test["_answer_dicts"].append(answers)
        answer_lines_buffer = []
        in_answers = False

    def _fix_q0_renumbering():
        """Fix Q0 and duplicate question numbers from page-break OCR artifacts.

        Example: page break splits "30." into page-number + "0." on next page,
        so Q30-Q37 appear as Q0-Q7, duplicating the real Q1-Q7.
        Must run BEFORE answer matching so renumbered Qs get correct answers.
        """
        if not current_test or not current_test["questions"]:
            return
        nums = [q["number"] for q in current_test["questions"]]
        if 0 not in nums:
            return
        idx_of_zero = nums.index(0)
        # Count occurrences to identify duplicates
        from collections import Counter
        num_counts = Counter(nums)
        # Find first missing number > 0
        num_set = set(nums)
        expected = 1
        while expected in num_set:
            expected += 1
        # Renumber Q0 and subsequent duplicates only.
        # Stop when we reach a question that's not a duplicate (unique original).
        offset = expected  # Q0 → expected, Q1 → expected+1, etc.
        for j in range(idx_of_zero, len(nums)):
            old_num = current_test["questions"][j]["number"]
            # Only renumber Q0 or numbers that appear more than once
            if old_num != 0 and num_counts[old_num] <= 1:
                break
            new_num = old_num + offset
            current_test["questions"][j]["number"] = new_num
            current_test["questions"][j]["id"] = (
                current_test["test_id"] + f"_q{new_num}"
            )
            # Clear any wrong answer that was matched with old number
            current_test["questions"][j]["correct_answer"] = None
            current_test["questions"][j]["page_ref"] = None
            current_test["questions"][j]["correct_statements"] = None
            num_counts[old_num] -= 1
        # Re-apply stored answer dicts to match renumbered questions
        for answers in current_test.get("_answer_dicts", []):
            for q in current_test["questions"]:
                if q["number"] in answers and not q.get("correct_answer"):
                    letter, pref = answers[q["number"]]
                    q["correct_answer"] = letter
                    q["page_ref"] = pref
                    if q["type"] == "complement_grupat":
                        q["correct_statements"] = GRUPAT_DECODE.get(letter)

    def _fix_page_concat_numbers():
        """Fix question numbers corrupted by page number concatenation.

        Example: page break makes "57" appear as "527" (page "52" + "7").
        Detect: Q number > max_expected AND the gap from neighbors tells us
        the correct number.
        """
        if not current_test or not current_test["questions"]:
            return
        qs = current_test["questions"]
        num_set = set(q["number"] for q in qs)
        max_normal = max((n for n in num_set if n <= 100), default=0)
        for idx, q in enumerate(qs):
            if q["number"] <= max_normal:
                continue
            # Use previous neighbor to guess correct number
            prev_num = qs[idx - 1]["number"] if idx > 0 else 0
            expected = prev_num + 1
            if expected not in num_set and 0 < expected <= max_normal + 5:
                old = q["number"]
                q["number"] = expected
                q["id"] = current_test["test_id"] + f"_q{expected}"
                q["correct_answer"] = None  # clear possibly wrong answer
                q["page_ref"] = None
                q["correct_statements"] = None
                num_set.discard(old)
                num_set.add(expected)
        # Re-apply stored answer dicts to match renumbered questions
        if current_test:
            for answers in current_test.get("_answer_dicts", []):
                for q in qs:
                    if q["number"] in answers and not q.get("correct_answer"):
                        letter, pref = answers[q["number"]]
                        q["correct_answer"] = letter
                        q["page_ref"] = pref
                        if q["type"] == "complement_grupat":
                            q["correct_statements"] = GRUPAT_DECODE.get(letter)

    def finalize_test():
        nonlocal current_test, deferred_answers
        finalize_question()
        # Fix Q0 renumbering BEFORE answer matching
        _fix_q0_renumbering()
        # Fix page-number concatenated question numbers
        _fix_page_concat_numbers()
        finalize_answers()
        # Apply deferred embedded answers (collected from inline answer sections)
        if current_test and deferred_answers:
            for q in current_test["questions"]:
                qnum = q["number"]
                if qnum in deferred_answers and not q.get("correct_answer"):
                    letter, pref = deferred_answers[qnum]
                    q["correct_answer"] = letter
                    q["page_ref"] = pref
                    if q["type"] == "complement_grupat":
                        q["correct_statements"] = GRUPAT_DECODE.get(letter)
            deferred_answers = {}
        if current_test and current_test["questions"]:
            current_test.pop("_answer_dicts", None)  # clean up internal key
            tests.append(current_test)
        current_test = None

    def start_new_test(title, topic_slug, author, test_type):
        nonlocal current_test, current_complement, test_counter, pending_new_section
        finalize_test()

        count = test_counter.get(topic_slug, 0) + 1
        test_counter[topic_slug] = count

        year_prefix = str(year) if year else "unknown"
        test_id = f"{year_prefix}_{topic_slug}_{count}"

        current_test = {
            "test_id": test_id,
            "title": title,
            "author": author,
            "topic": topic_slug,
            "type": test_type,
            "questions": [],
        }
        current_complement = None
        pending_new_section = False

    i = 0
    skip_cuprins = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        i += 1

        # Strip markdown formatting (Mistral OCR output)
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        # Strip bold markers (**text**)
        if stripped.startswith("**") and stripped.endswith("**"):
            stripped = stripped[2:-2].strip()
        # Strip list markers (- A. choice text)
        if stripped.startswith("- ") and len(stripped) > 2:
            stripped = stripped[2:].strip()
        # Strip "Capitolul N." prefix (2021/2023 book-style chapter headers)
        _had_capitolul_prefix = False
        _m_cap = re.match(r"^Capitolul\s+\d+\s*[.:]\s*", stripped, re.IGNORECASE)
        if _m_cap:
            _cap_rest = stripped[_m_cap.end():].strip()
            if _cap_rest:
                _had_capitolul_prefix = True
                stripped = _cap_rest

        # Skip page markers
        if RE_PAGE_MARKER.match(stripped):
            continue

        # Skip empty lines
        if not stripped:
            continue

        # Skip standalone page numbers
        if RE_PAGE_NUMBER.match(stripped):
            continue

        # --- CUPRINS skipping ---
        if RE_CUPRINS.match(stripped):
            skip_cuprins = True
            continue
        if skip_cuprins:
            # End cuprins when we hit real content markers
            if (is_topic_header_line(stripped) and not re.search(r"\.\.\.", stripped)):
                skip_cuprins = False
                i -= 1
                continue
            if RE_COMPLEMENT_HEADER.match(stripped):
                skip_cuprins = False
                i -= 1
                continue
            if RE_AUTHOR.match(stripped):
                skip_cuprins = False
                i -= 1
                continue
            # CUPRINS entries like "11. TESTE GENERALE" start with a digit;
            # real section headers don't.
            if RE_TESTE_GENERALE.match(stripped) and not re.match(r"^\s*\d", stripped):
                skip_cuprins = False
                i -= 1
                continue
            # CUPRINS entries like "1. TESTE RECAPITULATIVE" start with a digit;
            # real headers use "L TESTE RECAPITULATIVE" or bare "TESTE RECAPITULATIV".
            if RE_TESTE_PE_CAPITOLE.match(stripped) and not re.match(r"^\s*\d", stripped):
                skip_cuprins = False
                i -= 1
                continue
            # CUPRINS test names are followed by page numbers on the next line;
            # real TEST headers are followed by complement headers or questions.
            if RE_TEST_HEADER.match(stripped) and not re.search(r"\.\.\.", stripped):
                _next_is_page = False
                for _la in range(i, min(i + 3, len(lines))):
                    _la_s = lines[_la].strip()
                    if not _la_s or RE_PAGE_MARKER.match(_la_s):
                        continue
                    if RE_PAGE_NUMBER.match(_la_s):
                        _next_is_page = True
                    break
                if not _next_is_page:
                    skip_cuprins = False
                    i -= 1
                    continue
            continue

        # Skip non-content lines
        if is_skippable_line(stripped):
            continue

        # --- TESTE GENERALE detection ---
        if RE_TESTE_GENERALE.match(stripped):
            in_general_tests = True
            continue

        # --- TESTE PE CAPITOLE detection ---
        if RE_TESTE_PE_CAPITOLE.match(stripped):
            continue

        # --- RĂSPUNSURI header ---
        # Check both stripped line and individual table cells
        _raspunsuri_match = (RE_RASPUNSURI.match(stripped) or RE_RASPUNSURI_OCR.match(stripped)
                             or RE_RASPUNSURI_SPACED.match(stripped) or RE_RASPUNSURI_MISSPELL.match(stripped)
                             or RE_RASPUNSURI_TRUNCATED.match(stripped))
        if not _raspunsuri_match and "|" in stripped:
            for _cell in stripped.split("|"):
                _c = _cell.strip()
                if RE_RASPUNSURI.match(_c) or RE_RASPUNSURI_OCR.match(_c):
                    _raspunsuri_match = True
                    break
        if _raspunsuri_match:
            finalize_question()
            # If already in answer mode, finalize current answers before starting
            # new answer section (2009 has multiple RĂSPUNSURI headers in sequence)
            if in_answers and answer_lines_buffer:
                finalize_answers()
            in_answers = True
            answer_lines_buffer = []
            pending_new_section = True  # After answers, next topic/complement = new test
            # Extract inline answer content from the same line (e.g.
            # "Răspunsuri complement simplu 8 B pg. 15")
            remainder = RE_RASPUNSURI_PREFIX.sub("", stripped).strip()
            if remainder and RE_ANSWER_INLINE.search(remainder):
                answer_lines_buffer.append(remainder)
            continue

        # --- Answer accumulation mode ---
        if in_answers:
            # Check for section-ending markers
            if RE_AUTHOR.match(stripped):
                finalize_answers()
                i -= 1
                continue

            if RE_TEST_HEADER.match(stripped) or RE_TEST_GENERAL_HEADER.match(stripped):
                # 2023: "CAPITOLUL 14. TEST GENERAL" appears as a label between
                # RĂSPUNSURI header and actual answer lines. If buffer is empty and
                # line had a Capitolul prefix, skip this and any following metadata
                # (author, complement headers) until answer lines start.
                if _had_capitolul_prefix and not answer_lines_buffer:
                    while i < len(lines):
                        _sk = lines[i].strip()
                        if _sk.startswith("#"):
                            _sk = _sk.lstrip("#").strip()
                        if not _sk or RE_PAGE_MARKER.match(_sk) or RE_PAGE_NUMBER.match(_sk):
                            i += 1; continue
                        if RE_AUTHOR.match(_sk):
                            i += 1; continue
                        _isch, _ = is_complement_header(_sk)
                        if _isch:
                            i += 1; continue
                        break
                    continue
                finalize_answers()
                i -= 1
                continue

            if RE_TESTE_GENERALE.match(stripped):
                finalize_answers()
                i -= 1
                continue

            if is_topic_header_line(stripped):
                # Is this a topic label within the answer section, or a new section?
                # Look ahead: if followed by complement header or answer lines, it's
                # part of the answers. If followed by questions, it's a new section.
                is_answer_section_topic = False
                for la in range(i, min(i + 5, len(lines))):
                    la_line = lines[la].strip()
                    if not la_line or RE_PAGE_MARKER.match(la_line) or RE_PAGE_NUMBER.match(la_line):
                        continue
                    is_ch, _ = is_complement_header(la_line)
                    if is_ch:
                        is_answer_section_topic = True
                        break
                    if RE_ANSWER_LINE.match(la_line) or RE_ANSWER_NOSEP.match(la_line):
                        is_answer_section_topic = True
                        break
                    if RE_QUESTION_START.match(la_line):
                        break
                    if RE_AUTHOR.match(la_line):
                        break
                    break

                if not is_answer_section_topic:
                    finalize_answers()
                    i -= 1
                    continue

            # Accumulate answer line
            answer_lines_buffer.append(line)
            continue

        # --- Author line ---
        m_author = RE_AUTHOR.match(stripped)
        if m_author:
            current_author = m_author.group(1).strip()
            # If we just created a test (from TEST header) with 0 questions,
            # update its author rather than marking a new section
            if current_test and not current_test["questions"]:
                current_test["author"] = current_author
            else:
                pending_new_section = True
            continue

        # --- TEST N header ---
        m_test = RE_TEST_HEADER.match(stripped)
        if m_test:
            test_type = "general_test" if in_general_tests else "chapter_test"
            title = stripped
            topic_slug = "general" if in_general_tests else (current_topic or "general")

            # Look ahead for author
            for la in range(i, min(i + 4, len(lines))):
                la_line = lines[la].strip()
                if not la_line or RE_PAGE_MARKER.match(la_line) or RE_PAGE_NUMBER.match(la_line):
                    continue
                m_la_auth = RE_AUTHOR.match(la_line)
                if m_la_auth:
                    current_author = m_la_auth.group(1).strip()
                    break
                break

            current_topic_title = title
            current_topic = topic_slug
            start_new_test(title, topic_slug, current_author, test_type)
            continue

        # --- TEST GENERAL header (without number) ---
        m_test_gen = RE_TEST_GENERAL_HEADER.match(stripped)
        if m_test_gen:
            in_general_tests = True
            title = stripped

            # Look ahead for author
            for la in range(i, min(i + 4, len(lines))):
                la_line = lines[la].strip()
                if not la_line or RE_PAGE_MARKER.match(la_line) or RE_PAGE_NUMBER.match(la_line):
                    continue
                m_la_auth = RE_AUTHOR.match(la_line)
                if m_la_auth:
                    current_author = m_la_auth.group(1).strip()
                    break
                break

            current_topic_title = title
            current_topic = "general"
            start_new_test(title, "general", current_author, "general_test")
            continue

        # --- Topic header ---
        if is_topic_header_line(stripped):
            # Multi-line topic continuation
            full_title = stripped
            peek = i
            while peek < len(lines):
                peek_line = lines[peek].strip()
                if not peek_line or RE_PAGE_MARKER.match(peek_line) or RE_PAGE_NUMBER.match(peek_line):
                    peek += 1
                    continue
                # Strip markdown from peek line for header detection
                peek_clean = peek_line
                if peek_clean.startswith("#"):
                    peek_clean = peek_clean.lstrip("#").strip()
                if peek_clean.startswith("**") and peek_clean.endswith("**"):
                    peek_clean = peek_clean[2:-2].strip()
                is_ch, _ = is_complement_header(peek_clean)
                if is_ch:
                    break
                if RE_TEST_HEADER.match(peek_clean) or RE_AUTHOR.match(peek_clean):
                    break
                if (peek_line.isupper() or peek_line.endswith(".")) and not RE_RASPUNSURI.match(peek_clean):
                    if len(peek_line) > 3 and not RE_QUESTION_START.match(peek_line) and not peek_line[0].isdigit():
                        full_title += " " + peek_clean
                        i = peek + 1
                        peek += 1
                        continue
                break

            topic_slug = detect_topic(full_title)
            if topic_slug != "unknown":
                current_topic_title = full_title
                current_topic = topic_slug
                in_general_tests = False  # chapter topic overrides general flag
                pending_new_section = True
                pending_topic_change = True
            continue

        # --- Complement header ---
        is_ch, complement_type = is_complement_header(stripped)
        if is_ch:
            # Detect answer section without RĂSPUNSURI header (2009 TEST 3,
            # 2016 EXCRETOR):  A complement header followed by answer-format
            # lines with page references.  Requires 2+ consecutive answer-like
            # lines.  Collects answers inline (NOT full answer mode) so
            # subsequent questions in the same test are not absorbed.
            if not in_answers and current_test and current_test["questions"]:
                _ans_sect_count = 0
                for _la in range(i, min(i + 10, len(lines))):
                    _la_line = lines[_la].strip()
                    if not _la_line or RE_PAGE_MARKER.match(_la_line) or RE_PAGE_NUMBER.match(_la_line):
                        continue
                    _la_fixed = fix_ocr_answer_line(_la_line)
                    _m_la = RE_ANSWER_LINE.match(_la_fixed) or RE_ANSWER_NOSEP.match(_la_fixed)
                    if _m_la:
                        _la_text = (_m_la.group(3) if _m_la.group(3) else "").strip()
                        if _la_text and re.match(r"(?:p[.\s]|pg|pag|[(])", _la_text, re.IGNORECASE):
                            _ans_sect_count += 1
                            if _ans_sect_count >= 2:
                                break
                            continue
                    break
                if _ans_sect_count >= 2:
                    finalize_question()
                    embedded_buf = [stripped]
                    while i < len(lines):
                        _el = lines[i].strip()
                        if not _el or RE_PAGE_MARKER.match(_el) or RE_PAGE_NUMBER.match(_el):
                            embedded_buf.append(lines[i])
                            i += 1
                            continue
                        _el_fixed = fix_ocr_answer_line(_el)
                        if (RE_ANSWER_LINE.match(_el_fixed)
                                or RE_ANSWER_NOSEP.match(_el_fixed)
                                or RE_ANSWER_CONTINUATION.match(_el)):
                            embedded_buf.append(lines[i])
                            i += 1
                            continue
                        break
                    if embedded_buf:
                        emb_answers = parse_answer_lines(embedded_buf)
                        if emb_answers:
                            deferred_answers.update(emb_answers)
                    continue

            # Lookahead: if this is a DUPLICATE complement header (same type already
            # active) AND next lines are answer lines, it labels an embedded answer
            # section, not new questions. (2016 EXCRETOR/METABOLISMUL have answers
            # inline with duplicate complement headers mid-question-section.)
            _ans_lookahead = False
            if (current_complement == complement_type
                    and current_test and current_test["questions"]
                    and not pending_new_section):
                for _la in range(i, min(i + 5, len(lines))):
                    _la_line = lines[_la].strip()
                    if not _la_line or RE_PAGE_MARKER.match(_la_line) or RE_PAGE_NUMBER.match(_la_line):
                        continue
                    _la_fixed = fix_ocr_answer_line(_la_line)
                    if RE_ANSWER_LINE.match(_la_fixed) or RE_ANSWER_NOSEP.match(_la_fixed):
                        _ans_lookahead = True
                    break
            if _ans_lookahead:
                # Collect embedded answers inline without entering full answer mode.
                finalize_question()
                embedded_buf = []
                while i < len(lines):
                    _el = lines[i].strip()
                    if not _el or RE_PAGE_MARKER.match(_el) or RE_PAGE_NUMBER.match(_el):
                        embedded_buf.append(lines[i])
                        i += 1
                        continue
                    if RE_ANSWER_LINE.match(_el) or RE_ANSWER_NOSEP.match(_el) or RE_ANSWER_CONTINUATION.match(_el):
                        embedded_buf.append(lines[i])
                        i += 1
                        continue
                    break  # Non-answer line — stop collecting
                # Defer embedded answers for application at test finalization
                if embedded_buf:
                    emb_answers = parse_answer_lines(embedded_buf)
                    if emb_answers:
                        deferred_answers.update(emb_answers)
                continue

            finalize_question()

            if current_test is None:
                # No test yet — start one
                title = current_topic_title or "Unknown"
                topic_slug = current_topic or "unknown"
                test_type = "general_test" if in_general_tests else "chapter_test"
                start_new_test(title, topic_slug, current_author, test_type)
            elif pending_new_section and current_test["questions"]:
                # There's an existing test with questions, and we've seen signals
                # (author/topic/raspunsuri) indicating a new section
                title = current_topic_title or "Unknown"
                topic_slug = current_topic or "unknown"
                test_type = "general_test" if in_general_tests else "chapter_test"
                start_new_test(title, topic_slug, current_author, test_type)

            current_complement = complement_type
            pending_new_section = False
            pending_topic_change = False

            # Detect numbered choices (1-5) for complement_simplu sections.
            # Some files (e.g. 2009) use "1." through "5." instead of "A." through "E."
            numbered_simplu_choices = False
            if complement_type == "complement_simplu":
                _la_idx = i
                _found_q = False
                while _la_idx < min(i + 30, len(lines)):
                    _la_s = lines[_la_idx].strip()
                    _la_idx += 1
                    if not _la_s or RE_PAGE_MARKER.match(_la_s) or RE_PAGE_NUMBER.match(_la_s):
                        continue
                    if not _found_q:
                        if RE_QUESTION_START.match(_la_s):
                            _found_q = True
                        continue
                    # After the first question line, check what follows
                    if RE_CHOICE_SIMPLU.match(_la_s):
                        break  # Standard A-E letter choices
                    if re.match(r"^\s*[1-5]\s*\.\s*", _la_s):
                        numbered_simplu_choices = True
                    break
            continue

        # --- Skip if no active test ---
        if not current_test:
            continue

        # --- New test from topic header without complement header ---
        # If a TOPIC HEADER (not just RĂSPUNSURI/author) signalled a new section
        # and we see question 1 starting, begin a new test even without a complement
        # header.  This handles files like 2020 where MIȘCAREA (2) jumps straight
        # into questions without an explicit complement header.
        if pending_topic_change and current_test["questions"]:
            _m_q_check = RE_QUESTION_START.match(stripped)
            if _m_q_check and int(_m_q_check.group(1)) == 1:
                finalize_question()
                _title = current_topic_title or "Unknown"
                _topic_slug = current_topic or "unknown"
                _test_type = "general_test" if in_general_tests else "chapter_test"
                start_new_test(_title, _topic_slug, current_author, _test_type)
                pending_new_section = False
                pending_topic_change = False
                current_complement = None  # Auto-detect from choices

        # --- Auto-detect complement type if missing or mismatched ---
        if current_complement in (None, "complement_simplu") and RE_QUESTION_START.match(stripped):
            # Look ahead for choice patterns to determine type
            for la in range(i, min(i + 8, len(lines))):
                la_stripped = lines[la].strip()
                if not la_stripped:
                    continue
                if RE_PAGE_MARKER.match(la_stripped) or RE_PAGE_NUMBER.match(la_stripped):
                    continue
                if RE_CHOICE_SIMPLU.match(la_stripped):
                    if current_complement is None:
                        current_complement = "complement_simplu"
                    break
                if RE_CHOICE_GRUPAT.match(la_stripped):
                    current_complement = "complement_grupat"
                    break
                break  # non-empty, non-choice line — stop looking

        # --- Question and choice parsing ---
        if current_complement == "complement_simplu":
            # Choice line (A-E)
            m_choice = RE_CHOICE_SIMPLU.match(stripped)
            if m_choice and current_question:
                choice_key = m_choice.group(1).upper()
                choice_text = m_choice.group(2).strip()

                while i < len(lines):
                    next_stripped = lines[i].strip()
                    if not next_stripped:
                        break
                    if RE_PAGE_MARKER.match(next_stripped):
                        i += 1
                        continue
                    if RE_PAGE_NUMBER.match(next_stripped):
                        i += 1
                        continue
                    if (RE_CHOICE_SIMPLU.match(next_stripped) or
                            RE_QUESTION_START.match(next_stripped)):
                        break
                    is_ch2, _ = is_complement_header(next_stripped)
                    if is_ch2 or RE_RASPUNSURI.match(next_stripped) or RE_AUTHOR.match(next_stripped):
                        break
                    if is_topic_header_line(next_stripped) or RE_TEST_HEADER.match(next_stripped):
                        break
                    choice_text += " " + next_stripped
                    i += 1

                current_question["choices"][choice_key] = choice_text
                continue

            # Numbered choices (1-5) used instead of A-E in some files (e.g. 2009)
            if numbered_simplu_choices and current_question:
                m_num = re.match(r"^\s*([1-5])\s*\.\s*(.*)$", stripped)
                if m_num:
                    num = int(m_num.group(1))
                    choice_text = m_num.group(2).strip()

                    while i < len(lines):
                        next_stripped = lines[i].strip()
                        if not next_stripped:
                            break
                        if RE_PAGE_MARKER.match(next_stripped):
                            i += 1
                            continue
                        if RE_PAGE_NUMBER.match(next_stripped):
                            i += 1
                            continue
                        if re.match(r"^\s*[1-5]\s*[.\)]", next_stripped):
                            break
                        if RE_QUESTION_START.match(next_stripped):
                            break
                        is_ch2, _ = is_complement_header(next_stripped)
                        if is_ch2 or RE_RASPUNSURI.match(next_stripped) or RE_AUTHOR.match(next_stripped):
                            break
                        if is_topic_header_line(next_stripped) or RE_TEST_HEADER.match(next_stripped):
                            break
                        choice_text += " " + next_stripped
                        i += 1

                    letter_map = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
                    current_question["choices"][letter_map[num]] = choice_text
                    continue

            # Question start
            m_q = RE_QUESTION_START.match(stripped)
            if m_q:
                finalize_question()
                q_num = int(m_q.group(1))
                q_text = m_q.group(2).strip()

                while i < len(lines):
                    next_stripped = lines[i].strip()
                    if not next_stripped:
                        break
                    if RE_PAGE_MARKER.match(next_stripped):
                        i += 1
                        continue
                    if RE_PAGE_NUMBER.match(next_stripped):
                        i += 1
                        continue
                    if RE_CHOICE_SIMPLU.match(next_stripped):
                        break
                    # In numbered mode, also break on numbered choices
                    if numbered_simplu_choices and re.match(r"^\s*[1-5]\s*[.\)]", next_stripped):
                        break
                    if RE_QUESTION_START.match(next_stripped):
                        break
                    is_ch2, _ = is_complement_header(next_stripped)
                    if is_ch2 or RE_RASPUNSURI.match(next_stripped):
                        break
                    q_text += " " + next_stripped
                    i += 1

                test_id_base = current_test["test_id"]
                current_question = {
                    "id": f"{test_id_base}_q{q_num}",
                    "number": q_num,
                    "type": "complement_simplu",
                    "text": q_text,
                    "choices": {},
                    "correct_answer": None,
                    "correct_statements": None,
                    "page_ref": None,
                }
                continue

        elif current_complement == "complement_grupat":
            # Choice line (1-4)
            m_choice = RE_CHOICE_GRUPAT.match(stripped)
            if m_choice and current_question:
                choice_key = m_choice.group(1)
                choice_text = m_choice.group(2).strip()

                while i < len(lines):
                    next_stripped = lines[i].strip()
                    if not next_stripped:
                        break
                    if RE_PAGE_MARKER.match(next_stripped):
                        i += 1
                        continue
                    if RE_PAGE_NUMBER.match(next_stripped):
                        i += 1
                        continue
                    if (RE_CHOICE_GRUPAT.match(next_stripped) or
                            RE_QUESTION_START.match(next_stripped)):
                        break
                    is_ch2, _ = is_complement_header(next_stripped)
                    if is_ch2 or RE_RASPUNSURI.match(next_stripped) or RE_AUTHOR.match(next_stripped):
                        break
                    if is_topic_header_line(next_stripped) or RE_TEST_HEADER.match(next_stripped):
                        break
                    choice_text += " " + next_stripped
                    i += 1

                current_question["choices"][choice_key] = choice_text
                continue

            # Question start
            m_q = RE_QUESTION_START.match(stripped)
            if m_q:
                finalize_question()
                q_num = int(m_q.group(1))
                q_text = m_q.group(2).strip()

                while i < len(lines):
                    next_stripped = lines[i].strip()
                    if not next_stripped:
                        break
                    if RE_PAGE_MARKER.match(next_stripped):
                        i += 1
                        continue
                    if RE_PAGE_NUMBER.match(next_stripped):
                        i += 1
                        continue
                    if RE_CHOICE_GRUPAT.match(next_stripped):
                        break
                    if RE_QUESTION_START.match(next_stripped):
                        break
                    is_ch2, _ = is_complement_header(next_stripped)
                    if is_ch2 or RE_RASPUNSURI.match(next_stripped):
                        break
                    q_text += " " + next_stripped
                    i += 1

                test_id_base = current_test["test_id"]
                current_question = {
                    "id": f"{test_id_base}_q{q_num}",
                    "number": q_num,
                    "type": "complement_grupat",
                    "text": q_text,
                    "choices": {},
                    "correct_answer": None,
                    "correct_statements": None,
                    "page_ref": None,
                }
                continue

    # Finalize last test
    finalize_test()

    return {
        "file": filename,
        "year": year,
        "subject": subject,
        "extraction_method": "pymupdf",
        "tests": tests,
    }


def main():
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(NORMALIZED_DIR.glob("*.md"))
    if not md_files:
        print("No normalized .md files found in", NORMALIZED_DIR)
        return

    for filepath in md_files:
        print(f"Parsing: {filepath.name}")
        result = parse_file(filepath)

        out_path = PARSED_DIR / f"{filepath.stem.strip()}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        total_q = sum(len(t["questions"]) for t in result["tests"])
        total_a = sum(
            1 for t in result["tests"]
            for q in t["questions"]
            if q.get("correct_answer")
        )
        print(f"  -> {len(result['tests'])} tests, {total_q} questions, {total_a} with answers")
        print(f"  -> Saved to {out_path}")


if __name__ == "__main__":
    main()
