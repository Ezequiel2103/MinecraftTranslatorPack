from pathlib import Path
import re

from ai.ai_translator import MockAITranslator, OllamaTranslator, OpenAITranslator
from analyzer.text_extractor import extract_texts
from analyzer.text_replacer import apply_translations
from analyzer.translation_decision import decide_translation
from analyzer.translation_validator import validate_translation
from formats.handler import get_handler
from localization.localization_manager import load_interface
from review.pending_manager import save_pending
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


def create_ai_translator(provider, model=None):
    if provider == "openai":
        return OpenAITranslator(model=model)
    if provider == "ollama":
        return OllamaTranslator(model=model)
    return MockAITranslator()


def translate_file(
    input_path,
    output_path,
    source_language="en",
    target_language="es",
    interface_language="es",
    ai_provider="mock",
    ai_model=None,
    replace_pending=True,
    review_root="review"
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    language_pair = f"{source_language}_{target_language}"
    interface = load_interface(interface_language)
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

    service = TranslationService(
        language_pair,
        ai_translator=create_ai_translator(ai_provider, ai_model)
    )
    results = []

    for item in translatable_texts:
        result = service.translate(
            item["text"],
            item["path"],
            source_language=source_language,
            target_language=target_language,
            context=item.get("parent_path")
        )
        validation = validate_translation(
            item["text"],
            result["translation"]
        )
        results.append({
            "path": item["path"],
            "original": item["text"],
            "translation": result["translation"],
            "source": result["source"],
            "valid": result["valid"] and validation["valid"],
            "validation_reason": (
                result.get("validation_reason")
                or validation["reason"]
            ),
            "attempts": result.get("attempts", 0)
        })

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
            replacements=replacement_by_index
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
        "pending_items": pending_items
    }


def translate_folder(
    input_folder,
    output_folder,
    source_language="en",
    target_language="es",
    interface_language="es",
    ai_provider="mock",
    ai_model=None,
    review_root="review",
    target_locale_name=None
):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    language_pair = f"{source_language}_{target_language}"
    files = [
        path for path in input_folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    save_pending(
        [],
        language_pair,
        replace=True,
        review_root=review_root
    )
    reports = []

    for input_path in files:
        relative_path = translated_relative_path(
            input_path.relative_to(input_folder),
            target_language,
            target_locale_name
        )
        reports.append(translate_file(
            input_path,
            output_folder / relative_path,
            source_language=source_language,
            target_language=target_language,
            interface_language=interface_language,
            ai_provider=ai_provider,
            ai_model=ai_model,
            replace_pending=False,
            review_root=review_root
        ))

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
