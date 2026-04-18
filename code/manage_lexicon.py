from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CATEGORY_FILES = {
    "verbs": "verbs.json",
    "nouns": "nouns.json",
    "adjectives": "adjectives.json",
    "adverbs": "adverbs.json",
    "common_phrases": "common_phrases.json",
}

UNIQUE_KEYS = {
    "verbs": "infinitive",
    "nouns": "singular_indefinite",
    "adjectives": "base",
    "adverbs": "base",
    "common_phrases": "danish",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage split lexicon files: split, merge, and append category JSON uploads."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    split_parser = subparsers.add_parser("split", help="Split combined lexicon.json into category files.")
    split_parser.add_argument("--source", type=Path, default=Path("data") / "lexicon.json")
    split_parser.add_argument("--data-dir", type=Path, default=Path("data"))

    merge_parser = subparsers.add_parser("merge", help="Merge category files into one combined lexicon.json.")
    merge_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    merge_parser.add_argument("--output", type=Path, default=Path("data") / "lexicon.json")

    append_parser = subparsers.add_parser("append", help="Append uploaded category JSON into existing category file.")
    append_parser.add_argument("--category", choices=sorted(CATEGORY_FILES.keys()), required=True)
    append_parser.add_argument("--input", type=Path, required=True, help="Path to uploaded JSON file.")
    append_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    append_parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="If set, replace existing entry when duplicate unique key is found.",
    )

    return parser.parse_args()


def read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_category_payload(raw: Any, category: str) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    if isinstance(raw, dict):
        if isinstance(raw.get(category), list):
            return [item for item in raw[category] if isinstance(item, dict)]
        # Accept combined payload and extract only the requested category.
        if category in raw and isinstance(raw[category], list):
            return [item for item in raw[category] if isinstance(item, dict)]

    return []


def split_combined(source: Path, data_dir: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Combined lexicon file not found: {source}")

    combined = read_json_file(source)
    if not isinstance(combined, dict):
        raise ValueError("Combined lexicon must be a JSON object.")

    for category, filename in CATEGORY_FILES.items():
        entries = combined.get(category, [])
        if not isinstance(entries, list):
            entries = []
        write_json_file(data_dir / filename, entries)
        print(f"Wrote {len(entries)} entries -> {data_dir / filename}")


def merge_split(data_dir: Path, output: Path) -> None:
    combined: dict[str, list[dict[str, Any]]] = {}
    for category, filename in CATEGORY_FILES.items():
        path = data_dir / filename
        if not path.exists():
            combined[category] = []
            continue

        payload = read_json_file(path)
        combined[category] = normalize_category_payload(payload, category)

    write_json_file(output, combined)
    print(f"Wrote merged lexicon -> {output}")


def append_category(category: str, input_path: Path, data_dir: Path, allow_overwrite: bool) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input upload file not found: {input_path}")

    source_payload = read_json_file(input_path)
    incoming = normalize_category_payload(source_payload, category)
    if not incoming:
        raise ValueError(
            "Input JSON did not contain entries for the requested category. "
            f"Expected an array or an object with key '{category}'."
        )

    category_path = data_dir / CATEGORY_FILES[category]
    existing_raw: Any = []
    if category_path.exists():
        existing_raw = read_json_file(category_path)
    existing = normalize_category_payload(existing_raw, category)

    key = UNIQUE_KEYS[category]
    index_by_key = {
        str(entry.get(key, "")).strip().lower(): i
        for i, entry in enumerate(existing)
        if str(entry.get(key, "")).strip()
    }

    appended = 0
    replaced = 0
    skipped = 0

    for entry in incoming:
        marker = str(entry.get(key, "")).strip().lower()
        if not marker:
            skipped += 1
            continue

        if marker not in index_by_key:
            existing.append(entry)
            index_by_key[marker] = len(existing) - 1
            appended += 1
            continue

        if allow_overwrite:
            existing[index_by_key[marker]] = entry
            replaced += 1
        else:
            skipped += 1

    write_json_file(category_path, existing)
    print(f"Updated {category_path}")
    print(f"Appended: {appended}")
    print(f"Replaced: {replaced}")
    print(f"Skipped: {skipped}")


def main() -> int:
    args = parse_args()

    if args.command == "split":
        split_combined(args.source, args.data_dir)
        return 0

    if args.command == "merge":
        merge_split(args.data_dir, args.output)
        return 0

    if args.command == "append":
        append_category(args.category, args.input, args.data_dir, args.allow_overwrite)
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
