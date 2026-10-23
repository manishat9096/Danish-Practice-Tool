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

The dashboard keeps exercise packs below the header, session progress and translation beside the quiz, and the searchable word bank at the bottom. On phones, these sections stack vertically. Vocabulary import, export, the session seed, and reset/reload controls are under **Settings / Data**.

Use **Custom exercise builder** in the header to select specific forms and translations across categories, choose an answer style and question count, and preview the available questions. **Save setup** remembers those selections in this browser. **Add word** saves new vocabulary in the browser; **Export vocabulary** downloads a JSON copy.

- Translation answers use an inline input; multiple-choice answers and verb-table fields use compact grids.
- Quick revision appears after checking or revealing an answer. Optional `example_da` and `example_en` fields add an example sentence.
- Speaker buttons use browser text-to-speech with a Danish voice (`da-DK`). Buttons are disabled if a Danish voice is unavailable on the device. Translation requires an internet connection.
- A new session resets the score; correct answers and attempted questions are counted separately from session completion. Revealing an answer earns no points.

The full vocabulary is included through `data/lexicon.browser.js`, so opening the HTML directly also works without a server. Keep the `code/` and `data/` folders together. After editing the category JSON files, regenerate the browser copy before previewing or deploying:

```powershell
python code/build_browser_data.py
```

The Common phrases category currently has no entries. Its pack is disabled until you add phrases through **Add word** or JSON import. Empty selections display an explanation; sets smaller than the requested count report their actual size.

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
- Common phrases: `danish`, `english`

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

## Note on Kaikki extraction

Automatic Kaikki extraction is no longer part of the default refresh workflow.

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
