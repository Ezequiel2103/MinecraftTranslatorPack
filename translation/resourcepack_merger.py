import json
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


PACK_MCMETA = {
    "pack": {
        "pack_format": 34,
        "description": "Traducciones de mods combinadas por MinecraftTranslatorPack"
    }
}


def iter_lang_files(source_root):
    assets_dir = Path(source_root) / "assets"

    if not assets_dir.is_dir():
        return

    for lang_file in sorted(assets_dir.glob("*/lang/*.json")):
        modid = lang_file.parent.parent.name
        locale = lang_file.stem
        yield modid, locale, lang_file


def merge_resourcepacks(source_paths, output_path, pack_icon=None):
    """
    Combines several already-translated resource packs (each a folder or
    a .zip in the usual assets/<modid>/lang/<locale>.json layout) into
    one, so a player only has to install a single pack instead of one
    per source (e.g. one you translated plus a couple a friend shared).

    If two sources both provide a translation for the same modid+locale,
    the FIRST source given wins — never silently overwritten by a later
    one — and the collision is reported back so it can be checked by
    hand instead of guessed at.

    Returns {"output_path", "merged_mods", "conflicts"}.
    """

    output_path = Path(output_path)
    merged_mods = set()
    conflicts = []
    claimed_by = {}

    with TemporaryDirectory() as tmp:
        roots = []

        for index, source in enumerate(source_paths):
            source = Path(source)

            if source.is_dir():
                roots.append(source)
            elif zipfile.is_zipfile(source):
                extract_dir = Path(tmp) / f"source_{index}"
                with zipfile.ZipFile(source) as archive:
                    archive.extractall(extract_dir)
                roots.append(extract_dir)
            else:
                raise ValueError(
                    f"'{source}' no es ni una carpeta ni un archivo .zip valido."
                )

        for root in roots:
            for modid, locale, lang_file in iter_lang_files(root):
                key = (modid, locale)

                if key in claimed_by:
                    conflicts.append({
                        "modid": modid,
                        "locale": locale,
                        "kept_from": str(claimed_by[key]),
                        "skipped_from": str(root)
                    })
                    continue

                claimed_by[key] = root
                destination = (
                    output_path / "assets" / modid / "lang" / f"{locale}.json"
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(lang_file, destination)
                merged_mods.add(modid)

    mcmeta_path = output_path / "pack.mcmeta"
    mcmeta_path.parent.mkdir(parents=True, exist_ok=True)

    with mcmeta_path.open("w", encoding="utf-8") as file:
        json.dump(PACK_MCMETA, file, ensure_ascii=False, indent=4)

    if pack_icon:
        shutil.copyfile(pack_icon, output_path / "pack.png")

    return {
        "output_path": str(output_path),
        "merged_mods": sorted(merged_mods),
        "conflicts": conflicts
    }
