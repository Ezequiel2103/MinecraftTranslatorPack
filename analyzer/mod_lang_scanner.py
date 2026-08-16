import json
import re
import zipfile
from pathlib import Path


_LANG_PATH = re.compile(r"^assets/([a-z0-9_.-]+)/lang/(en_us|es_es)\.json$")


def scan_mod_lang_sources(mods_folder):
    """
    Reads every .jar in a Minecraft mods folder and finds each mod's own
    en_us.json, so its text can be translated independently of any
    specific modpack.

    Returns a list of dicts: {modid, jar_name, en_us, has_es_es}.
    Mods without an en_us.json (libraries, mods with no translatable
    text) are skipped. has_es_es marks mods that already ship their own
    Spanish translation, so they can be left untouched.
    """

    mods_folder = Path(mods_folder)
    results = []

    for jar_path in sorted(mods_folder.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar_path) as archive:
                en_us = {}
                es_es_modids = set()

                for entry in archive.namelist():
                    match = _LANG_PATH.match(entry)

                    if not match:
                        continue

                    modid, locale = match.groups()

                    if locale == "es_es":
                        es_es_modids.add(modid)
                        continue

                    try:
                        data = json.loads(
                            archive.read(entry).decode("utf-8")
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue

                    en_us.setdefault(modid, {}).update(data)

                for modid, content in en_us.items():
                    results.append({
                        "modid": modid,
                        "jar_name": jar_path.name,
                        "en_us": content,
                        "has_es_es": modid in es_es_modids
                    })

        except zipfile.BadZipFile:
            continue

    return results
