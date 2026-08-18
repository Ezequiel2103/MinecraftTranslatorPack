import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from analyzer.mod_lang_scanner import scan_mod_lang_sources
from translation.mod_lang_cache import build_text_glossary, merge_into_item_glossary
from translation.resourcepack_merger import iter_lang_files


def import_community_resourcepack(
    pack_path, mods_folder, language_pair="en_es", target_locale="es_es"
):
    """
    Takes an already-translated resource pack (a community download, a
    friend's export, anything in the usual assets/<modid>/lang/<locale>
    layout) and feeds it into the same cross-modpack item glossary the
    AI-translated mods use — so quest and mod text that matches gets
    reused for free, with zero AI calls, exactly like a mod we already
    translated ourselves.

    Only mods actually present in mods_folder are considered, matched by
    modid against their OWN en_us.json, so the English/translated pairs
    are always correctly paired to real source text instead of trusting
    the downloaded pack's structure blindly.
    """

    pack_path = Path(pack_path)

    with TemporaryDirectory() as tmp:
        if pack_path.is_dir():
            root = pack_path
        elif zipfile.is_zipfile(pack_path):
            root = Path(tmp) / "extracted"
            with zipfile.ZipFile(pack_path) as archive:
                archive.extractall(root)
        else:
            raise ValueError(
                f"'{pack_path}' no es ni una carpeta ni un archivo .zip valido."
            )

        translated_by_modid = {}

        for modid, locale, lang_file in iter_lang_files(root):
            if locale != target_locale:
                continue

            try:
                translated_by_modid[modid] = json.loads(
                    lang_file.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                continue

        if not translated_by_modid:
            return {"mods_matched": 0, "pairs_added": 0}

        sources = scan_mod_lang_sources(mods_folder, target_locale=target_locale)
        mods_matched = 0
        pairs_added = 0

        for source in sources:
            translated = translated_by_modid.get(source["modid"])

            if not translated:
                continue

            pairs = build_text_glossary(source["en_us"], translated)

            if not pairs:
                continue

            merge_into_item_glossary(pairs, language_pair)
            mods_matched += 1
            pairs_added += len(pairs)

        return {"mods_matched": mods_matched, "pairs_added": pairs_added}
