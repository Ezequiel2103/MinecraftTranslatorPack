import json
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from app_paths import data_dir
from translation.translation_memory import load_memory, memory_path


MOD_CACHE_ROOT = data_dir() / "mod_lang_cache"


def export_quest_dictionary(output_path, language_pair="en_es"):
    """
    Copies the quest/lang-folder translation memory to a single portable
    file another user can import, so they don't have to pay the AI to
    re-translate the same modpack.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(memory_path(language_pair), output_path)
    return str(output_path)


def import_quest_dictionary(input_path, language_pair="en_es"):
    """
    Merges a shared quest dictionary into the local translation memory.
    Only fills in entries that don't already exist locally — an
    imported file never overwrites a translation already approved here.
    """

    with Path(input_path).open("r", encoding="utf-8") as file:
        incoming = json.load(file)

    local = load_memory(language_pair)
    added = 0

    for original, entry in incoming.items():
        if original not in local:
            local[original] = entry
            added += 1

    path = memory_path(language_pair)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(local, file, ensure_ascii=False, indent=4)

    return {"added": added, "total": len(local)}


def export_mods_dictionary(output_path, language_pair="en_es"):
    """
    Packages every cached per-mod translation (mod_lang_cache/<pair>/)
    into a single zip another user can import.
    """

    source_dir = MOD_CACHE_ROOT / language_pair
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        if source_dir.is_dir():
            for file_path in sorted(source_dir.glob("*.json")):
                archive.write(file_path, file_path.name)

    return str(output_path)


def import_mods_dictionary(input_path, language_pair="en_es"):
    """
    Merges a shared mods dictionary zip into the local mod cache. Only
    adds mods (or the classification of mods) not already cached
    locally — never overwrites an existing local entry.
    """

    target_dir = MOD_CACHE_ROOT / language_pair
    target_dir.mkdir(parents=True, exist_ok=True)

    added_mods = 0
    added_classifications = 0

    with TemporaryDirectory() as tmp:
        with zipfile.ZipFile(input_path) as archive:
            archive.extractall(tmp)

        for file_path in sorted(Path(tmp).glob("*.json")):
            target_file = target_dir / file_path.name

            if file_path.name == "content_classification.json":
                incoming = json.loads(file_path.read_text(encoding="utf-8"))
                local = (
                    json.loads(target_file.read_text(encoding="utf-8"))
                    if target_file.exists()
                    else {}
                )

                for modid, has_content in incoming.items():
                    if modid not in local:
                        local[modid] = has_content
                        added_classifications += 1

                target_file.write_text(
                    json.dumps(local, ensure_ascii=False, indent=4, sort_keys=True),
                    encoding="utf-8"
                )
                continue

            if not target_file.exists():
                shutil.copyfile(file_path, target_file)
                added_mods += 1

    return {"added_mods": added_mods, "added_classifications": added_classifications}
