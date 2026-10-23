# Danish Practice Tool

This workspace now contains a small offline practice tool for Danish vocabulary and inflection drills.

## What it does

- Quizzes you on Danish verbs, nouns, adjectives, adverbs, and common phrases.
- Randomizes prompts so you can practice translation and forms.
- Uses split JSON files so you can manage each category independently.

## Run it

Open [code/danish_practice_tool.html](code/danish_practice_tool.html) in a browser.
https://manishat9096.github.io/Danish-Practice-Tool/code/danish_practice_tool.html

The page works locally without a build step.

The dashboard keeps exercise packs below the header, session progress and translation beside the quiz, and the searchable word bank at the bottom. On phones, these sections stack vertically. The vocabulary scope defaults to **Core 500**; choose **Everyday 1,500**, **Extended 3,000**, or **Full dictionary** in the header. The scope applies to quizzes, exercise packs, custom-builder availability, multiple-choice distractors, and the word bank. Vocabulary import, export, the session seed, and reset/reload controls are under **Settings / Data**.

Use **Custom exercise builder** in the header to select specific forms and translations across categories, choose an answer style and question count, and preview the available questions. **Save setup** remembers those selections in this browser. **Add word** saves new vocabulary in the browser; **Export vocabulary** downloads a JSON copy.

- Translation answers use an inline input; multiple-choice answers and verb-table fields use compact grids.
- Quick revision appears after checking or revealing an answer. Optional `example_da` and `example_en` fields add an example sentence.
- Speaker buttons use browser text-to-speech with a Danish voice (`da-DK`). Buttons are disabled if a Danish voice is unavailable on the device. Translation requires an internet connection.
- A new session resets the score; correct answers and attempted questions are counted separately from session completion. Revealing an answer earns no points.

The full vocabulary is included through `data/lexicon.browser.js`, so opening the HTML directly also works without a server. Keep the `code/` and `data/` folders together. After editing the category JSON files, regenerate the browser copy before previewing or deploying:

```powershell
python code/build_browser_data.py
```

The Common phrases pack contains 78 reviewed phrases for introductions, everyday communication, shopping, food, transport, places, healthcare, work, and social situations. Selecting **Common phrases** in the category control reveals a situation filter for focused quizzes. You can also search the word bank for a topic such as `transport` to browse that group. Empty selections display an explanation; sets smaller than the requested count report their actual size.

### Browser checks

With Chrome, Chromium, or Edge installed, run from the repository root:

```powershell
python tests/check_quiz_browser.py
```

This uses Python's standard library to check complete pack sessions, custom quizzes, search, pronunciation controls, and desktop/phone layouts in a headless browser. It tests both HTTP and direct-file opening. Screenshots of the dashboard and custom builder are saved in the system temporary directory. Speech requests and translation responses are checked without requiring audible playback or an external translation request.

If you want a Windows app later, the simplest route is to wrap the same HTML in a WebView2 or Electron shell. For now, the browser version is the lightest local option.

## Data files

The project now supports split lexicon files in `data/`:

- [data/verbs.json](data/verbs.json)
- [data/nouns.json](data/nouns.json)
- [data/adjectives.json](data/adjectives.json)
- [data/adverbs.json](data/adverbs.json)
- [data/common_phrases.json](data/common_phrases.json)

A combined file [data/lexicon.json](data/lexicon.json) is still kept for compatibility.

You can edit category files directly, or append uploaded JSON into an existing category.

- Verbs: `infinitive`, `english`, `imperative`, `past`, `present_perfect`, `past_perfect`
- Nouns: `gender`, `singular_indefinite`, `singular_definite`, `plural_indefinite`, `plural_definite`, `english`
- Adjectives: `base`, `common`, `neuter`, `plural`, `definite`, `comparative`, `superlative`, `english`
- Adverbs: `base`, `english`, and optional `comparative` / `superlative`
- Common phrases: `danish`, `english`, `topic`, `difficulty`, `curriculum_tier`

Ranked word entries also include `frequency`, `frequency_rank`, `curriculum_rank`, and `curriculum_tier`. The curriculum rank is the order among compatible entries in this practice database; `frequency_rank` retains the word's position in the original DSL list.

## Import and append workflow

In the browser tool:

- Use `Import category` to choose where the uploaded file should go.
- Use `Append JSON file` to upload a JSON array for that category.
- Duplicate entries are skipped automatically.

## CLI data management

Use [code/manage_lexicon.py](code/manage_lexicon.py) for split/merge/append operations.

### Append uploaded category file

```powershell
python code/manage_lexicon.py append --category verbs --input C:\path\to\my_verbs.json --data-dir data
```

If Python is not available, use the PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File code/append_lexicon_category.ps1 -Category verbs -InputFile C:\path\to\my_verbs.json
```

### Split combined file into category files

```powershell
python code/manage_lexicon.py split --source data/lexicon.json --data-dir data
```

### Merge category files back to combined file

```powershell
python code/manage_lexicon.py merge --data-dir data --output data/lexicon.json
```

### Validate schema

```powershell
python code/validate_lexicon.py --data-dir data --file data/lexicon.json
```

### Refresh helper

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File code/refresh_lexicon.ps1
```

This workflow:

- Merges split files into `data/lexicon.json`.
- Validates schema consistency.

## Vocabulary enrichment (no AI required)

Run the repeatable pipeline from the repository root:

```powershell
python code/enrich_lexicon.py
```

It downloads and caches the Danish Kaikki/Wiktionary JSONL, COR level-1 TSV, and DSL frequency-list archive on first use. Later runs reuse the cache. To explicitly download newer sources:

```powershell
python code/enrich_lexicon.py --refresh
```

To rebuild using only local sources, or preview counts without changing the vocabulary:

```powershell
python code/enrich_lexicon.py --offline
python code/enrich_lexicon.py --offline --dry-run
```

For alternative source snapshots or a separate output directory:

```powershell
python code/enrich_lexicon.py --source-file data/cache/kaikki.jsonl --cor-file data/cache/cor.tsv --frequency-file data/cache/freq-lemma.zip --data-dir data
```

`--limit 500` caps new additions per category in a run; the default imports all eligible entries. `--source-url`, `--cor-url`, and `--frequency-url` allow updated download locations. Source caches are ignored by Git; the generated vocabulary is included so users can practise without downloading sources.

The pipeline:

- Extracts verbs, nouns, adjectives, and adverbs. Skips inflection-only senses, obsolete/archaic/rare senses, and unsupported categories.
- Reads gender and inflected forms from Wiktionary; fills missing forms from unambiguous COR lemmas. Rejects passive/genitive forms where inappropriate. Perfect auxiliaries must be explicitly supplied by the source; they are never inferred from the participle.
- Deduplicates within each category and selects the most complete source entry for a headword. Keeps one primary meaning per headword for compatibility with the current quiz; it is not a complete multi-sense dictionary.
- Preserves existing nonempty answers and manual edits. Repairs the known verb translation placeholders where English repeats the Danish infinitive. Other disagreements are recorded for review.
- Includes translated example sentences where available, excluding attributed quotations. Imported entries carry their Wiktionary page URL, sense IDs, review status, and fields enriched by COR where applicable.
- Quarantines incomplete records and unresolved translation placeholders rather than using them as quiz answers. Missing plurals or unknown auxiliaries are not fabricated. Previous quarantined original entries are rechecked on later builds.
- Matches lemmas and parts of speech against DSL's 30,000-word frequency list. It assigns exactly 500, 1,500, and 3,000 ranked words to the cumulative curriculum scopes; unmatched entries remain in Full dictionary.
- Applies reviewed core corrections from `data/curriculum_overrides.json`, then replaces dictionary idioms with the situation-based phrases in `data/curated_phrases.json`.
- Rebuilds all five split JSON files, the combined `data/lexicon.json`, and `data/lexicon.browser.js` together.

Inspect [data/enrichment-report.json](data/enrichment-report.json) for counts, source URLs, licensing references, and SHA-256 fingerprints. [data/curriculum-report.json](data/curriculum-report.json) records scope counts, phrase topics, and reviewed corrections. [data/review/pending.json](data/review/pending.json) contains incomplete records; [data/review/conflicts.json](data/review/conflicts.json) contains disagreements with retained answers. Durable core corrections belong in `data/curriculum_overrides.json`; direct edits to generated entries can otherwise be superseded by those overrides.

Most imported vocabulary is **not human-reviewed** and the Full dictionary includes specialist words. Frequency is sourced from DSL rather than inferred. The first 500 ranked entries receive automated cross-source checks, with explicit manual corrections for issues found during review; this still does not establish native-speaker verification of every entry. Curated phrases have manually assigned A1/A2 difficulty labels. Existing disagreements still need review, and schema checks do not establish linguistic correctness.

See [data/SOURCES.md](data/SOURCES.md) for attribution and reuse terms. The older `code/build_lexicon.py` remains an extraction helper; use `code/enrich_lexicon.py` for the complete split/combined/browser workflow.

Run the offline importer regression tests and schema check:

```powershell
python -m unittest discover -s tests -p test_enrichment.py
python code/validate_lexicon.py
```


## Current exercise types

- Mixed: random blend of the available drill styles.
- Translation: Danish to English and English to Danish prompts.
- Form practice: single-form prompts for verbs, nouns, adjectives, and adverbs.
- Common phrase translation: English phrase to Danish and Danish phrase to English.
- Verb table: one verb form is given and you fill the remaining forms.
- Multiple choice: pick the correct answer from four options.

## Other good future exercise ideas

- Reverse spelling quiz: show English and ask for the Danish word without the article.
- Article drill: ask only for `en` or `et`.
- Missing-letter quiz: hide one part of the word and ask you to complete it.
- Sentence completion: insert the correct form into a short example sentence.
- Timed review mode: rapid-fire questions for exam-style practice.
