"""Offline regression tests for source extraction and safe, repeatable merging."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import build_lexicon as extract
import enrich_lexicon as pipeline
import build_curriculum


def verb(word="spise", auxiliary="have /havde"):
    return {"word": word, "lang_code": "da", "pos": "verb",
            "senses": [{"glosses": ["eat"], "id": "eat-1"}], "forms": [
                {"form": "spistes", "tags": ["passive", "past"]},
                {"form": "spiste", "tags": ["active", "past"]},
                {"form": "spis", "tags": ["imperative"]},
                {"form": f"({auxiliary}) spist", "tags": ["past", "participle"]}]}


class ExtractionTests(unittest.TestCase):
    def test_active_and_source_auxiliary(self):
        entry = extract.build_verb(verb())
        self.assertEqual(entry["past"], "spiste")
        self.assertEqual(entry["present_perfect"], "har spist")
        entry = extract.build_verb(verb(auxiliary="er /var"))
        self.assertEqual(entry["present_perfect"], "er spist")
        self.assertEqual(entry["past_perfect"], "var spist")

    def test_unknown_auxiliary_is_not_guessed(self):
        raw = verb()
        raw["forms"] = [{"form": "spist", "tags": ["perfect"]}]
        entry = extract.build_verb(raw)
        extract.enrich_verb_from_cor(entry, {"spise": {"vb.perf.part": "spist"}})
        self.assertFalse(entry["present_perfect"])

    def test_gender_from_sense_and_no_genitives(self):
        entry = extract.build_noun({"word": "bog", "senses": [{"glosses": ["book"], "tags": ["common-gender"]}],
                                    "forms": [{"form": "bogens", "tags": ["genitive", "singular", "definite"]},
                                              {"form": "bogen", "tags": ["singular", "definite"]}]})
        self.assertEqual(entry["gender"], "en")
        self.assertEqual(entry["singular_definite"], "bogen")

    def test_inflections_and_archaisms_filtered(self):
        for sense in [{"glosses": ["plural of book"], "form_of": [{"word": "book"}]},
                      {"glosses": ["old word"], "tags": ["archaic"]}]:
            self.assertIsNone(extract.choose_english({"senses": [sense]}))

    def test_cor_ambiguous_lemmas_not_spliced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cor.tsv"
            path.write_text("COR.1.110.01\tbog\tbook\tsb.fk.sg.ubest.\tbog\tN\n"
                            "COR.2.112.01\tbog\tfruit\tsb.fk.pl.ubest.\tbog\tN\n"
                            "COR.3.206.01\tspise\ta gloss with a period.\tvb.præt.akt.\tspiste\tN\n", encoding="utf-8")
            lookup = pipeline.safe_cor(path)
            self.assertNotIn("bog", lookup)
            self.assertEqual(lookup["spise"]["vb.præt.akt"], "spiste")


class PipelineTests(unittest.TestCase):
    def test_merge_review_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            source = data / "source.jsonl"
            source.write_text(json.dumps(verb()) + "\n" + json.dumps({
                "word": "god morgen", "lang_code": "da", "pos": "phrase",
                "senses": [{"glosses": ["good morning"]}]}) + "\n", encoding="utf-8")
            extract.write_json(data / "verbs.json", [
                {"infinitive": "at spise", "english": "at spise", "past": "custom past"},
                {"infinitive": "at unknown", "english": "at unknown"}])
            first, report, pending, conflicts = pipeline.build(source, None, data)
            self.assertEqual(first["verbs"][0]["english"], "eat")
            self.assertEqual(first["verbs"][0]["past"], "custom past")
            self.assertEqual(len(first["common_phrases"]), 1)
            self.assertEqual(report["filled_fields"]["english"], 1)
            self.assertEqual(conflicts[0]["field"], "past")
            self.assertTrue(any(p["reason"] == "unresolved_translation_placeholder" for p in pending))
            for c, entries in first.items():
                extract.write_json(data / f"{c}.json", entries)
            extract.write_json(data / "review" / "pending.json", pending)
            second, _, second_pending, _ = pipeline.build(source, None, data)
            self.assertEqual(first, second)
            self.assertEqual(pending, second_pending)

    def test_broken_source_fails_with_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.jsonl"
            path.write_text("{}\ninvalid\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2"):
                pipeline.build(path, None, Path(tmp))


class CurriculumTests(unittest.TestCase):
    def test_ranking_tiers_pos_matching_and_curated_phrases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frequency = root / "frequency.zip"
            with zipfile.ZipFile(frequency, "w") as archive:
                archive.writestr("freq-30k-ex.txt", "V\tvære\t0.2\nNC\tbog\t0.1\nD\tikke\t0.08\nA\tbog\t0.01\n")
            phrases = root / "phrases.json"
            phrases.write_text(json.dumps([{"danish": "Godmorgen", "english": "Good morning",
                                             "topic": "introductions", "curriculum_tier": "core_500"}]), encoding="utf-8")
            overrides = root / "overrides.json"
            overrides.write_text(json.dumps([{"category": "verbs", "lemma": "være",
                                               "fields": {"english": "to be"}, "note": "reviewed"}]), encoding="utf-8")
            vocabulary = {"verbs": [{"infinitive": "at være", "english": "be"}],
                          "nouns": [{"singular_indefinite": "en bog", "english": "book"}],
                          "adjectives": [{"base": "bog", "english": "poor"}],
                          "adverbs": [{"base": "ikke", "english": "not"}], "common_phrases": []}
            report = build_curriculum.apply_curriculum(vocabulary, frequency, phrases, overrides)
            self.assertEqual(vocabulary["verbs"][0]["curriculum_rank"], 1)
            self.assertEqual(vocabulary["verbs"][0]["english"], "to be")
            self.assertEqual(vocabulary["nouns"][0]["curriculum_rank"], 2)
            self.assertEqual(vocabulary["adverbs"][0]["curriculum_rank"], 3)
            self.assertEqual(vocabulary["adjectives"][0]["curriculum_rank"], 4)
            self.assertEqual(vocabulary["common_phrases"][0]["topic"], "introductions")
            self.assertEqual(report["manual_core_corrections"], 1)


if __name__ == "__main__":
    unittest.main()
