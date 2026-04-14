from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate lexicon schema and print coverage counts.")
    parser.add_argument("--file", type=Path, default=Path("data") / "lexicon.json", help="Lexicon JSON path.")
    return parser.parse_args()


def required_fields() -> dict[str, list[str]]:
    return {
        "verbs": ["infinitive", "english", "imperative", "past", "present_perfect", "past_perfect"],
        "nouns": [
            "gender",
            "singular_indefinite",
            "singular_definite",
            "plural_indefinite",
            "plural_definite",
            "english",
        ],
        "adjectives": ["base", "common", "neuter", "plural", "comparative", "superlative", "english"],
        "adverbs": ["base", "english"],
    }


def main() -> int:
    args = parse_args()
    payload = json.loads(args.file.read_text(encoding="utf-8"))

    rules = required_fields()
    total_errors = 0
    for bucket, fields in rules.items():
      entries = payload.get(bucket, [])
      print(f"{bucket}: {len(entries)}")
      for index, entry in enumerate(entries, start=1):
        missing = [field for field in fields if not str(entry.get(field, "")).strip()]
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