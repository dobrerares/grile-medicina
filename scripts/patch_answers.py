"""Apply answer patches to parsed JSON files.

Reads patch definitions from patches/ directory and applies them to parsed/ JSONs.
Each patch file is a JSON with structure:
{
    "target": "Biologie 2009 UMFCD.json",
    "patches": [
        {"test_title": "TEST 3", "question_number": 1, "correct_answer": "E"},
        ...
    ]
}
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSED_DIR = ROOT / "parsed"
PATCHES_DIR = ROOT / "patches"


def apply_patches():
    if not PATCHES_DIR.exists():
        print("No patches/ directory found")
        return

    total_applied = 0
    total_skipped = 0

    for patch_file in sorted(PATCHES_DIR.glob("*.json")):
        with open(patch_file) as f:
            patch_data = json.load(f)

        target = patch_data["target"]
        target_path = PARSED_DIR / target

        if not target_path.exists():
            print(f"SKIP: Target file {target} not found")
            continue

        with open(target_path) as f:
            data = json.load(f)

        applied = 0
        skipped = 0

        for p in patch_data["patches"]:
            test_title = p["test_title"]
            q_num = p["question_number"]
            answer = p["correct_answer"]

            # Find matching test
            matched = False
            for test in data["tests"]:
                if test["title"] != test_title:
                    continue
                force = p.get("force", False)
                for q in test["questions"]:
                    if q["number"] == q_num and (force or not q.get("correct_answer")):
                        q["correct_answer"] = answer
                        applied += 1
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                skipped += 1

        if applied > 0:
            with open(target_path, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"{patch_file.name}: applied {applied}, skipped {skipped} → {target}")
        total_applied += applied
        total_skipped += skipped

    print(f"\nTotal: applied {total_applied}, skipped {total_skipped}")


if __name__ == "__main__":
    apply_patches()
