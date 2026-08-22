from app_paths import data_dir
from json_io import load_json_safe, write_json_atomic


MEMORY_ROOT = data_dir() / "translation"


def memory_path(language_pair="en_es"):
    return MEMORY_ROOT / language_pair / "memory.json"


def load_memory(language_pair="en_es"):
    return load_json_safe(memory_path(language_pair), {})


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

    write_json_atomic(path, memory, ensure_ascii=False, indent=4)
