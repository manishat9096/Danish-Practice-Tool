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

## Next useful step

If you want, the next upgrade should be a simple UI so you can click through quizzes instead of using the terminal.
