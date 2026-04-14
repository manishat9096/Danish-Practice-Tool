# Danish Practice Tool

This workspace now contains a small offline practice tool for Danish vocabulary and inflection drills.

## What it does

- Quizzes you on Danish verbs, nouns, adjectives, and adverbs.
- Randomizes prompts so you can practice translation and forms.
- Uses a JSON lexicon file so you can keep adding your own words.

## Run it

Open [code/danish_practice_tool.html](code/danish_practice_tool.html) in a browser.

The page works locally without a build step.

If you want a Windows app later, the simplest route is to wrap the same HTML in a WebView2 or Electron shell. For now, the browser version is the lightest local option.

## Data file

Edit [data/lexicon.json](data/lexicon.json) to add more vocabulary. The browser app uses the same underlying structure, so you can keep the data in sync easily.

- Verbs: `infinitive`, `english`, `imperative`, `past`, `present_perfect`, `past_perfect`
- Nouns: `gender`, `singular_indefinite`, `singular_definite`, `plural_indefinite`, `plural_definite`, `english`
- Adjectives: `base`, `common`, `neuter`, `plural`, `definite`, `comparative`, `superlative`, `english`
- Adverbs: `base`, `english`, and optional `comparative` / `superlative`

## Automatic data expansion

You can auto-generate a much larger word bank (hundreds of verbs/adjectives and many nouns) from Kaikki/Wiktextract Danish data.

### One-command refresh

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File code/refresh_lexicon.ps1 -Verbs 250 -Adjectives 200 -Nouns 600
```

This workflow:

- Downloads the Danish JSONL source to `data/cache/` (if a local source file is not provided).
- Builds `data/lexicon.generated.json` with the requested counts.
- Merges unique items into `data/lexicon.json`.
- Validates schema consistency.

### Load generated data inside the app

After you generate data, open the HTML tool and use:

- `Load generated data`: tries to load `../data/lexicon.generated.json` automatically.
- `Import JSON file`: manual fallback if browser file permissions block automatic loading.

The app then refreshes the word bank and quiz data immediately.

### Direct builder command

```bash
python code/build_lexicon.py --verbs 220 --adjectives 220 --nouns 450
python code/validate_lexicon.py --file data/lexicon.json
```

### Notes

- The importer prioritizes quality and complete forms over raw quantity.
- Free online lexical sources can have gaps; not every entry has all Danish forms.
- Generated data should still be spot-checked for learning quality.

## Current exercise types

- Mixed: random blend of the available drill styles.
- Translation: Danish to English and English to Danish prompts.
- Form practice: single-form prompts for verbs, nouns, adjectives, and adverbs.
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
