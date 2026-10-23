"""Repeatable, non-AI vocabulary enrichment. Run from any working directory."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote

import build_lexicon as extract
import build_curriculum

ROOT = Path(__file__).resolve().parent.parent
KEYS = {"verbs": "infinitive", "nouns": "singular_indefinite", "adjectives": "base",
        "adverbs": "base", "common_phrases": "danish"}
REQUIRED = {"verbs": ("infinitive", "english", "past", "present_perfect", "past_perfect"),
            "nouns": ("gender", "singular_indefinite", "singular_definite", "plural_indefinite", "plural_definite", "english"),
            "adjectives": ("base", "neuter", "plural", "english"),
            "adverbs": ("base", "english"), "common_phrases": ("danish", "english")}
POS = {"verb": "verbs", "noun": "nouns", "adj": "adjectives", "adv": "adverbs",
       "phrase": "common_phrases", "prep_phrase": "common_phrases"}
SOURCES = {
    "wiktionary": {"name": "English Wiktionary, extracted by Kaikki/Wiktextract",
                   "url": "https://kaikki.org/dictionary/Danish/",
                   "license": "CC-BY-SA-4.0 (text; see Wiktionary terms)",
                   "terms": "https://en.wiktionary.org/wiki/Wiktionary:Copyrights"},
    "cor": {"name": "COR level 1, Danish Language Council",
            "url": extract.DEFAULT_COR_URL, "license": "Free and open for any use, per COR documentation",
            "terms": "https://ordregister.dk/doc/COR.html"},
}


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def marker(category, entry):
    text = entry.get(KEYS[category], "").strip().casefold()
    if category == "verbs":
        text = re.sub(r"^at\s+", "", text)
    if category == "nouns":
        text = re.sub(r"^(en|et)\s+", "", text)
    return text


def placeholder(category, entry):
    # Identical Danish/English words can be valid loanwords. Only the known
    # verb placeholder pattern ("at acceptere" in english) is repaired.
    return category == "verbs" and entry.get("english", "").strip().casefold() == entry.get("infinitive", "").strip().casefold()


def missing_fields(category, entry):
    return [f for f in REQUIRED[category] if not isinstance(entry.get(f), str)
            or entry[f].strip() in {"", "-", "—", "?"}]


def source_info(raw):
    word = raw["word"]
    return {"source": "wiktionary", "url": f"https://en.wiktionary.org/wiki/{quote(word, safe='')}#Danish",
            "sense_ids": [s["id"] for s in raw.get("senses", []) if s.get("id") and not s.get("form_of")],
            "review_status": "imported_unreviewed"}


def candidate(raw, cor):
    category = POS.get(raw.get("pos"))
    if not category or raw.get("lang_code") != "da" or not extract.choose_english(raw):
        return None
    word = raw.get("word", "").strip()
    if not word or any(c in word for c in "{}<>[]"):
        return None
    enriched_fields = []
    if category == "verbs":
        entry = extract.build_verb(raw)
        if entry:
            original = dict(entry)
            extract.enrich_verb_from_cor(entry, cor)
            enriched_fields = [f for f in entry if entry[f] and not original.get(f)]
    elif category == "nouns":
        entry = extract.build_noun(raw)
        if entry:
            # Never splice together paradigms of homographs: only use COR
            # if the lookup has a single paradigm for this lemma.
            original = dict(entry)
            extract.enrich_noun_from_cor(entry, cor)
            enriched_fields = [f for f in entry if entry[f] and not original.get(f)]
    elif category == "adjectives":
        entry = extract.build_adjective(raw)
        if entry:
            original = dict(entry)
            extract.enrich_adjective_from_cor(entry, cor)
            enriched_fields = [f for f in entry if entry[f] and not original.get(f)]
    else:
        entry = {KEYS[category]: word, "english": extract.choose_english(raw)}
        if category == "adverbs":
            if not extract.is_simple_headword(word):
                return None
            for field in ("comparative", "superlative"):
                value = extract.find_form(raw.get("forms", []), {field})
                if value:
                    entry[field] = value
    if not entry:
        return None
    for sense in raw.get("senses", []):
        for example in sense.get("examples", []):
            if example.get("type") != "example" or example.get("ref"):
                continue
            da = example.get("text")
            en = example.get("english") or example.get("translation")
            if da and en and len(da) < 400 and len(en) < 500:
                entry["example_da"], entry["example_en"] = da, en
                break
        if entry.get("example_da"):
            break
    entry["provenance"] = source_info(raw)
    if enriched_fields:
        entry["provenance"]["cor_fields"] = enriched_fields
    return category, entry


def safe_cor(path):
    """Exclude ambiguous lemmas before using the legacy lemma-based helpers."""
    identities = {}
    with path.open(encoding="utf-8-sig") as fh:
        for line in fh:
            parts = line.rstrip().split("\t")
            if len(parts) >= 4:
                identities.setdefault(parts[1].casefold(), set()).add(parts[0].split(".")[1])
    return {k: v for k, v in extract.load_cor_lookup(path).items() if len(identities.get(k, [])) == 1}


def merge_entry(category, existing, incoming, changes, conflicts):
    """Preserve user edits, repair placeholders, and fill genuinely empty fields."""
    repaired = placeholder(category, existing)
    for field, value in incoming.items():
        if field == "provenance" or not value:
            continue
        if not existing.get(field) or (field == "english" and repaired):
            existing[field] = value
            changes[field] += 1
        elif field not in {KEYS[category], "example_da", "example_en"} and existing[field] != value:
            conflicts.append({"category": category, "word": marker(category, existing), "field": field,
                              "kept": existing[field], "imported": value, "source": incoming["provenance"]["url"]})
    if "provenance" not in existing:
        existing["provenance"] = {**incoming["provenance"], "review_status": "existing_with_imported_enrichment"}


def build(source, cor_file, data_dir, limit=0):
    cor = safe_cor(cor_file) if cor_file else {}
    before = {c: read_json(data_dir / f"{c}.json", []) for c in KEYS}
    output = {c: [] for c in KEYS}
    indexes = {c: {} for c in KEYS}
    changes, excluded = Counter(), Counter()
    pending, conflicts = [], []
    # Preserve quarantined original records across repeated builds. Recheck
    # them against refreshed sources so a newly supplied translation can repair them.
    previous_pending = read_json(data_dir / "review" / "pending.json", [])
    seeds = {c: list(entries) for c, entries in before.items()}
    for item in previous_pending:
        if item.get("reason") in {"unresolved_translation_placeholder", "incomplete_existing"}:
            seeds[item["category"]].append(item["entry"])
    for c, entries in seeds.items():
        for entry in entries:
            key = marker(c, entry)
            if not key or key in indexes[c]:
                excluded["existing_duplicate_or_empty"] += 1
                pending.append({"category": c, "reason": "existing_duplicate_or_empty", "entry": entry})
                continue
            indexes[c][key] = entry
            output[c].append(entry)
    imported = {c: {} for c in KEYS}
    with source.open(encoding="utf-8-sig") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid source JSON at line {number}") from exc
            built = candidate(raw, cor)
            if not built:
                excluded["unsupported_or_filtered"] += 1
                continue
            c, entry = built
            key = marker(c, entry)
            # Prefer the most complete paradigm; source order breaks ties.
            score = sum(bool(entry.get(f)) for f in REQUIRED[c])
            previous = imported[c].get(key)
            if previous is None or score > sum(bool(previous.get(f)) for f in REQUIRED[c]):
                imported[c][key] = entry
    for c, entries in imported.items():
        added = 0
        for key, entry in sorted(entries.items()):
            missing = missing_fields(c, entry)
            if key in indexes[c]:
                merge_entry(c, indexes[c][key], entry, changes, conflicts)
            elif missing:
                pending.append({"category": c, "reason": "missing_fields", "missing": missing, "entry": entry})
            elif not limit or added < limit:
                output[c].append(entry)
                indexes[c][key] = entry
                added += 1
    # Keep unresolved placeholders out of quizzes; retain every record in review.
    for c in KEYS:
        retained = []
        for entry in output[c]:
            if placeholder(c, entry):
                pending.append({"category": c, "reason": "unresolved_translation_placeholder", "entry": entry})
            elif missing_fields(c, entry):
                pending.append({"category": c, "reason": "incomplete_existing",
                                "missing": missing_fields(c, entry), "entry": entry})
            else:
                retained.append(entry)
        output[c] = retained
    manifest = {name: {**SOURCES[name], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "cache_file": path.name}
                for name, path in [("wiktionary", source), *(([("cor", cor_file)]) if cor_file else [])]}
    report = {"sources": manifest, "before": {c: len(v) for c, v in before.items()},
              "after": {c: len(v) for c, v in output.items()}, "filled_fields": dict(changes),
              "review_count": len(pending), "conflict_count": len(conflicts), "excluded": dict(excluded),
              "notes": ["Imported entries are not human-reviewed or CEFR-graded.",
                        "Existing nonempty fields are preserved; disagreements are recorded in review/conflicts.json.",
                        "Missing inflections and unknown perfect auxiliaries are not guessed."]}
    return output, report, pending, conflicts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--source-file", type=Path, help="Local Kaikki Danish JSONL; otherwise cached/downloaded.")
    parser.add_argument("--cor-file", type=Path, help="Local COR level-1 TSV; otherwise cached/downloaded.")
    parser.add_argument("--source-url", default=extract.DEFAULT_KAIKKI_URL)
    parser.add_argument("--cor-url", default=extract.DEFAULT_COR_URL)
    parser.add_argument("--frequency-url", default="https://korpus.dsl.dk/download/freq-lemma.zip")
    parser.add_argument("--frequency-file", type=Path, help="Local DSL frequency-list zip or text file.")
    parser.add_argument("--phrases", type=Path, default=ROOT / "data" / "curated_phrases.json")
    parser.add_argument("--curriculum-overrides", type=Path, default=ROOT / "data" / "curriculum_overrides.json")
    parser.add_argument("--refresh", action="store_true", help="Download fresh source files instead of using cache.")
    parser.add_argument("--offline", action="store_true", help="Never download; fail if source files are missing.")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing database files.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum additions per category; 0 means all eligible entries.")
    args = parser.parse_args()
    if args.limit < 0 or (args.offline and args.refresh):
        parser.error("Use a nonnegative limit; --offline and --refresh are mutually exclusive.")
    paths = []
    for supplied, filename, url in [(args.source_file, "kaikki.jsonl", args.source_url),
                                    (args.cor_file, "cor.tsv", args.cor_url),
                                    (args.frequency_file, "freq-lemma.zip", args.frequency_url)]:
        path = supplied or args.data_dir / "cache" / filename
        if not path.exists() or (args.refresh and supplied is None):
            if args.offline or supplied is not None:
                parser.error(f"Source file not found: {path}")
            temporary = path.with_suffix(path.suffix + ".download")
            extract.download_file(url, temporary)
            temporary.replace(path)
        paths.append(path)
    output, report, pending, conflicts = build(*paths[:2], args.data_dir, args.limit)
    curriculum_report = build_curriculum.apply_curriculum(
        output, paths[2], args.phrases, args.curriculum_overrides
    )
    # Imported dictionary phrases are deliberately replaced by the reviewed
    # situational collection, so their rejected candidates are not review work.
    pending = [item for item in pending if item.get("category") != "common_phrases"]
    conflicts = [item for item in conflicts if item.get("category") != "common_phrases"]
    report["after"] = {category: len(entries) for category, entries in output.items()}
    report["review_count"] = len(pending)
    report["conflict_count"] = len(conflicts)
    report["curriculum"] = curriculum_report
    # Record actual download URLs, including command-line overrides.
    report["sources"]["wiktionary"]["download_url"] = args.source_url
    report["sources"]["cor"]["download_url"] = args.cor_url
    if not args.dry_run:
        for c, entries in output.items():
            extract.write_json(args.data_dir / f"{c}.json", entries)
        extract.write_json(args.data_dir / "lexicon.json", output)
        content = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
        (args.data_dir / "lexicon.browser.js").write_text(
            "// Generated from split vocabulary. Run code/enrich_lexicon.py to refresh.\nwindow.DANISH_LEXICON = " + content + ";\n", encoding="utf-8")
        extract.write_json(args.data_dir / "enrichment-report.json", report)
        extract.write_json(args.data_dir / "curriculum-report.json", curriculum_report)
        extract.write_json(args.data_dir / "review" / "pending.json", pending)
        extract.write_json(args.data_dir / "review" / "conflicts.json", conflicts)
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
