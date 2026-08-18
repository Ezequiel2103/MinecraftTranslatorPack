"""
Seeds the translation memory with Mojang's own official translations for
vanilla Minecraft (item/block/entity names, UI text, etc.), pulled straight
from an installed Minecraft client. This gives quest text an instant,
professionally-translated match for anything that mentions base-game
content, without spending any AI budget, and never overwrites an existing
memory entry.
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path

from translation.translation_memory import load_memory, memory_path


DEFAULT_MINECRAFT_ROOT = Path.home() / "AppData" / "Roaming" / ".minecraft"


def find_latest_client_jar(minecraft_root):
    versions_dir = Path(minecraft_root) / "versions"
    if not versions_dir.is_dir():
        return None

    candidates = list(versions_dir.glob("*/*.jar"))
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def find_latest_asset_index(minecraft_root):
    indexes_dir = Path(minecraft_root) / "assets" / "indexes"
    if not indexes_dir.is_dir():
        return None

    candidates = list(indexes_dir.glob("*.json"))
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def read_asset_object(minecraft_root, asset_index_path, asset_key):
    index_data = json.loads(Path(asset_index_path).read_text(encoding="utf-8"))
    entry = index_data["objects"].get(asset_key)
    if entry is None:
        return None

    object_hash = entry["hash"]
    object_path = (
        Path(minecraft_root) / "assets" / "objects"
        / object_hash[:2] / object_hash
    )
    if not object_path.exists():
        return None

    return json.loads(object_path.read_text(encoding="utf-8"))


def read_jar_lang_file(client_jar_path, locale):
    with zipfile.ZipFile(client_jar_path) as jar:
        entry_name = f"assets/minecraft/lang/{locale}.json"
        if entry_name not in jar.namelist():
            return None
        return json.loads(jar.read(entry_name).decode("utf-8"))


def load_vanilla_pairs(minecraft_root, client_jar_path=None, asset_index_path=None):
    client_jar_path = client_jar_path or find_latest_client_jar(minecraft_root)
    asset_index_path = asset_index_path or find_latest_asset_index(minecraft_root)

    if client_jar_path is None:
        raise FileNotFoundError(
            "No vanilla Minecraft client jar found under "
            f"{minecraft_root}\\versions. Pass --client-jar explicitly."
        )
    if asset_index_path is None:
        raise FileNotFoundError(
            "No asset index found under "
            f"{minecraft_root}\\assets\\indexes. Pass --asset-index explicitly."
        )

    en_us = read_jar_lang_file(client_jar_path, "en_us")
    if en_us is None:
        raise FileNotFoundError(
            f"{client_jar_path} does not contain assets/minecraft/lang/en_us.json"
        )

    es_es = read_asset_object(minecraft_root, asset_index_path, "minecraft/lang/es_es.json")
    if es_es is None:
        raise FileNotFoundError(
            "Could not find minecraft/lang/es_es.json in the asset index "
            f"{asset_index_path}. Has Spanish been downloaded/selected in "
            "this Minecraft install at least once?"
        )

    pairs = {}
    for key, english_text in en_us.items():
        spanish_text = es_es.get(key)
        if not spanish_text or not english_text:
            continue
        if spanish_text == english_text:
            continue
        pairs[english_text] = spanish_text

    return pairs


def import_vanilla_glossary(
    minecraft_root=DEFAULT_MINECRAFT_ROOT,
    client_jar_path=None,
    asset_index_path=None,
    language_pair="en_es"
):
    pairs = load_vanilla_pairs(minecraft_root, client_jar_path, asset_index_path)

    memory = load_memory(language_pair)
    added = 0
    skipped_existing = 0

    for english_text, spanish_text in pairs.items():
        if english_text in memory:
            skipped_existing += 1
            continue

        memory[english_text] = {
            "translation": spanish_text,
            "type": "vanilla_minecraft",
            "source": "minecraft_official"
        }
        added += 1

    path = memory_path(language_pair)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=4)

    return {
        "found_pairs": len(pairs),
        "added": added,
        "skipped_existing": skipped_existing,
        "total_memory_entries": len(memory)
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Seed the translation memory with Mojang's official vanilla "
            "Minecraft translations, read from an installed client."
        )
    )
    parser.add_argument("--minecraft-root", default=str(DEFAULT_MINECRAFT_ROOT))
    parser.add_argument("--client-jar", default=None)
    parser.add_argument("--asset-index", default=None)
    parser.add_argument("--language-pair", default="en_es")
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()

    result = import_vanilla_glossary(
        minecraft_root=args.minecraft_root,
        client_jar_path=args.client_jar,
        asset_index_path=args.asset_index,
        language_pair=args.language_pair
    )

    print(f"Pares oficiales encontrados: {result['found_pairs']}")
    print(f"Agregados a la memoria: {result['added']}")
    print(f"Ya existian (no se tocaron): {result['skipped_existing']}")
    print(f"Total en memoria ahora: {result['total_memory_entries']}")


if __name__ == "__main__":
    main()
