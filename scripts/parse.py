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
    (r"MIȘCAR|MISCAR|OSOS|MUSCUL|OSTEO", "miscarea"),
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
    r"(S\s*I\s*M\s*P\s*L\s*U|U\s*N\s*I\s*C|T\s*J\s*N\s*I\s*C|"
    r"G\s*R\s*U\s*P\s*A\s*T|M\s*U\s*L\s*T\s*I\s*P\s*L\s*U|"
    r"C\s*O\s*M\s*P\s*U\s*S|M\s*U\s*L\s*T\s*U\s*P\s*L\s*U)",
    re.IGNORECASE,
)

# RĂSPUNSURI / RASPUNSURI header
RE_RASPUNSURI = re.compile(r"^\s*R[ĂAÃ]SPUNSURI\s*:?\s*$", re.IGNORECASE)

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
RE_CHOICE_GRUPAT = re.compile(r"^\s*([1-4])\s*[.\)]\s*(.*)$")

# Test header: TEST 1 / TEST1 / TESTÓ / TEST GENERAL etc.
RE_TEST_HEADER = re.compile(r"^\s*TEST\s*[OÓ]?\s*(\d+)\s*$", re.IGNORECASE)
RE_TEST_GENERAL_HEADER = re.compile(r"^\s*TEST\s+GENERAL\s*(\d*)\s*$", re.IGNORECASE)
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
    r"^\s*(\d{1,3})\s*[-.\s,)]+\s*([A-Ea-e])\s*[-.\s,)]*\s*(.*)?$"
)
RE_ANSWER_NOSEP = re.compile(
    r"^\s*(\d{1,3})\s*([A-Ea-e])\s*[-.\s,)]*\s*(.*)?$"
)
RE_ANSWER_CONTINUATION = re.compile(
    r"^\s*(?:pag|pg|fig|\.fig|\.pag|\(pag|\(pg)", re.IGNORECASE
)


def classify_complement(text: str) -> str:
    """Classify a complement header match as simplu or grupat."""
    collapsed = re.sub(r"\s+", "", text).upper()
    if collapsed in ("SIMPLU", "UNIC", "TJNIC"):
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
    m = RE_COMPLEMENT_HEADER.match(line.strip())
    if m:
        return True, classify_complement(m.group(1))

    stripped = line.strip().rstrip(":. ")
    collapsed = re.sub(r"\s+", "", stripped.lower())
    if collapsed in (
        "complementsimplu", "complementunic", "complementtjnic",
        "complementgrupat", "complementmultiplu", "complementcompus",
        "complementmultuplu",
        # OCR variants
        "compementsimplu", "compementgrupat", "compementmultiplu",
        "compementcompus",
    ):
        if collapsed in ("complementsimplu", "complementunic", "complementtjnic",
                         "compementsimplu"):
            return True, "complement_simplu"
        return True, "complement_grupat"

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
    - 'l' or 't' used instead of '1' in answer numbers
    - 's' used instead of '5' in answer numbers
    - 'ps.' or 'pe.' instead of 'pg.'
    """
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
    # Pattern: after number+separator, '8' followed by space or paren or dot
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)8(\s*[(\s.])", r"\1B\2", line)
    # Also handle "8 pg" or "8pg"
    line = re.sub(r"^(\s*\d{1,3}\s*[.\-,)\s]+\s*)8(p[gaes])", r"\1B \2", line)

    return line


def parse_answer_lines(lines: list[str]) -> dict[int, tuple[str, str | None]]:
    """Parse answer key lines into {question_number: (letter, page_ref)}."""
    answers = {}
    i = 0

    while i < len(lines):
        line = fix_ocr_answer_line(lines[i])
        stripped = line.strip()
        i += 1

        if not stripped:
            continue

        # Skip page markers (but NOT standalone page numbers — they might be
        # split answer numbers like "10" or "31")
        if RE_PAGE_MARKER.match(stripped):
            continue

        # Skip complement section headers and topic headers within answers
        is_ch, _ = is_complement_header(stripped)
        if is_ch:
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
                    num = int(m.group(1))
                    letter = m.group(2).upper()
                    pref = parse_page_ref(m.group(3)) if m.group(3) else None
                    temp_answers[num] = (letter, pref)
                else:
                    parsed_both = False
                    break
            if parsed_both and len(temp_answers) >= 2:
                answers.update(temp_answers)
                continue

        # Try standard answer line
        m = RE_ANSWER_LINE.match(stripped)
        if not m:
            m = RE_ANSWER_NOSEP.match(stripped)
        if m:
            num = int(m.group(1))
            letter = m.group(2).upper()
            page_text = m.group(3) if m.group(3) else ""

            # Collect continuation lines
            while i < len(lines):
                next_line = lines[i].strip()
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
                num = int(num_str)
                letter = m_ocr.group(2).upper()
                rest = stripped[m_ocr.end():]
                pref = parse_page_ref(rest)
                answers[num] = (letter, pref)
            except ValueError:
                pass
            continue

        # Handle split answers: number on one line (e.g. "10." or "10"),
        # letter on the next line (e.g. "D (pag. 43)" or "B (pg 118)")
        m_num_only = re.match(r"^\s*(\d{1,3})\s*[.\s)]*\s*$", stripped)
        if m_num_only:
            num = int(m_num_only.group(1))
            # Look ahead for the letter on the next non-empty line
            while i < len(lines):
                next_stripped = lines[i].strip()
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
                    while i < len(lines):
                        cont = lines[i].strip()
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
                r"nAspuN|ALEGETI|SINGIIR)", stripped, re.IGNORECASE):
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
    in_general_tests = False
    test_counter = {}
    # Flag: we've seen a new topic/author and expect a new test at next complement header
    pending_new_section = False

    def finalize_question():
        nonlocal current_question
        if current_question and current_test:
            current_question["text"] = current_question["text"].strip()
            # Discard zero-choice "questions" that are actually answer lines
            # (e.g. "Apg.6", "Dpg.7" — a letter immediately followed by pg/pag)
            if not current_question["choices"] and re.search(
                r"[A-Ea-e]\s*p(?:a)?g", current_question["text"]
            ):
                current_question = None
                return
            current_test["questions"].append(current_question)
        current_question = None

    def finalize_answers():
        nonlocal in_answers, answer_lines_buffer
        if in_answers and answer_lines_buffer and current_test:
            match_answers_to_test(current_test, answer_lines_buffer)
        answer_lines_buffer = []
        in_answers = False

    def finalize_test():
        nonlocal current_test
        finalize_question()
        finalize_answers()
        if current_test and current_test["questions"]:
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

    def match_answers_to_test(test, ans_lines):
        answers = parse_answer_lines(ans_lines)
        if not answers:
            return
        for q in test["questions"]:
            qnum = q["number"]
            if qnum in answers:
                letter, pref = answers[qnum]
                q["correct_answer"] = letter
                q["page_ref"] = pref
                if q["type"] == "complement_grupat":
                    q["correct_statements"] = GRUPAT_DECODE.get(letter)

    i = 0
    skip_cuprins = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        i += 1

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
            if RE_TESTE_GENERALE.match(stripped):
                skip_cuprins = False
                i -= 1
                continue
            if RE_TESTE_PE_CAPITOLE.match(stripped):
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
        if RE_RASPUNSURI.match(stripped):
            finalize_question()
            in_answers = True
            answer_lines_buffer = []
            pending_new_section = True  # After answers, next topic/complement = new test
            continue

        # --- Answer accumulation mode ---
        if in_answers:
            # Check for section-ending markers
            if RE_AUTHOR.match(stripped):
                finalize_answers()
                i -= 1
                continue

            if RE_TEST_HEADER.match(stripped) or RE_TEST_GENERAL_HEADER.match(stripped):
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
            test_num = int(m_test.group(1))
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
                is_ch, _ = is_complement_header(peek_line)
                if is_ch:
                    break
                if (peek_line.isupper() or peek_line.endswith(".")) and not RE_AUTHOR.match(peek_line) and not RE_RASPUNSURI.match(peek_line):
                    if len(peek_line) > 3 and not RE_QUESTION_START.match(peek_line) and not peek_line[0].isdigit():
                        full_title += " " + peek_line
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
            continue

        # --- Complement header ---
        is_ch, complement_type = is_complement_header(stripped)
        if is_ch:
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
            continue

        # --- Skip if no active test ---
        if not current_test:
            continue

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
