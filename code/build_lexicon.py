from __future__ import annotations

import argparse
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_URL = "https://kaikki.org/dictionary/Danish/kaikki.org-dictionary-Danish.jsonl"


@dataclass
class BuildTargets:
    verbs: int
    adjectives: int
    nouns: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a larger Danish lexicon automatically from Kaikki/Wiktextract JSONL data."
    )
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL, help="Remote JSONL source URL.")
    parser.add_argument(
        "--source-file",
        type=Path,
        default=None,
        help="Optional local JSONL file. If set, no download is performed.",
    )
    parser.add_argument("--verbs", type=int, default=220, help="Target number of verbs.")
    parser.add_argument("--adjectives", type=int, default=220, help="Target number of adjectives.")
    parser.add_argument("--nouns", type=int, default=450, help="Target number of nouns.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data") / "lexicon.generated.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--merged-output",
        type=Path,
        default=Path("data") / "lexicon.json",
        help="Merged output path (existing data + generated data).",
    )
    return parser.parse_args()


def download_source(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destination)
    return destination


def clean_gloss(text: str) -> str:
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ;,.-")
    if ";" in text:
        text = text.split(";", 1)[0].strip()
    if "," in text:
        text = text.split(",", 1)[0].strip()
    return text


def choose_english(entry: dict[str, Any]) -> str | None:
    senses = entry.get("senses") or []
    candidates: list[str] = []
    for sense in senses:
        for key in ("glosses", "raw_glosses"):
            for gloss in sense.get(key, []) or []:
                cleaned = clean_gloss(str(gloss))
                if cleaned and not cleaned.lower().startswith("inflection of"):
                    candidates.append(cleaned)
    if not candidates:
        return None
    best = min(candidates, key=lambda c: len(c))
    return best


def is_simple_headword(word: str) -> bool:
    if not word:
        return False
    if len(word) < 2:
        return False
    if any(char.isdigit() for char in word):
        return False
    if " " in word:
        return False
    if any(ch in word for ch in "[]{}<>"):
        return False
    return True


def find_form(forms: list[dict[str, Any]], required_tags: set[str], forbidden_tags: set[str] | None = None) -> str | None:
    forbidden_tags = forbidden_tags or set()
    for form in forms:
        tags = {str(tag).lower() for tag in form.get("tags", [])}
        if required_tags.issubset(tags) and tags.isdisjoint(forbidden_tags):
            candidate = str(form.get("form", "")).strip()
            if candidate:
                return candidate
    return None


def detect_gender(entry: dict[str, Any], forms: list[dict[str, Any]]) -> str | None:
    for container in (entry.get("tags", []), entry.get("head_templates", [])):
        if isinstance(container, list):
            for item in container:
                item_text = str(item).lower()
                if item_text in {"en", "common-gender", "common"}:
                    return "en"
                if item_text in {"et", "neuter"}:
                    return "et"

    for form in forms:
        tags = {str(tag).lower() for tag in form.get("tags", [])}
        if "common-gender" in tags or "common" in tags:
            return "en"
        if "neuter" in tags:
            return "et"
    return None


def build_verb(entry: dict[str, Any]) -> dict[str, str] | None:
    word = str(entry.get("word", "")).strip()
    if not is_simple_headword(word):
        return None

    forms = entry.get("forms") or []
    english = choose_english(entry)
    imperative = find_form(forms, {"imperative"})
    past = find_form(forms, {"past"}, forbidden_tags={"participle"})
    supine = find_form(forms, {"supine"})
    if not supine:
        supine = find_form(forms, {"past", "participle"})

    if not all([english, imperative, past, supine]):
        return None

    infinitive = word if word.startswith("at ") else f"at {word}"
    return {
        "infinitive": infinitive,
        "english": english,
        "imperative": imperative,
        "past": past,
        "present_perfect": f"har {supine}",
        "past_perfect": f"havde {supine}",
    }


def build_adjective(entry: dict[str, Any]) -> dict[str, str] | None:
    word = str(entry.get("word", "")).strip()
    if not is_simple_headword(word):
        return None

    forms = entry.get("forms") or []
    english = choose_english(entry)
    neuter = find_form(forms, {"neuter"})
    plural = find_form(forms, {"plural"})
    comparative = find_form(forms, {"comparative"})
    superlative = find_form(forms, {"superlative"})

    if not all([english, neuter, plural, comparative, superlative]):
        return None

    return {
        "base": word,
        "common": word,
        "neuter": neuter,
        "plural": plural,
        "definite": plural,
        "comparative": comparative,
        "superlative": superlative,
        "english": english,
    }


def build_noun(entry: dict[str, Any]) -> dict[str, str] | None:
    word = str(entry.get("word", "")).strip()
    if not is_simple_headword(word):
        return None

    forms = entry.get("forms") or []
    english = choose_english(entry)
    gender = detect_gender(entry, forms)
    singular_definite = find_form(forms, {"definite", "singular"})
    plural_indefinite = find_form(forms, {"plural"}, forbidden_tags={"definite"})
    plural_definite = find_form(forms, {"definite", "plural"})

    if not all([english, gender, singular_definite, plural_indefinite, plural_definite]):
        return None

    return {
        "gender": gender,
        "singular_indefinite": f"{gender} {word}",
        "singular_definite": singular_definite,
        "plural_indefinite": plural_indefinite,
        "plural_definite": plural_definite,
        "english": english,
    }


def merge_unique(existing: list[dict[str, str]], generated: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    output = existing.copy()
    seen = {str(item.get(key, "")).lower() for item in existing}
    for item in generated:
        marker = str(item.get(key, "")).lower()
        if marker and marker not in seen:
            output.append(item)
            seen.add(marker)
    return output


def read_existing_lexicon(path: Path) -> dict[str, list[dict[str, str]]]:
    if not path.exists():
        return {"verbs": [], "nouns": [], "adjectives": [], "adverbs": []}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    for bucket in ("verbs", "nouns", "adjectives", "adverbs"):
        data.setdefault(bucket, [])
    return data


def build_from_jsonl(jsonl_path: Path, targets: BuildTargets) -> dict[str, list[dict[str, str]]]:
    verbs: list[dict[str, str]] = []
    adjectives: list[dict[str, str]] = []
    nouns: list[dict[str, str]] = []

    seen_verbs: set[str] = set()
    seen_adjectives: set[str] = set()
    seen_nouns: set[str] = set()

    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if len(verbs) >= targets.verbs and len(adjectives) >= targets.adjectives and len(nouns) >= targets.nouns:
                break
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if str(entry.get("lang_code", "")).lower() != "da":
                continue

            pos = str(entry.get("pos", "")).lower()
            if pos == "verb" and len(verbs) < targets.verbs:
                built = build_verb(entry)
                if built:
                    marker = built["infinitive"].lower()
                    if marker not in seen_verbs:
                        verbs.append(built)
                        seen_verbs.add(marker)
            elif pos in {"adj", "adjective"} and len(adjectives) < targets.adjectives:
                built = build_adjective(entry)
                if built:
                    marker = built["base"].lower()
                    if marker not in seen_adjectives:
                        adjectives.append(built)
                        seen_adjectives.add(marker)
            elif pos == "noun" and len(nouns) < targets.nouns:
                built = build_noun(entry)
                if built:
                    marker = built["singular_indefinite"].lower()
                    if marker not in seen_nouns:
                        nouns.append(built)
                        seen_nouns.add(marker)

    return {
        "verbs": verbs,
        "adjectives": adjectives,
        "nouns": nouns,
        "adverbs": [],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    targets = BuildTargets(verbs=args.verbs, adjectives=args.adjectives, nouns=args.nouns)

    if args.source_file:
        source_path = args.source_file
    else:
        source_path = Path("data") / "cache" / "kaikki.org-dictionary-Danish.jsonl"
        print(f"Downloading source data from {args.source_url} ...")
        download_source(args.source_url, source_path)

    print("Building generated lexicon ...")
    generated = build_from_jsonl(source_path, targets)
    write_json(args.output, generated)

    existing = read_existing_lexicon(args.merged_output)
    merged = {
        "verbs": merge_unique(existing["verbs"], generated["verbs"], "infinitive"),
        "nouns": merge_unique(existing["nouns"], generated["nouns"], "singular_indefinite"),
        "adjectives": merge_unique(existing["adjectives"], generated["adjectives"], "base"),
        "adverbs": existing["adverbs"],
    }
    write_json(args.merged_output, merged)

    print("Done.")
    print(f"Generated verbs: {len(generated['verbs'])}")
    print(f"Generated adjectives: {len(generated['adjectives'])}")
    print(f"Generated nouns: {len(generated['nouns'])}")
    print(f"Wrote generated file: {args.output}")
    print(f"Wrote merged file: {args.merged_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())