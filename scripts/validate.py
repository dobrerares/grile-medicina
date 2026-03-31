#!/usr/bin/env python3
"""Validate parsed question JSON files for structural correctness."""

import json
import sys
from pathlib import Path

PARSED_DIR = Path(__file__).resolve().parent.parent / "parsed"

CS_EXPECTED_KEYS = {"A", "B", "C", "D", "E"}
CG_EXPECTED_KEYS = {"1", "2", "3", "4"}
VALID_ANSWER_LETTERS = {"A", "B", "C", "D", "E"}


def validate_file(filepath: Path) -> tuple[int, int, list[str]]:
    """Validate a single parsed JSON file.

    Returns (total_questions, answered_count, list_of_issues).
    """
    with open(filepath) as f:
        data = json.load(f)

    issues: list[str] = []
    total = 0
    answered = 0

    for test in data.get("tests", []):
        test_id = test.get("test_id", "unknown_test")
        seen_numbers: dict[int, str] = {}

        for q in test.get("questions", []):
            total += 1
            qid = q.get("id", f"{test_id}/q?")
            qnum = q.get("number")
            qtype = q.get("type", "")
            text = q.get("text", "")
            choices = q.get("choices", {})
            answer = q.get("correct_answer")

            # 3. Duplicate question numbers within a test
            if qnum is not None:
                if qnum in seen_numbers:
                    issues.append(
                        f"{qid}: duplicate question number {qnum} "
                        f"(also {seen_numbers[qnum]})"
                    )
                else:
                    seen_numbers[qnum] = qid

            # 4. Empty/short question text
            if len(text.strip()) < 5:
                issues.append(f"{qid}: question text too short ({len(text.strip())} chars)")

            # 1. Choice count validation
            choice_keys = set(choices.keys())
            if qtype == "complement_simplu":
                missing = CS_EXPECTED_KEYS - choice_keys
                extra = choice_keys - CS_EXPECTED_KEYS
                if missing or extra:
                    issues.append(
                        f"{qid}: CS choices mismatch — missing={missing}, extra={extra}"
                    )
            elif qtype == "complement_grupat":
                missing = CG_EXPECTED_KEYS - choice_keys
                extra = choice_keys - CG_EXPECTED_KEYS
                if missing or extra:
                    issues.append(
                        f"{qid}: CG choices mismatch — missing={missing}, extra={extra}"
                    )

            # 5. Empty/short choice text
            for key, val in choices.items():
                if len(str(val).strip()) < 2:
                    issues.append(
                        f"{qid}: choice {key} text too short "
                        f"({len(str(val).strip())} chars)"
                    )

            # 6. Invalid answer letters
            if answer:
                if answer not in VALID_ANSWER_LETTERS:
                    issues.append(f"{qid}: invalid answer letter '{answer}'")
                answered += 1
            # 2. Track unanswered (handled via answered count)

    return total, answered, issues


def main() -> None:
    if not PARSED_DIR.is_dir():
        print(f"ERROR: parsed directory not found at {PARSED_DIR}")
        sys.exit(1)

    json_files = sorted(PARSED_DIR.glob("*.json"))
    if not json_files:
        print(f"No .json files found in {PARSED_DIR}")
        sys.exit(1)

    grand_total = 0
    grand_answered = 0
    grand_issues = 0

    for filepath in json_files:
        total, answered, issues = validate_file(filepath)
        grand_total += total
        grand_answered += answered
        grand_issues += len(issues)

        pct = (100 * answered / total) if total else 0
        name = filepath.name

        if not issues:
            print(f"PASS: {name} — {total} questions, {answered} answered ({pct:.1f}%)")
        else:
            label = "WARN" if pct >= 50 else "FAIL"
            print(
                f"{label} ({len(issues)} issues): {name} — "
                f"{total} questions, {answered} answered ({pct:.1f}%)"
            )
            for issue in issues[:10]:
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... ({len(issues) - 10} more issues not shown)")

    # Final summary
    overall_pct = (100 * grand_answered / grand_total) if grand_total else 0
    print()
    print(f"Total: {grand_total} questions, {grand_answered} with answers")
    print(f"Issues: {grand_issues}")
    print(f"Answer coverage: {overall_pct:.1f}%")

    if grand_issues > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
