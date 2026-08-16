from pathlib import Path


def locate_modpack_paths(modpack_root):
    """
    Given a modpack instance's root folder, finds the mods folder and the
    quests lang folder automatically, so the user only has to point at
    one path (the instance folder) instead of hunting for each subfolder
    themselves.

    Returns {"mods_folder": path_or_None, "quests_lang_folder": path_or_None}.
    """

    root = Path(modpack_root)
    result = {"mods_folder": None, "quests_lang_folder": None}

    if not root.is_dir():
        return result

    mods_candidate = root / "mods"
    if mods_candidate.is_dir():
        result["mods_folder"] = str(mods_candidate)

    known_quests_lang = root / "config" / "ftbquests" / "quests" / "lang"
    if known_quests_lang.is_dir():
        result["quests_lang_folder"] = str(known_quests_lang)
    else:
        config_dir = root / "config"
        if config_dir.is_dir():
            for lang_dir in config_dir.rglob("quests/lang"):
                if lang_dir.is_dir():
                    result["quests_lang_folder"] = str(lang_dir)
                    break

    return result
