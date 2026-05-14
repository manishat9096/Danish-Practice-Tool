from __future__ import annotations

import argparse
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_KAIKKI_URL = "https://kaikki.org/dictionary/Danish/kaikki.org-dictionary-Danish.jsonl"
DEFAULT_COR_URL = "https://ordregister.dk/files/cor1.5.1.0.tsv"

# COR grammatical form labels that map to our vocabulary fields.
# Verbs: vb.imp → imperative, vb.præt.akt → past, vb.perf.part → supine
#        (supine is used to construct present_perfect / past_perfect)
# Nouns: fk = fælleskøn (common/"en"), itk = intetkøn (neuter/"et")
# Adjectives: adj.kompar → comparative, adj.superl.sg.ubest → superlative


@dataclass
class BuildTargets:
    verbs: int
    adjectives: int
    nouns: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Danish lexicon from Kaikki/Wiktextract JSONL, optionally enriched with COR."
    )
    # Kaikki options
    parser.add_argument("--source-url", default=DEFAULT_KAIKKI_URL, help="Remote Kaikki JSONL URL.")
    parser.add_argument("--source-file", type=Path, default=None, help="Local JSONL file (skips download).")
    parser.add_argument("--verbs", type=int, default=220, help="Target verb count.")
    parser.add_argument("--adjectives", type=int, default=220, help="Target adjective count.")
    parser.add_argument("--nouns", type=int, default=450, help="Target noun count.")
    parser.add_argument("--output", type=Path, default=Path("data") / "lexicon.generated.json")
    parser.add_argument("--merged-output", type=Path, default=Path("data") / "lexicon.json")
    # COR options
    parser.add_argument("--use-cor", action="store_true",
                        help="Download COR and use it to fill missing forms during Kaikki build.")
    parser.add_argument("--cor-url", default=DEFAULT_COR_URL, help="COR TSV download URL.")
    parser.add_argument("--cor-file", type=Path, default=None, help="Local COR TSV (skips download).")
    # Enrich-only mode
    parser.add_argument("--enrich-only", action="store_true",
                        help="Skip Kaikki; enrich existing split data files in --data-dir with COR.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"),
                        help="Directory containing verbs.json / nouns.json / adjectives.json.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, destination)
    print(f"  Saved to {destination}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def merge_unique(existing: list[dict], generated: list[dict], key: str) -> list[dict]:
    output = existing.copy()
    seen = {str(item.get(key, "")).lower() for item in existing}
    for item in generated:
        marker = str(item.get(key, "")).lower()
        if marker and marker not in seen:
            output.append(item)
            seen.add(marker)
    return output


def read_existing_lexicon(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {"verbs": [], "nouns": [], "adjectives": [], "adverbs": []}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    for bucket in ("verbs", "nouns", "adjectives", "adverbs"):
        data.setdefault(bucket, [])
    return data


# ---------------------------------------------------------------------------
# COR loading
# ---------------------------------------------------------------------------

def load_cor_lookup(cor_path: Path) -> dict[str, dict[str, str]]:
    """Parse the COR TSV into {lemma_lower: {gform_label: inflected_form}}.

    COR TSV columns: COR-id | lemma | [glosse] | grammatical_designation | form | [normering]
    The glosse column is absent for most entries; we detect the gform by looking
    for the first field after the lemma that contains a dot (e.g. "vb.præt.akt").
    Only the first (best-normalised) form per lemma+gform pair is kept.
    """
    lookup: dict[str, dict[str, str]] = {}
    with cor_path.open("r", encoding="utf-8-sig") as fh:
        for raw in fh:
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            lemma = parts[1].strip().lower()
            if not lemma:
                continue
            # Locate gform: first field after lemma (index ≥ 2) that contains "."
            gform = form = None
            for i in range(2, min(len(parts), 5)):
                if "." in parts[i]:
                    gform = parts[i].strip()
                    form = parts[i + 1].strip() if i + 1 < len(parts) else ""
                    break
            if gform and form:
                lookup.setdefault(lemma, {}).setdefault(gform, form)
    return lookup


# ---------------------------------------------------------------------------
# COR enrichment
# ---------------------------------------------------------------------------

def enrich_verb_from_cor(entry: dict, cor: dict[str, dict[str, str]]) -> dict:
    lemma = re.sub(r"^at\s+", "", entry.get("infinitive", ""), flags=re.IGNORECASE).strip().lower()
    forms = cor.get(lemma, {})
    if not entry.get("imperative"):
        entry["imperative"] = forms.get("vb.imp", "")
    if not entry.get("past"):
        entry["past"] = forms.get("vb.præt.akt", "")
    supine = forms.get("vb.perf.part", "")
    if supine:
        if not entry.get("present_perfect"):
            entry["present_perfect"] = f"har {supine}"
        if not entry.get("past_perfect"):
            entry["past_perfect"] = f"havde {supine}"
    return entry


def enrich_noun_from_cor(entry: dict, cor: dict[str, dict[str, str]]) -> dict:
    sg_indef = entry.get("singular_indefinite", "")
    lemma = re.sub(r"^(en|et)\s+", "", sg_indef, flags=re.IGNORECASE).strip().lower()
    if not lemma:
        return entry
    forms = cor.get(lemma, {})
    # Detect or confirm gender from COR when not set
    gender = entry.get("gender") or (
        "en" if any(k.startswith("sb.fk.") for k in forms) else
        "et" if any(k.startswith("sb.itk.") for k in forms) else None
    )
    if not gender:
        return entry
    entry["gender"] = gender
    gk = "fk" if gender == "en" else "itk"
    prefix = gender  # "en" or "et"
    field_map = {
        f"sb.{gk}.sg.ubest": ("singular_indefinite", f"{prefix} {{}}"),
        f"sb.{gk}.sg.best":  ("singular_definite",   "{}"),
        f"sb.{gk}.pl.ubest": ("plural_indefinite",   "{}"),
        f"sb.{gk}.pl.best":  ("plural_definite",     "{}"),
    }
    for gform, (field, tmpl) in field_map.items():
        if not entry.get(field) and gform in forms:
            entry[field] = tmpl.format(forms[gform])
    return entry


def enrich_adjective_from_cor(entry: dict, cor: dict[str, dict[str, str]]) -> dict:
    lemma = entry.get("base", "").lower()
    forms = cor.get(lemma, {})
    if not entry.get("neuter"):
        entry["neuter"] = forms.get("adj.sg.ubest.itk", "")
    if not entry.get("plural"):
        entry["plural"] = forms.get("adj.pl") or forms.get("adj.sg.best", "")
    if not entry.get("definite"):
        entry["definite"] = forms.get("adj.sg.best", "")
    if not entry.get("comparative"):
        entry["comparative"] = forms.get("adj.kompar", "")
    if not entry.get("superlative"):
        entry["superlative"] = forms.get("adj.superl.sg.ubest", "")
    return entry


# ---------------------------------------------------------------------------
# Completeness checks (mirror REQUIRED_CATEGORY_FIELDS in the HTML app)
# ---------------------------------------------------------------------------

def is_complete_verb(e: dict) -> bool:
    return all(e.get(f) for f in ("infinitive", "english", "past", "present_perfect", "past_perfect"))


def is_complete_noun(e: dict) -> bool:
    return all(e.get(f) for f in (
        "gender", "singular_indefinite", "singular_definite",
        "plural_indefinite", "plural_definite", "english",
    ))


def is_complete_adjective(e: dict) -> bool:
    return all(e.get(f) for f in ("base", "neuter", "plural", "english"))


# ---------------------------------------------------------------------------
# Kaikki / Wiktextract extraction
# ---------------------------------------------------------------------------

def clean_gloss(text: str) -> str:
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ;,.-")
    if ";" in text:
        text = text.split(";", 1)[0].strip()
    if "," in text:
        text = text.split(",", 1)[0].strip()
    return text


def choose_english(entry: dict[str, Any]) -> str | None:
    candidates: list[str] = []
    for sense in entry.get("senses") or []:
        for key in ("glosses", "raw_glosses"):
            for gloss in sense.get(key, []) or []:
                cleaned = clean_gloss(str(gloss))
                if cleaned and not cleaned.lower().startswith("inflection of"):
                    candidates.append(cleaned)
    return min(candidates, key=len) if candidates else None


def is_simple_headword(word: str) -> bool:
    return (
        bool(word)
        and len(word) >= 2
        and not any(c.isdigit() for c in word)
        and " " not in word
        and not any(ch in word for ch in "[]{}<>")
    )


def find_form(
    forms: list[dict[str, Any]],
    required_tags: set[str],
    forbidden_tags: set[str] | None = None,
) -> str | None:
    forbidden_tags = forbidden_tags or set()
    for form in forms:
        tags = {str(t).lower() for t in form.get("tags", [])}
        if required_tags.issubset(tags) and tags.isdisjoint(forbidden_tags):
            candidate = str(form.get("form", "")).strip()
            if candidate:
                return candidate
    return None


def detect_gender(entry: dict[str, Any], forms: list[dict[str, Any]]) -> str | None:
    for container in (entry.get("tags", []), entry.get("head_templates", [])):
        if isinstance(container, list):
            for item in container:
                s = str(item).lower()
                if s in {"en", "common-gender", "common"}:
                    return "en"
                if s in {"et", "neuter"}:
                    return "et"
    for form in forms:
        tags = {str(t).lower() for t in form.get("tags", [])}
        if "common-gender" in tags or "common" in tags:
            return "en"
        if "neuter" in tags:
            return "et"
    return None


def build_verb(entry: dict[str, Any]) -> dict[str, str] | None:
    word = str(entry.get("word", "")).strip()
    if not is_simple_headword(word):
        return None
    english = choose_english(entry)
    if not english:
        return None
    forms = entry.get("forms") or []
    imperative = find_form(forms, {"imperative"})
    past = find_form(forms, {"past"}, forbidden_tags={"participle"})
    supine = find_form(forms, {"supine"}) or find_form(forms, {"past", "participle"})
    infinitive = word if word.startswith("at ") else f"at {word}"
    return {
        "infinitive": infinitive,
        "english": english,
        "imperative": imperative or "",
        "past": past or "",
        "present_perfect": f"har {supine}" if supine else "",
        "past_perfect": f"havde {supine}" if supine else "",
    }


def build_adjective(entry: dict[str, Any]) -> dict[str, str] | None:
    word = str(entry.get("word", "")).strip()
    if not is_simple_headword(word):
        return None
    english = choose_english(entry)
    if not english:
        return None
    forms = entry.get("forms") or []
    neuter = find_form(forms, {"neuter"})
    plural = find_form(forms, {"plural"})
    comparative = find_form(forms, {"comparative"})
    superlative = find_form(forms, {"superlative"})
    return {
        "base": word,
        "common": word,
        "neuter": neuter or "",
        "plural": plural or "",
        "definite": plural or "",
        "comparative": comparative or "",
        "superlative": superlative or "",
        "english": english,
    }


def build_noun(entry: dict[str, Any]) -> dict[str, str] | None:
    word = str(entry.get("word", "")).strip()
    if not is_simple_headword(word):
        return None
    english = choose_english(entry)
    if not english:
        return None
    forms = entry.get("forms") or []
    gender = detect_gender(entry, forms)
    singular_definite = find_form(forms, {"definite", "singular"})
    plural_indefinite = find_form(forms, {"plural"}, forbidden_tags={"definite"})
    plural_definite = find_form(forms, {"definite", "plural"})
    return {
        "gender": gender or "",
        "singular_indefinite": f"{gender} {word}" if gender else word,
        "singular_definite": singular_definite or "",
        "plural_indefinite": plural_indefinite or "",
        "plural_definite": plural_definite or "",
        "english": english,
    }


def build_from_jsonl(
    jsonl_path: Path,
    targets: BuildTargets,
    cor: dict[str, dict[str, str]] | None = None,
) -> dict[str, list[dict]]:
    verbs: list[dict] = []
    adjectives: list[dict] = []
    nouns: list[dict] = []
    seen_verbs: set[str] = set()
    seen_adj: set[str] = set()
    seen_nouns: set[str] = set()

    with jsonl_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            if (
                len(verbs) >= targets.verbs
                and len(adjectives) >= targets.adjectives
                and len(nouns) >= targets.nouns
            ):
                break
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if str(entry.get("lang_code", "")).lower() != "da":
                continue

            pos = str(entry.get("pos", "")).lower()

            if pos == "verb" and len(verbs) < targets.verbs:
                built = build_verb(entry)
                if not built:
                    continue
                if cor:
                    built = enrich_verb_from_cor(built, cor)
                if not is_complete_verb(built):
                    continue
                marker = built["infinitive"].lower()
                if marker not in seen_verbs:
                    verbs.append(built)
                    seen_verbs.add(marker)

            elif pos in {"adj", "adjective"} and len(adjectives) < targets.adjectives:
                built = build_adjective(entry)
                if not built:
                    continue
                if cor:
                    built = enrich_adjective_from_cor(built, cor)
                if not is_complete_adjective(built):
                    continue
                marker = built["base"].lower()
                if marker not in seen_adj:
                    adjectives.append(built)
                    seen_adj.add(marker)

            elif pos == "noun" and len(nouns) < targets.nouns:
                built = build_noun(entry)
                if not built:
                    continue
                if cor:
                    built = enrich_noun_from_cor(built, cor)
                if not is_complete_noun(built):
                    continue
                marker = built["singular_indefinite"].lower()
                if marker not in seen_nouns:
                    nouns.append(built)
                    seen_nouns.add(marker)

    return {"verbs": verbs, "adjectives": adjectives, "nouns": nouns, "adverbs": []}


# ---------------------------------------------------------------------------
# Enrich-only mode: patch existing split data files in-place
# ---------------------------------------------------------------------------

def run_enrich_only(data_dir: Path, cor: dict[str, dict[str, str]]) -> None:
    tasks = [
        ("verbs",      "verbs.json",      enrich_verb_from_cor),
        ("nouns",      "nouns.json",      enrich_noun_from_cor),
        ("adjectives", "adjectives.json", enrich_adjective_from_cor),
    ]
    for category, filename, enrich_fn in tasks:
        path = data_dir / filename
        if not path.exists():
            print(f"  Skipping {filename}: file not found")
            continue
        with path.open("r", encoding="utf-8") as fh:
            entries: list[dict] = json.load(fh)

        filled: dict[str, int] = {}
        enriched: list[dict] = []
        for e in entries:
            before = {k: v for k, v in e.items()}
            e2 = enrich_fn(e, cor)
            for k, v in e2.items():
                if v and not before.get(k):
                    filled[k] = filled.get(k, 0) + 1
            enriched.append(e2)

        write_json(path, enriched)
        total_filled = sum(filled.values())
        if filled:
            detail = ", ".join(f"{v} {k}" for k, v in sorted(filled.items()))
            print(f"  {category}: {len(enriched)} entries — filled {total_filled} gaps ({detail})")
        else:
            print(f"  {category}: {len(enriched)} entries — no gaps found")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    # Resolve COR data when needed
    cor: dict[str, dict[str, str]] | None = None
    if args.use_cor or args.enrich_only:
        if args.cor_file and args.cor_file.exists():
            cor_path = args.cor_file
        else:
            cor_path = Path("data") / "cache" / "cor.tsv"
            if not cor_path.exists():
                download_file(args.cor_url, cor_path)
        print(f"Loading COR from {cor_path} ...")
        cor = load_cor_lookup(cor_path)
        print(f"  {len(cor):,} lemmas loaded.")

    # Enrich-only: patch existing split files, then exit
    if args.enrich_only:
        print(f"Enriching split data files in {args.data_dir} ...")
        run_enrich_only(args.data_dir, cor)  # type: ignore[arg-type]
        print("Done.")
        return 0

    # Normal build from Kaikki
    if args.source_file:
        source_path = args.source_file
    else:
        source_path = Path("data") / "cache" / "kaikki.org-dictionary-Danish.jsonl"
        if not source_path.exists():
            download_file(args.source_url, source_path)

    targets = BuildTargets(verbs=args.verbs, adjectives=args.adjectives, nouns=args.nouns)
    print("Building lexicon from Kaikki data ...")
    generated = build_from_jsonl(source_path, targets, cor)
    write_json(args.output, generated)

    existing = read_existing_lexicon(args.merged_output)
    merged = {
        "verbs":      merge_unique(existing["verbs"],      generated["verbs"],      "infinitive"),
        "nouns":      merge_unique(existing["nouns"],      generated["nouns"],      "singular_indefinite"),
        "adjectives": merge_unique(existing["adjectives"], generated["adjectives"], "base"),
        "adverbs":    existing["adverbs"],
    }
    write_json(args.merged_output, merged)

    print("Done.")
    print(f"  Verbs:      {len(generated['verbs'])}")
    print(f"  Adjectives: {len(generated['adjectives'])}")
    print(f"  Nouns:      {len(generated['nouns'])}")
    if cor is not None:
        print("  (COR enrichment applied)")
    print(f"  Generated: {args.output}")
    print(f"  Merged:    {args.merged_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
