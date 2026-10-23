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
        "verbs": ["infinitive", "english", "past", "present_perfect", "past_perfect"],
        "nouns": [
            "singular_indefinite",
            "singular_definite",
            "plural_indefinite",
            "plural_definite",
            "english",
        ],
        "adjectives": ["base", "neuter", "plural", "english"],
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

        content = json.loads(category_path.read_text(encoding="utf-8-sig"))
        if isinstance(content, list):
            payload[category] = content
        elif isinstance(content, dict):
            payload[category] = content.get(category, [])

    has_split_data = any(payload[category] for category in CATEGORY_FILES)
    if has_split_data:
        return payload

    merged = json.loads(fallback_file.read_text(encoding="utf-8-sig"))
    for category in CATEGORY_FILES:
        payload[category] = merged.get(category, [])
    return payload


def main() -> int:
    args = parse_args()
    payload = load_payload(args.data_dir, args.file)

    rules = required_fields()
    total_errors = 0
    keys = {"verbs": "infinitive", "nouns": "singular_indefinite",
            "adjectives": "base", "adverbs": "base", "common_phrases": "danish"}
    for bucket, fields in rules.items():
        entries = payload.get(bucket, [])
        print(f"{bucket}: {len(entries)}")
        seen = set()
        for index, entry in enumerate(entries, start=1):
            issues = [field for field in fields if not isinstance(entry.get(field), str) or not entry[field].strip()]
            if bucket == "nouns" and not noun_has_gender(entry):
                issues.append("gender (or en/et in singular_indefinite)")
            key = str(entry.get(keys[bucket], "")).strip().casefold()
            if key in seen:
                issues.append("duplicate headword")
            seen.add(key)
            if bucket == "verbs" and key == str(entry.get("english", "")).strip().casefold():
                issues.append("untranslated infinitive placeholder")
            if issues:
                total_errors += 1
                print(f"  - {bucket}[{index}] invalid: {', '.join(issues)}")

    if total_errors:
        print(f"Validation finished with {total_errors} issue(s).")
        return 1

    ranked = []
    for bucket in ("verbs", "nouns", "adjectives", "adverbs"):
        for entry in payload[bucket]:
            if "curriculum_rank" in entry:
                ranked.append((int(entry["curriculum_rank"]), entry))
    if ranked:
        ranks = sorted(rank for rank, _ in ranked)
        if ranks != list(range(1, len(ranks) + 1)):
            print("Validation failed: curriculum ranks must be unique and contiguous.")
            return 1
        limits = ((500, "core_500"), (1500, "everyday_1500"), (3000, "extended_3000"))
        for rank, entry in ranked:
            expected = next((name for limit, name in limits if rank <= limit), "full")
            if entry.get("curriculum_tier") != expected:
                print(f"Validation failed: curriculum rank {rank} has the wrong tier.")
                return 1
        print("curriculum scopes: " + ", ".join(
            f"{name}={sum(rank <= limit for rank, _ in ranked)}" for limit, name in limits
        ))
    for index, phrase in enumerate(payload["common_phrases"], 1):
        if not str(phrase.get("topic", "")).strip() or phrase.get("curriculum_tier") not in {
            "core_500", "everyday_1500", "extended_3000", "full"
        }:
            print(f"Validation failed: common_phrases[{index}] lacks a valid topic or curriculum tier.")
            return 1

    print("Validation passed with no schema issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
