from pathlib import Path
import re
import shutil

from ai.ai_translator import (
    ArgosTranslateTranslator,
    ClaudeTranslator,
    DeepSeekTranslator,
    GoogleTranslateTranslator,
    MockAITranslator,
    OllamaTranslator,
    OpenAITranslator
)
from analyzer.mod_scanner import scan_mod_names
from analyzer.text_extractor import extract_texts
from analyzer.text_replacer import apply_translations
from analyzer.translation_decision import decide_translation
from formats.handler import get_handler
from localization.localization_manager import load_interface
from review.pending_manager import save_pending
from translation.concurrent_translate import (
    DEFAULT_BATCH_SIZE,
    translate_items_concurrently
)
from translation.mod_lang_cache import build_mod_item_glossary
from translation.protected_terms_manager import (
    load_protected_terms,
    save_protected_terms
)
from translation.translation_service import TranslationService


SUPPORTED_SUFFIXES = {".json", ".lang", ".snbt"}
DEFAULT_LOCALES = {
    "en": "en_us", "es": "es_es", "pt": "pt_br", "fr": "fr_fr",
    "de": "de_de", "it": "it_it", "ru": "ru_ru", "zh": "zh_cn",
    "ja": "ja_jp", "ko": "ko_kr"
}


def translated_relative_path(relative_path, target_language, explicit_locale=None):
    locale = (explicit_locale or target_language).lower()
    locale = DEFAULT_LOCALES.get(locale, locale)
    if re.fullmatch(r"[a-z]{2}_[a-z]{2}", relative_path.stem, re.IGNORECASE):
        return relative_path.with_name(f"{locale}{relative_path.suffix}")
    return relative_path


LOCALE_STEM_PATTERN = re.compile(r"[a-z]{2,3}_[a-z0-9]{2,3}", re.IGNORECASE)


def select_source_files(files, source_language):
    """
    A lang folder can ship other locales already translated by the
    modpack (fan translations, regional English variants). Without this
    filter, every one of those gets treated as if it were the source
    language and written over the same output file, corrupting it with
    whatever language processed last.

    Only files that would actually collide on the same output path can
    corrupt each other that way, and translated_relative_path() keeps
    each file's original suffix — so "en_us.json" and "en_us.lang" never
    collide with each other, only with another same-suffix locale file
    (e.g. "en_gb.json" also colliding on "es_es.json"). So when there's
    no exact canonical match and several regional variants of the source
    language exist, only one per suffix is kept — the rest would just
    reproduce the same last-one-wins corruption this filter exists to
    prevent, one level down.
    """

    source_language = source_language.lower()
    canonical = DEFAULT_LOCALES.get(source_language)

    non_locale_files = [
        path for path in files if not LOCALE_STEM_PATTERN.fullmatch(path.stem)
    ]
    locale_files = [
        path for path in files if LOCALE_STEM_PATTERN.fullmatch(path.stem)
    ]

    suffixes = sorted({path.suffix.lower() for path in locale_files})
    selected = []

    for suffix in suffixes:
        candidates = [path for path in locale_files if path.suffix.lower() == suffix]

        if canonical:
            exact_matches = sorted(
                path for path in candidates if path.stem.lower() == canonical
            )
            if exact_matches:
                selected.append(exact_matches[0])
                continue

        prefix_matches = sorted(
            path for path in candidates
            if path.stem.lower().split("_")[0] == source_language
        )
        if prefix_matches:
            selected.append(prefix_matches[0])

    return non_locale_files + selected


def create_ai_translator(provider, model=None):
    if provider == "openai":
        return OpenAITranslator(model=model)
    if provider == "ollama":
        return OllamaTranslator(model=model)
    if provider == "claude":
        return ClaudeTranslator(model=model)
    if provider == "deepseek":
        return DeepSeekTranslator(model=model)
    if provider == "google":
        return GoogleTranslateTranslator()
    if provider == "argos":
        return ArgosTranslateTranslator()
    return MockAITranslator()


def resolve_protected_terms(language_pair, mods_folder, translate_mod_names=False):
    if translate_mod_names:
        return []

    if mods_folder:
        names, unresolved = scan_mod_names(mods_folder)
        save_protected_terms(names, language_pair)

        if unresolved:
            print(
                "⚠️ No se pudo leer el nombre de "
                f"{len(unresolved)} mod(s): {', '.join(unresolved)}"
            )

        return names

    return load_protected_terms(language_pair)


def translate_file(
    input_path,
    output_path,
    source_language="en",
    target_language="es",
    interface_language="es",
    ai_provider="mock",
    ai_model=None,
    fallback_ai_provider=None,
    fallback_ai_model=None,
    replace_pending=True,
    review_root=None,
    mods_folder=None,
    protected_terms=None,
    mod_item_glossary=None,
    translate_mod_names=False,
    concurrency=4,
    on_text_progress=None,
    cancel_event=None,
    resume_event=None
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    language_pair = f"{source_language}_{target_language}"
    interface = load_interface(interface_language)

    if protected_terms is None:
        protected_terms = resolve_protected_terms(
            language_pair,
            mods_folder,
            translate_mod_names=translate_mod_names
        )
    if mod_item_glossary is None:
        mod_item_glossary = build_mod_item_glossary(language_pair)
    data = get_handler(input_path).read(input_path)
    texts = extract_texts(data)
    translatable_texts = []
    technical_texts = []
    uncertain_texts = []

    for item in texts:
        decision = decide_translation(item)
        if decision["action"] == "translate":
            translatable_texts.append(item)
        elif decision["action"] == "ignore":
            technical_texts.append(item)
        else:
            uncertain_texts.append(item)

    fallback_ai_translator = (
        create_ai_translator(fallback_ai_provider, fallback_ai_model)
        if fallback_ai_provider else None
    )

    service = TranslationService(
        language_pair,
        ai_translator=create_ai_translator(ai_provider, ai_model),
        protected_terms=protected_terms,
        mod_item_glossary=mod_item_glossary,
        cancel_event=cancel_event,
        fallback_ai_translator=fallback_ai_translator
    )
    total_translatable = len(translatable_texts)

    def report_progress(completed, total):
        if on_text_progress:
            on_text_progress(completed, total)
            return

        print(
            interface["translating_progress"].format(
                current=completed,
                total=total
            ),
            end="\r",
            flush=True
        )

    results = translate_items_concurrently(
        translatable_texts,
        service,
        source_language=source_language,
        target_language=target_language,
        concurrency=concurrency,
        # Argos has no real batch call (see AITranslator.translate_batch's
        # default): a "batch" for it is just looping translate() one item
        # at a time inside a single worker, so grouping items only delays
        # progress reporting until the whole group finishes, with none of
        # batching's actual benefit (fewer requests). One item per group
        # keeps progress updates arriving as each one actually completes.
        batch_size=1 if ai_provider == "argos" else DEFAULT_BATCH_SIZE,
        on_progress=report_progress if total_translatable else None,
        cancel_event=cancel_event,
        resume_event=resume_event,
        flush_callback=service.save_new_translations
    )

    if total_translatable and not on_text_progress:
        print()

    service.save_new_translations()

    pending_items = []
    for result in results:
        if result["translation"] and result["valid"]:
            continue
        pending_item = dict(result)
        pending_item["reason"] = (
            result.get("validation_reason")
            or "translation_not_found"
        )
        pending_items.append(pending_item)

    for item in uncertain_texts:
        pending_items.append({
            "path": item["path"],
            "original": item["text"],
            "translation": None,
            "source": "decision_engine",
            "reason": "uncertain_context"
        })

    save_pending(
        pending_items,
        language_pair,
        replace=replace_pending,
        review_root=review_root
    )
    data = apply_translations(data, results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handler = get_handler(output_path)
    if input_path.suffix.lower() == ".snbt":
        replacement_by_index = {}
        path_to_index = {item["path"]: index for index, item in enumerate(texts)}
        for result in results:
            if result.get("valid", True) and result.get("translation") is not None:
                index = path_to_index.get(result["path"])
                if index is not None:
                    replacement_by_index[index] = result["translation"]
        handler.write(
            data,
            output_path,
            source_text=input_path.read_text(encoding="utf-8"),
            replacements=replacement_by_index,
            expected_value_count=len(texts)
        )
    else:
        handler.write(data, output_path)

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "interface": interface,
        "texts": texts,
        "results": results,
        "translatable_texts": translatable_texts,
        "technical_texts": technical_texts,
        "uncertain_texts": uncertain_texts,
        "pending_items": pending_items,
        "quota_exceeded": service.quota_exceeded
    }


def translate_folder(
    input_folder,
    output_folder,
    source_language="en",
    target_language="es",
    interface_language="es",
    ai_provider="mock",
    ai_model=None,
    fallback_ai_provider=None,
    fallback_ai_model=None,
    review_root=None,
    target_locale_name=None,
    mods_folder=None,
    translate_mod_names=False,
    concurrency=4,
    on_file_progress=None,
    on_text_progress=None,
    cancel_event=None,
    resume_event=None,
    backup_dir=None
):
    """
    backup_dir, if given, is where any file about to be overwritten gets
    copied first (keeping the same relative path it has under
    output_folder) -- meant for the case where output_folder IS the
    modpack's real lang folder (translating in place) and a previous
    run's translation, or a fan translation, already lives there.
    """

    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    backup_dir = Path(backup_dir) if backup_dir is not None else None
    language_pair = f"{source_language}_{target_language}"
    all_matching_files = [
        path for path in input_folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    files = select_source_files(all_matching_files, source_language)
    if all_matching_files and not files:
        print(
            f"Aviso: se encontraron {len(all_matching_files)} archivo(s) en "
            f"{input_folder}, pero ninguno coincide con el idioma de origen "
            f"'{source_language}'. Revisa --source-language. No se tradujo nada."
        )
    save_pending(
        [],
        language_pair,
        replace=True,
        review_root=review_root
    )
    reports = []
    interface = load_interface(interface_language)
    protected_terms = resolve_protected_terms(
        language_pair,
        mods_folder,
        translate_mod_names=translate_mod_names
    )
    mod_item_glossary = build_mod_item_glossary(language_pair)
    total_files = len(files)

    for index, input_path in enumerate(files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            break

        if on_file_progress:
            on_file_progress(index, total_files, input_path.name)
        else:
            print(
                interface["translating_file_progress"].format(
                    current=index,
                    total=total_files,
                    name=input_path.name
                )
            )
        relative_path = translated_relative_path(
            input_path.relative_to(input_folder),
            target_language,
            target_locale_name
        )
        target_path = output_folder / relative_path

        backed_up_from = None
        if backup_dir is not None and target_path.exists():
            backup_target = backup_dir / relative_path
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_path, backup_target)
            backed_up_from = str(backup_target)

        report = translate_file(
            input_path,
            target_path,
            source_language=source_language,
            target_language=target_language,
            interface_language=interface_language,
            ai_provider=ai_provider,
            ai_model=ai_model,
            fallback_ai_provider=fallback_ai_provider,
            fallback_ai_model=fallback_ai_model,
            replace_pending=False,
            review_root=review_root,
            protected_terms=protected_terms,
            mod_item_glossary=mod_item_glossary,
            concurrency=concurrency,
            on_text_progress=on_text_progress,
            cancel_event=cancel_event,
            resume_event=resume_event
        )
        report["backed_up_to"] = backed_up_from
        reports.append(report)

    return reports


def print_report(report):
    interface = report["interface"]
    print("===================================")
    print(f"     {interface['app_title']}")
    print("===================================\n")
    print(f"📝 {interface['texts_found']}: {len(report['texts'])}")
    print(f"🌎 {interface['translatable_texts']}: {len(report['translatable_texts'])}")
    print(f"🔒 {interface['technical_texts']}: {len(report['technical_texts'])}")
    print(f"❓ {interface['uncertain_texts']}: {len(report['uncertain_texts'])}\n")

    for result in report["results"]:
        if result["translation"] and result["valid"]:
            print(f"✅ {result['original']}\n   → {result['translation']}\n")
        else:
            print(f"❓ {result['original']}\n   → {interface['translation_not_found']}\n")

    print(f"✅ Archivo traducido creado: {report['output_path']}")
