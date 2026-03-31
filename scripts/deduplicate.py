"""Deduplicate questions across same-year PDF files.

Some years have two PDFs (different scans of the same book). This script
merges them using fuzzy text matching: keeps the version with the most
answered questions as primary and adds any unique questions from the
secondary file.

Usage:
    nix-shell -p python3Packages.rapidfuzz --run "python scripts/deduplicate.py"
"""

import json
from pathlib import Path

from rapidfuzz import fuzz

# Groups of files that are duplicate scans of the same book.
# First entry is preferred if answer counts are equal.
DUPLICATE_GROUPS = [
    ["Biologie 2010 UMFCD", "Biologie 2010 UMFCD "],
    ["Biologie 2016 UMFCD", "Biologie 2016 UMFCD-"],
    ["Biologie 2020 UMFCD", "Biologie 2020 UMFCD-"],
]

FUZZY_THRESHOLD = 85


def count_answered(data: dict) -> int:
    """Count questions that have a non-null correct_answer."""
    return sum(
        1
        for test in data["tests"]
        for q in test["questions"]
        if q.get("correct_answer")
    )


def question_signature(q: dict) -> str:
    """Build a text signature for fuzzy comparison.

    Combines question text with sorted choice texts for a richer match.
    """
    parts = [q.get("text", "")]
    choices = q.get("choices", {})
    for key in sorted(choices.keys()):
        parts.append(choices[key])
    return " ".join(parts)


def find_duplicate_in_primary(
    q_sig: str, primary_sigs: list[str]
) -> int | None:
    """Return index of the best fuzzy match in primary_sigs, or None."""
    best_score = 0
    best_idx = None
    for idx, p_sig in enumerate(primary_sigs):
        score = fuzz.ratio(q_sig, p_sig)
        if score > best_score:
            best_score = score
            best_idx = idx
    if best_score >= FUZZY_THRESHOLD:
        return best_idx
    return None


def merge_files(primary_data: dict, secondary_data: dict) -> dict:
    """Merge secondary into primary, adding unique questions."""
    result = json.loads(json.dumps(primary_data))  # deep copy

    # Build a flat index of all primary question signatures
    primary_sigs = []
    primary_q_refs = []  # (test_idx, question_idx) for each sig
    for ti, test in enumerate(result["tests"]):
        for qi, q in enumerate(test["questions"]):
            primary_sigs.append(question_signature(q))
            primary_q_refs.append((ti, qi))

    # Walk secondary questions, find unique ones
    unique_questions = []  # (secondary_test, question)
    duplicates_found = 0

    for test in secondary_data["tests"]:
        for q in test["questions"]:
            sec_sig = question_signature(q)
            match_idx = find_duplicate_in_primary(sec_sig, primary_sigs)
            if match_idx is not None:
                duplicates_found += 1
                # If secondary question has an answer but primary doesn't,
                # copy the answer over
                ti, qi = primary_q_refs[match_idx]
                pq = result["tests"][ti]["questions"][qi]
                if not pq.get("correct_answer") and q.get("correct_answer"):
                    pq["correct_answer"] = q["correct_answer"]
                if not pq.get("correct_statements") and q.get("correct_statements"):
                    pq["correct_statements"] = q["correct_statements"]
            else:
                unique_questions.append((test, q))

    # Add unique questions: group them into a new test if any exist
    if unique_questions:
        extra_test = {
            "test_id": f"{result.get('year', 'unknown')}_dedup_extra",
            "title": "Extra questions (from secondary scan)",
            "author": None,
            "topic": "general",
            "type": "general_test",
            "questions": [q for _, q in unique_questions],
        }
        result["tests"].append(extra_test)

    total_secondary = sum(len(t["questions"]) for t in secondary_data["tests"])
    print(
        f"  Merge: {duplicates_found}/{total_secondary} secondary questions "
        f"matched, {len(unique_questions)} unique added"
    )

    return result


def main():
    project_root = Path(__file__).parent.parent
    parsed_dir = project_root / "parsed"
    output_dir = parsed_dir / "deduped"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build lookup: file stem -> group membership
    stem_to_group: dict[str, int] = {}
    for gi, group in enumerate(DUPLICATE_GROUPS):
        for stem in group:
            stem_to_group[stem] = gi

    # Collect all .json files (skip deduped/ subdirectory)
    json_files = sorted(
        f for f in parsed_dir.glob("*.json") if f.is_file()
    )

    if not json_files:
        print("No .json files found in parsed/")
        return

    print(f"Found {len(json_files)} file(s) in parsed/")

    # Track which groups we've already processed
    processed_groups: set[int] = set()
    # Track which files are part of a group (even if partner is missing)
    grouped_stems: set[str] = set()
    for group in DUPLICATE_GROUPS:
        for stem in group:
            grouped_stems.add(stem)

    for json_file in json_files:
        stem = json_file.stem
        group_idx = stem_to_group.get(stem)

        if group_idx is not None and group_idx not in processed_groups:
            # Process this duplicate group
            processed_groups.add(group_idx)
            group = DUPLICATE_GROUPS[group_idx]

            # Find which files in this group actually exist
            existing = []
            for g_stem in group:
                g_path = parsed_dir / f"{g_stem}.json"
                if g_path.exists():
                    existing.append((g_stem, g_path))

            if len(existing) < 2:
                # Only one file exists, copy it as-is
                stem_name, path = existing[0]
                print(f"Group {group}: only '{stem_name}' exists, copying as-is")
                data = json.loads(path.read_text(encoding="utf-8"))
                out_path = output_dir / f"{stem_name}.json"
                out_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                # Both files exist — determine primary by answer count
                files_data = []
                for g_stem, g_path in existing:
                    data = json.loads(g_path.read_text(encoding="utf-8"))
                    answered = count_answered(data)
                    total = sum(len(t["questions"]) for t in data["tests"])
                    files_data.append((g_stem, data, answered, total))
                    print(
                        f"  '{g_stem}': {total} questions, "
                        f"{answered} answered"
                    )

                # Sort: most answered first; on tie, first in group wins
                files_data.sort(key=lambda x: -x[2])
                primary_stem, primary_data, p_ans, p_total = files_data[0]
                secondary_stem, secondary_data, s_ans, s_total = files_data[1]

                print(
                    f"Group {group}:\n"
                    f"  Primary: '{primary_stem}' "
                    f"({p_ans}/{p_total} answered)\n"
                    f"  Secondary: '{secondary_stem}' "
                    f"({s_ans}/{s_total} answered)"
                )

                merged = merge_files(primary_data, secondary_data)

                # Use primary stem for output filename
                out_path = output_dir / f"{primary_stem}.json"
                out_path.write_text(
                    json.dumps(merged, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                merged_total = sum(
                    len(t["questions"]) for t in merged["tests"]
                )
                merged_answered = count_answered(merged)
                print(
                    f"  Output: '{out_path.name}' — "
                    f"{merged_total} questions, "
                    f"{merged_answered} answered"
                )

        elif group_idx is not None:
            # Already processed this group
            continue
        else:
            # Not part of any duplicate group — copy as-is
            print(f"Copying '{stem}' (no duplicates)")
            data = json.loads(json_file.read_text(encoding="utf-8"))
            out_path = output_dir / json_file.name
            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    print(f"\nDone. Output in {output_dir}/")


if __name__ == "__main__":
    main()
