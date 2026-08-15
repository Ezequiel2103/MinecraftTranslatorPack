import json
from pathlib import Path


MEMORY_ROOT = Path(__file__).parent


def memory_path(language_pair="en_es"):
    return MEMORY_ROOT / language_pair / "memory.json"


def load_memory(language_pair="en_es"):
    path = memory_path(language_pair)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_translation(text, language_pair="en_es"):
    memory = load_memory(language_pair)

    entry = memory.get(text)

    if entry:
        return entry["translation"]

    return None


def translate_with_memory(texts, language_pair="en_es"):
    results = []

    for item in texts:

        text = item["text"]
        translation = find_translation(text, language_pair)

        results.append({
            "path": item["path"],
            "original": text,
            "translation": translation
        })

    return results
def add_translation(
    original,
    translation,
    translation_type="manual",
    language_pair="en_es"
):
    """
    Adds a translation to the translation memory.
    """

    path = memory_path(language_pair)
    memory = load_memory(language_pair)

    memory[original] = {
        "translation": translation,
        "type": translation_type,
        "source": "manual"
    }

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=4
        )
