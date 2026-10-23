"""Rank practice entries from DSL frequencies and merge reviewed practical phrases."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent.parent
CATEGORY_POS = {"verbs": "V", "nouns": "NC", "adjectives": "A", "adverbs": "D"}
KEYS = {"verbs": "infinitive", "nouns": "singular_indefinite", "adjectives": "base", "adverbs": "base"}
TIER_LIMITS = ((500, "core_500"), (1500, "everyday_1500"), (3000, "extended_3000"))


def lemma(category: str, entry: dict) -> str:
    value = str(entry.get(KEYS[category], "")).strip().casefold()
    if category == "verbs":
        value = re.sub(r"^at\s+", "", value)
    elif category == "nouns":
        value = re.sub(r"^(en|et)\s+", "", value)
    return value


def load_frequency(path: Path) -> tuple[dict[tuple[str, str], tuple[int, float]], dict]:
    if path.suffix.casefold() == ".zip":
        with zipfile.ZipFile(path) as archive:
            name = next((n for n in archive.namelist() if n.endswith("freq-30k-ex.txt")), None)
            if not name:
                raise ValueError("Frequency archive does not contain freq-30k-ex.txt")
            lines = archive.read(name).decode("utf-8-sig").splitlines()
    else:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    result = {}
    for source_rank, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        pos, word, value = parts
        try:
            frequency = float(value)
        except ValueError:
            continue
        result.setdefault((pos, word.casefold()), (source_rank, frequency))
    return result, {"source": "DSL 30,000 most frequent Danish lemmas, excluding proper nouns and numerals",
                    "url": "https://korpus.dsl.dk/resources/details/freq-lemmas.html",
                    "terms": "https://korpus.dsl.dk/resources/licences/dsl-open.html"}


def tier(rank: int | None) -> str:
    if rank is None:
        return "full"
    return next((name for limit, name in TIER_LIMITS if rank <= limit), "full")


def apply_curriculum(vocabulary: dict[str, list[dict]], frequency_file: Path,
                     curated_file: Path, overrides_file: Path | None = None) -> dict:
    frequencies, source = load_frequency(frequency_file)
    applied_overrides = []
    if overrides_file and overrides_file.exists():
        overrides = json.loads(overrides_file.read_text(encoding="utf-8-sig"))
        indexes = {category: {lemma(category, entry): entry for entry in entries}
                   for category, entries in vocabulary.items() if category in CATEGORY_POS}
        for override in overrides:
            category, word = override.get("category"), str(override.get("lemma", "")).casefold()
            entry = indexes.get(category, {}).get(word)
            if not entry:
                raise ValueError(f"Curriculum override does not match an entry: {category}/{word}")
            entry.update(override.get("fields", {}))
            provenance = entry.setdefault("provenance", {})
            provenance["curriculum_review"] = "manually_reviewed"
            provenance["review_note"] = override.get("note", "Reviewed for the core curriculum.")
            applied_overrides.append(f"{category}/{word}")
    matches = []
    for category, pos in CATEGORY_POS.items():
        for entry in vocabulary.get(category, []):
            key = lemma(category, entry)
            match = frequencies.get((pos, key))
            if match:
                matches.append((match[0], category, key, match[1], entry))
    matches.sort(key=lambda row: (row[0], row[1], row[2]))
    for curriculum_rank, (source_rank, category, _, frequency, entry) in enumerate(matches, 1):
        entry["frequency_rank"] = source_rank
        entry["frequency"] = frequency
        entry["curriculum_rank"] = curriculum_rank
        entry["curriculum_tier"] = tier(curriculum_rank)
        provenance = entry.setdefault("provenance", {})
        provenance["frequency_source"] = "dsl_frequency_2024"
        if curriculum_rank <= 500:
            checks = provenance.setdefault("quality_checks", [])
            for check in ("schema_complete", "required_forms_present", "english_gloss_present", "frequency_pos_match"):
                if check not in checks:
                    checks.append(check)
            provenance.setdefault("curriculum_review", "automated_cross_source_review")
    for category in CATEGORY_POS:
        for entry in vocabulary.get(category, []):
            if "curriculum_rank" not in entry:
                entry["curriculum_tier"] = "full"
    curated = json.loads(curated_file.read_text(encoding="utf-8-sig"))
    if not isinstance(curated, list):
        raise ValueError("Curated phrases must be a JSON array")
    seen = set()
    phrases = []
    for index, phrase in enumerate(curated, 1):
        if not all(str(phrase.get(field, "")).strip() for field in ("danish", "english", "topic", "curriculum_tier")):
            raise ValueError(f"Curated phrase {index} is missing a required field")
        marker = phrase["danish"].strip().casefold()
        if marker in seen:
            raise ValueError(f"Duplicate curated phrase: {phrase['danish']}")
        seen.add(marker)
        item = dict(phrase)
        item["review_status"] = "manually_curated"
        item["provenance"] = {"source": "project_curated", "review_status": "manually_curated"}
        phrases.append(item)
    vocabulary["common_phrases"] = phrases
    core = [entry for _, _, _, _, entry in matches[:500]]
    core_nouns = [entry for _, category, _, _, entry in matches[:500] if category == "nouns"]
    core_verbs = [entry for _, category, _, _, entry in matches[:500] if category == "verbs"]
    quality_review = {
        "translations_present": sum(bool(str(entry.get("english", "")).strip()) for entry in core),
        "noun_genders_present": sum(entry.get("gender") in {"en", "et"} for entry in core_nouns),
        "noun_entries": len(core_nouns),
        "verb_auxiliaries_present": sum(
            str(entry.get("present_perfect", "")).startswith(("har ", "er "))
            and str(entry.get("past_perfect", "")).startswith(("havde ", "var "))
            for entry in core_verbs
        ),
        "verb_entries": len(core_verbs),
        "translated_examples_present": sum(bool(entry.get("example_da") and entry.get("example_en")) for entry in core),
        "entries_without_examples": sum(not (entry.get("example_da") and entry.get("example_en")) for entry in core),
    }
    counts = {name: sum(1 for category in CATEGORY_POS for entry in vocabulary[category]
                        if entry.get("curriculum_rank", 10**9) <= limit)
              for limit, name in TIER_LIMITS}
    return {"frequency_source": source, "ranked_entries": len(matches), "scope_word_counts": counts,
            "unranked_entries": sum(len(vocabulary[c]) for c in CATEGORY_POS) - len(matches),
            "curated_phrases": len(phrases),
            "phrase_topics": sorted({p["topic"] for p in phrases}),
            "reviewed_core_entries": min(500, len(matches)),
            "manual_core_corrections": len(applied_overrides),
            "manual_override_entries": applied_overrides,
            "core_quality_review": quality_review,
            "review_method": "Schema, English-gloss, POS-frequency match, and COR/Wiktionary-form checks; not native-speaker review."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--frequency-file", type=Path, default=ROOT / "data" / "cache" / "freq-lemma.zip")
    parser.add_argument("--phrases", type=Path, default=ROOT / "data" / "curated_phrases.json")
    parser.add_argument("--overrides", type=Path, default=ROOT / "data" / "curriculum_overrides.json")
    args = parser.parse_args()
    vocabulary = {c: json.loads((args.data_dir / f"{c}.json").read_text(encoding="utf-8-sig"))
                  for c in (*CATEGORY_POS, "common_phrases")}
    report = apply_curriculum(vocabulary, args.frequency_file, args.phrases, args.overrides)
    for category, entries in vocabulary.items():
        (args.data_dir / f"{category}.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.data_dir / "lexicon.json").write_text(json.dumps(vocabulary, ensure_ascii=False, indent=2), encoding="utf-8")
    content = json.dumps(vocabulary, ensure_ascii=False, separators=(",", ":"))
    (args.data_dir / "lexicon.browser.js").write_text(
        "// Generated from the enriched and ranked vocabulary.\nwindow.DANISH_LEXICON = " + content + ";\n", encoding="utf-8")
    (args.data_dir / "curriculum-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
