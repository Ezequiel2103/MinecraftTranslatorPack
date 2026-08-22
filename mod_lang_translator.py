import json
import shutil
from pathlib import Path

from analyzer.mod_lang_scanner import has_real_content, scan_mod_lang_sources
from analyzer.text_extractor import extract_texts
from analyzer.text_replacer import apply_translations
from analyzer.translation_decision import decide_translation
from review.pending_manager import save_pending
from translation.concurrent_translate import (
    DEFAULT_BATCH_SIZE,
    translate_items_concurrently
)
from translation.mod_classification_cache import (
    load_classification,
    save_classification
)
from translation.mod_lang_cache import (
    content_hash,
    load_cached_translation,
    save_cached_translation
)
from translation.translation_service import TranslationService
from translator_app import (
    DEFAULT_LOCALES,
    create_ai_translator,
    resolve_protected_terms
)


PACK_MCMETA = {
    "pack": {
        "pack_format": 34,
        "description": "Traducciones de mods generadas por MinecraftTranslatorPack"
    }
}


def translate_mod_lang_files(
    mods_folder,
    output_resourcepack,
    source_language="en",
    target_language="es",
    ai_provider="mock",
    ai_model=None,
    fallback_ai_provider=None,
    fallback_ai_model=None,
    concurrency=4,
    review_root=None,
    content_only=False,
    pack_icon=None,
    on_mod_progress=None,
    on_text_progress=None,
    cancel_event=None,
    resume_event=None
):
    """
    Translates every mod's own en_us.json (skipping mods that already
    ship their own translation for the target locale) and assembles the
    result as a single resource pack (all mods under the same
    assets/<modid>/lang/<locale>.json layout), so mods are translated
    without touching their jars and the player only installs one pack.

    Each mod's translation is cached by content hash under
    mod_lang_cache/<language_pair>/<modid>.json, independent of any
    specific modpack: the same mod in a different modpack reuses the
    cached translation instead of being translated again, and a mod
    update (different text) is detected and re-translated automatically.

    Texts that fail validation are recorded in the usual
    review/<language_pair>/pending.json (prefixed with "mods/<modid>/")
    instead of being silently left in the source language, same as the
    quest/lang-folder flow.

    content_only=True skips mods with no real in-game content (see
    analyzer.mod_lang_scanner.has_real_content). Each mod's
    classification is cached under
    mod_lang_cache/<language_pair>/content_classification.json the
    first time it's seen, so later runs (even for a different modpack
    that shares the mod) look it up instead of re-analyzing its lang
    file — and the file can be hand-edited to correct a mod the
    heuristic got wrong.

    pack_icon, if given, is copied in as pack.png — the icon Minecraft
    shows next to the pack's name in the resource pack list, so players
    can spot the translation at a glance.
    """

    language_pair = f"{source_language}_{target_language}"
    target_locale = DEFAULT_LOCALES.get(target_language.lower(), target_language.lower())
    sources = scan_mod_lang_sources(mods_folder, target_locale=target_locale)
    protected_terms = resolve_protected_terms(language_pair, mods_folder)
    classification = load_classification(language_pair)
    classification_changed = False

    output_resourcepack = Path(output_resourcepack)

    stats = {
        "already_translated_by_mod": 0,
        "reused_from_cache": 0,
        "translated_fresh": 0,
        "skipped_config_only": 0,
        "quota_exceeded": False,
        "mods": []
    }
    pending_items = []
    total_sources = len(sources)

    for index, source in enumerate(sources, start=1):
        if cancel_event is not None and cancel_event.is_set():
            break

        modid = source["modid"]

        if on_mod_progress:
            on_mod_progress(index, total_sources, modid)

        if modid not in classification:
            classification[modid] = has_real_content(source["en_us"])
            classification_changed = True

        if content_only and not classification[modid]:
            stats["skipped_config_only"] += 1
            continue

        if source["has_target_translation"]:
            stats["already_translated_by_mod"] += 1
            continue

        source_hash = content_hash(source["en_us"])
        cached_translation = load_cached_translation(
            modid, source_hash, language_pair
        )

        if cached_translation is not None:
            translated_lang = cached_translation
            stats["reused_from_cache"] += 1
        else:
            translated_lang, failed_results, quota_exceeded = _translate_lang_dict(
                source["en_us"],
                language_pair,
                source_language,
                target_language,
                ai_provider,
                ai_model,
                protected_terms,
                concurrency,
                on_text_progress,
                cancel_event,
                resume_event,
                fallback_ai_provider,
                fallback_ai_model
            )

            if quota_exceeded:
                stats["quota_exceeded"] = True

            for item in failed_results:
                pending_items.append({
                    "path": f"mods/{modid}/{item['path']}",
                    "original": item["original"],
                    "translation": item["translation"],
                    "source": item["source"],
                    "attempts": item.get("attempts", 0),
                    "reason": (
                        item.get("validation_reason")
                        or "translation_not_found"
                    )
                })

            save_cached_translation(
                modid, source_hash, translated_lang, language_pair,
                source_lang=source["en_us"]
            )
            stats["translated_fresh"] += 1

        lang_path = (
            output_resourcepack / "assets" / modid / "lang"
            / f"{target_locale}.json"
        )
        lang_path.parent.mkdir(parents=True, exist_ok=True)

        with lang_path.open("w", encoding="utf-8") as file:
            json.dump(translated_lang, file, ensure_ascii=False, indent=4)

        stats["mods"].append(modid)

    if classification_changed:
        save_classification(classification, language_pair)

    if pending_items:
        save_pending(
            pending_items,
            language_pair,
            replace=False,
            review_root=review_root
        )

    stats["pending_items"] = len(pending_items)

    mcmeta_path = output_resourcepack / "pack.mcmeta"
    mcmeta_path.parent.mkdir(parents=True, exist_ok=True)

    with mcmeta_path.open("w", encoding="utf-8") as file:
        json.dump(PACK_MCMETA, file, ensure_ascii=False, indent=4)

    if pack_icon:
        shutil.copyfile(pack_icon, output_resourcepack / "pack.png")

    return stats


def _translate_lang_dict(
    en_us,
    language_pair,
    source_language,
    target_language,
    ai_provider,
    ai_model,
    protected_terms,
    concurrency,
    on_text_progress=None,
    cancel_event=None,
    resume_event=None,
    fallback_ai_provider=None,
    fallback_ai_model=None
):
    texts = extract_texts(en_us)
    translatable = [
        item for item in texts
        if decide_translation(item)["action"] == "translate"
    ]

    fallback_ai_translator = (
        create_ai_translator(fallback_ai_provider, fallback_ai_model)
        if fallback_ai_provider else None
    )

    service = TranslationService(
        language_pair,
        ai_translator=create_ai_translator(ai_provider, ai_model),
        protected_terms=protected_terms,
        # Quest-specific templates (e.g. "&eKill&f: ") have no business
        # matching mod lang text, which uses entirely different phrasing.
        templates=[],
        cancel_event=cancel_event,
        fallback_ai_translator=fallback_ai_translator
    )

    results = translate_items_concurrently(
        translatable,
        service,
        source_language=source_language,
        target_language=target_language,
        concurrency=concurrency,
        # See the matching comment in translator_app.py: Argos gains
        # nothing from grouping (it loops one item at a time internally
        # either way), so batching it only delays progress updates.
        batch_size=1 if ai_provider == "argos" else DEFAULT_BATCH_SIZE,
        on_progress=on_text_progress,
        cancel_event=cancel_event,
        resume_event=resume_event,
        flush_callback=service.save_new_translations
    )

    service.save_new_translations()

    failed_results = [
        result for result in results
        if not (result["translation"] and result["valid"])
    ]

    translated_lang = apply_translations(dict(en_us), results)

    return translated_lang, failed_results, service.quota_exceeded
