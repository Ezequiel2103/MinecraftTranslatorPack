import json
from pathlib import Path


MEMORY_PATH = (
    Path(__file__).parent
    / "en_es"
    / "memory.json"
)


def load_memory():
    if not MEMORY_PATH.exists():
        return {}

    with MEMORY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_translation(text):
    memory = load_memory()

    entry = memory.get(text)

    if entry:
        return entry["translation"]

    return None


def translate_with_memory(texts):
    results = []

    for item in texts:

        text = item["text"]
        translation = find_translation(text)

        results.append({
            "path": item["path"],
            "original": text,
            "translation": translation
        })

    return results
def add_translation(
    original,
    translation,
    translation_type="manual"
):
    """
    Adds a translation to the translation memory.
    """

    memory = load_memory()

    memory[original] = {
        "translation": translation,
        "type": translation_type,
        "source": "manual"
    }

    with MEMORY_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=4
        )