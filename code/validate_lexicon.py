from __future__ import annotations

import argparse
import json
from pathlib import Path


CATEGORY_FILES = {
    "verbs": "verbs.json",
    "nouns": "nouns.json",
    "adjectives": "adjectives.json",
    "adverbs": "adverbs.json",
    "common_phrases": "common_phrases.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate lexicon schema and print coverage counts.")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("data") / "lexicon.json",
        help="Fallback combined lexicon JSON path.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory with split category files.",
    )
    return parser.parse_args()


def required_fields() -> dict[str, list[str]]:
    return {
        "verbs": ["infinitive", "english", "imperative", "past", "present_perfect", "past_perfect"],
        "nouns": [
            "singular_indefinite",
            "singular_definite",
            "plural_indefinite",
            "plural_definite",
            "english",
        ],
        "adjectives": ["base", "common", "neuter", "plural", "comparative", "superlative", "english"],
        "adverbs": ["base", "english"],
        "common_phrases": ["danish", "english"],
    }


def noun_has_gender(entry: dict[str, str]) -> bool:
    gender = str(entry.get("gender", "")).strip().lower()
    if gender in {"en", "et"}:
        return True

    singular_indefinite = str(entry.get("singular_indefinite", "")).strip().lower()
    return singular_indefinite.startswith("en ") or singular_indefinite.startswith("et ")


def load_payload(data_dir: Path, fallback_file: Path) -> dict[str, list[dict[str, str]]]:
    payload: dict[str, list[dict[str, str]]] = {category: [] for category in CATEGORY_FILES}

    for category, filename in CATEGORY_FILES.items():
        category_path = data_dir / filename
        if not category_path.exists():
            continue

        content = json.loads(category_path.read_text(encoding="utf-8"))
        if isinstance(content, list):
            payload[category] = content
        elif isinstance(content, dict):
            payload[category] = content.get(category, [])

    has_split_data = any(payload[category] for category in CATEGORY_FILES)
    if has_split_data:
        return payload

    merged = json.loads(fallback_file.read_text(encoding="utf-8"))
    for category in CATEGORY_FILES:
        payload[category] = merged.get(category, [])
    return payload


def main() -> int:
    args = parse_args()
    payload = load_payload(args.data_dir, args.file)

    rules = required_fields()
    total_errors = 0
    for bucket, fields in rules.items():
      entries = payload.get(bucket, [])
      print(f"{bucket}: {len(entries)}")
      for index, entry in enumerate(entries, start=1):
        missing = [field for field in fields if not str(entry.get(field, "")).strip()]
                if bucket == "nouns" and not noun_has_gender(entry):
                    missing.append("gender (or en/et in singular_indefinite)")
        if missing:
          total_errors += 1
          print(f"  - {bucket}[{index}] missing: {', '.join(missing)}")

    if total_errors:
      print(f"Validation finished with {total_errors} issue(s).")
      return 1

    print("Validation passed with no schema issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())