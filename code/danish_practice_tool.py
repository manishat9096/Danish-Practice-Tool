from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_FILE = ROOT_DIR / "data" / "lexicon.json"


def load_lexicon(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        raise FileNotFoundError(f"Lexicon file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    for category in ("verbs", "nouns", "adjectives", "adverbs"):
        data.setdefault(category, [])

    return data


def normalize_answer(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    text = re.sub(r"[\s\-]+", " ", text)
    text = re.sub(r"[.!?,;:]+$", "", text)
    return text


def compare_answers(user_answer: str, accepted_answers: Iterable[str]) -> bool:
    normalized_user_answer = normalize_answer(user_answer)
    normalized_answers = {normalize_answer(answer) for answer in accepted_answers if answer}
    return normalized_user_answer in normalized_answers


def make_exercises(lexicon: dict[str, list[dict[str, Any]]], category: str) -> list[dict[str, Any]]:
    if category == "all":
        items: list[dict[str, Any]] = []
        for subcategory in ("verbs", "nouns", "adjectives", "adverbs"):
            items.extend(make_exercises(lexicon, subcategory))
        return items

    exercises: list[dict[str, Any]] = []
    for item in lexicon.get(category, []):
        if category == "verbs":
            exercises.extend(verb_exercises(item))
        elif category == "nouns":
            exercises.extend(noun_exercises(item))
        elif category == "adjectives":
            exercises.extend(adjective_exercises(item))
        elif category == "adverbs":
            exercises.extend(adverb_exercises(item))

    return exercises


def verb_exercises(item: dict[str, Any]) -> list[dict[str, Any]]:
    infinitive = item["infinitive"]
    bare_infinitive = infinitive[3:] if infinitive.startswith("at ") else infinitive
    english = item["english"]
    exercises = [
        {"prompt": f"English -> Danish infinitive for '{english}'", "answers": [infinitive, bare_infinitive]},
        {"prompt": f"English -> imperative for '{english}'", "answers": [item["imperative"]]},
        {"prompt": f"English -> past tense for '{english}'", "answers": [item["past"]]},
        {"prompt": f"English -> present perfect for '{english}'", "answers": [item["present_perfect"]]},
        {"prompt": f"English -> past perfect for '{english}'", "answers": [item["past_perfect"]]},
        {"prompt": f"Danish infinitive -> English for '{infinitive}'", "answers": [english]},
    ]
    return exercises


def noun_exercises(item: dict[str, Any]) -> list[dict[str, Any]]:
    english = item["english"]
    exercises = [
        {"prompt": f"English -> Danish noun for '{english}'", "answers": [item["singular_indefinite"]]},
        {"prompt": f"English -> definite singular for '{english}'", "answers": [item["singular_definite"]]},
        {"prompt": f"English -> plural for '{english}'", "answers": [item["plural_indefinite"]]},
        {"prompt": f"English -> definite plural for '{english}'", "answers": [item["plural_definite"]]},
        {"prompt": f"English -> gender article for '{english}'", "answers": [item["gender"]]},
        {"prompt": f"Danish noun -> English for '{item['singular_indefinite']}'", "answers": [english]},
    ]
    return exercises


def adjective_exercises(item: dict[str, Any]) -> list[dict[str, Any]]:
    english = item["english"]
    exercises = [
        {"prompt": f"English -> base adjective for '{english}'", "answers": [item["base"]]},
        {"prompt": f"English -> common form for '{english}'", "answers": [item["common"]]},
        {"prompt": f"English -> neuter form for '{english}'", "answers": [item["neuter"]]},
        {"prompt": f"English -> plural/definite form for '{english}'", "answers": [item["plural"]]},
        {"prompt": f"English -> comparative form for '{english}'", "answers": [item["comparative"]]},
        {"prompt": f"English -> superlative form for '{english}'", "answers": [item["superlative"]]},
        {"prompt": f"Danish adjective -> English for '{item['base']}'", "answers": [english]},
    ]
    return exercises


def adverb_exercises(item: dict[str, Any]) -> list[dict[str, Any]]:
    english = item["english"]
    exercises = [
        {"prompt": f"English -> Danish adverb for '{english}'", "answers": [item["base"]]},
        {"prompt": f"Danish adverb -> English for '{item['base']}'", "answers": [english]},
    ]

    if item.get("comparative"):
        exercises.append(
            {"prompt": f"English -> comparative form for '{english}'", "answers": [item["comparative"]]}
        )
    if item.get("superlative"):
        exercises.append(
            {"prompt": f"English -> superlative form for '{english}'", "answers": [item["superlative"]]}
        )

    return exercises


def run_quiz(exercises: list[dict[str, Any]], count: int, seed: int | None) -> int:
    if not exercises:
        raise ValueError("No exercises were generated. Check the lexicon data.")

    rng = random.Random(seed)
    selected = exercises.copy()
    rng.shuffle(selected)
    selected = selected[: min(count, len(selected))]

    correct = 0
    print(f"Loaded {len(exercises)} total prompts. Running {len(selected)} round(s).\n")

    for index, exercise in enumerate(selected, start=1):
        print(f"{index}. {exercise['prompt']}")
        user_answer = input("Your answer: ").strip()
        if compare_answers(user_answer, exercise["answers"]):
            print("Correct\n")
            correct += 1
        else:
            accepted = ", ".join(exercise["answers"])
            print(f"Not quite. Accepted answer(s): {accepted}\n")

    return correct


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Practice Danish vocabulary, forms, and translations.")
    parser.add_argument(
        "--category",
        choices=["all", "verbs", "nouns", "adjectives", "adverbs"],
        default="all",
        help="Vocabulary category to quiz.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of questions to ask.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for repeatable practice sessions.",
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="Path to the lexicon JSON file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lexicon = load_lexicon(args.data_file)
    exercises = make_exercises(lexicon, args.category)
    correct = run_quiz(exercises, args.count, args.seed)
    total = min(args.count, len(exercises))
    print(f"Score: {correct}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())