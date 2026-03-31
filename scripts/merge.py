"""Merge all deduplicated JSON files into the final output.

Reads parsed/deduped/*.json, combines into output/grile.json with metadata.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


COMPLEMENT_GRUPAT_RULES = {
    "A": "1,2,3 correct",
    "B": "1,3 correct",
    "C": "2,4 correct",
    "D": "only 4 correct",
    "E": "all correct or all false",
}


def count_questions(source: dict) -> int:
    """Count total questions across all tests in a source."""
    return sum(len(t["questions"]) for t in source["tests"])


def main():
    project_root = Path(__file__).parent.parent
    deduped_dir = project_root / "parsed" / "deduped"
    output_dir = project_root / "output"
    output_file = output_dir / "grile.json"

    if not deduped_dir.exists():
        print(f"ERROR: {deduped_dir} does not exist")
        return

    json_files = sorted(deduped_dir.glob("*.json"))
    if not json_files:
        print(f"ERROR: no .json files found in {deduped_dir}")
        return

    # Load all sources
    sources = []
    for path in json_files:
        with open(path, encoding="utf-8") as f:
            sources.append(json.load(f))

    # Sort by year
    sources.sort(key=lambda s: s.get("year", 0))

    # Count questions per source and total
    total_questions = 0
    for source in sources:
        q = count_questions(source)
        total_questions += q
        print(f"  {source['file']}.json: {q} questions")

    # Build output
    output = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "metadata": {
            "complement_grupat_rules": COMPLEMENT_GRUPAT_RULES,
            "total_questions": total_questions,
            "total_sources": len(sources),
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(
        f"Done. {total_questions} questions from {len(sources)} sources "
        f"-> {output_file.relative_to(project_root)}"
    )


if __name__ == "__main__":
    main()
