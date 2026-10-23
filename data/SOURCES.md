# Vocabulary sources and attribution

The expanded vocabulary uses English Wiktionary contributors' work, extracted
by [Kaikki](https://kaikki.org/dictionary/Danish/) using
[Wiktextract](https://github.com/tatuylonen/wiktextract).

Wiktionary text is reused under
[Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).
See [Wiktionary's copyright information](https://en.wiktionary.org/wiki/Wiktionary:Copyrights).
Each imported entry's `provenance.url` links to the original Danish entry;
contributors can be found through that page's history. The application has
selected a primary English gloss, simplified gloss formatting, selected
inflected forms, and merged compatible fields with existing vocabulary.
These adapted Wiktionary-derived texts remain available under CC BY-SA 4.0.
This notice concerns the imported text, not a change to the application's code license.

Inflectional enrichment uses the **Central Danish Word Register (COR), level 1**,
provided by **Dansk Sprognævn (Danish Language Council)**. Its base resource is
free, publicly available, and open for any use according to the
[COR documentation](https://ordregister.dk/doc/COR.html).
The build report identifies the source snapshot and download location.
Ambiguous COR lemmas are excluded from automated gap filling.

Curriculum ordering uses **DSL's 30,000 most frequent Danish lemmas**, excluding
proper nouns and numerals. The list was compiled by Jørg Asmussen from the 2024
BAKSPEJLET corpus. See the [resource description](https://korpus.dsl.dk/resources/details/freq-lemmas.html)
and [DSL open-resource terms](https://korpus.dsl.dk/resources/licences/dsl-open.html).
The application stores both the original source rank and a curriculum rank among
the word classes supported by the practice tool. DSL does not endorse this tool.

`enrichment-report.json` records source fingerprints and counts.
Imported entries are marked `imported_unreviewed`; existing entries enriched
with imported fields are marked `existing_with_imported_enrichment`.
Neither status means that the complete entry has been checked by a Danish speaker.
Existing nonempty data may disagree with source data: see `review/conflicts.json`.

Audio and images from these sources have not been imported. Only translated
usage examples marked as examples, without an external quotation reference,
are selected. Specialist vocabulary is retained in the Full dictionary.
The practical phrase collection is maintained by this project rather than
copied from the frequency list.
