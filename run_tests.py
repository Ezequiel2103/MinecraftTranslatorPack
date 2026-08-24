import os
import subprocess
import sys


TESTS = [
    "test_ai_review",
    "test_api_usage",
    "test_argos_word_repair",
    "test_batch_translation",
    "test_concurrency_order",
    "test_concurrent_control",
    "test_claude_translator",
    "test_community_import",
    "test_curseforge_search",
    "test_curseforge_zip",
    "test_deepseek_translator",
    "test_deploy_manager",
    "test_dictionary_io",
    "test_end_to_end_formats",
    "test_extract_texts_lists",
    "test_format_handlers",
    "test_fully_protected_text",
    "test_google_translate_translator",
    "test_json_corruption_recovery",
    "test_language_pair_memory",
    "test_mod_classification_cache",
    "test_mod_content_filter",
    "test_mod_lang_cache",
    "test_mod_lang_scanner",
    "test_mod_item_glossary",
    "test_mod_lang_translator",
    "test_mod_scanner",
    "test_modpack_locator",
    "test_ollama_translator",
    "test_openai_translator",
    "test_pending_fallback",
    "test_placeholder_repair",
    "test_progress_throttle",
    "test_protected_terms",
    "test_quota_stop",
    "test_resourcepack_merger",
    "test_retry",
    "test_retry_pending_fix",
    "test_select_source_files",
    "test_service_memory_reuse",
    "test_skeleton_match",
    "test_snbt_count_guard",
    "test_template_matching",
    "test_translate_in_place",
    "test_terminology_context",
    "test_text_protection",
    "test_translate_mod_names_toggle",
    "test_translated_lists",
    "test_translation_quality",
    "test_translation_service_ai",
    "test_validator_service",
    "test_vanilla_glossary_import",
    "test_word_inference",
]


def main():
    failures = []
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    for test_name in TESTS:
        print(f"\n=== {test_name} ===")
        result = subprocess.run(
            [sys.executable, "-m", f"tests.{test_name}"],
            text=True,
            env=env
        )

        if result.returncode != 0:
            failures.append(test_name)

    if failures:
        print("\nFallaron:")
        for test_name in failures:
            print(f"- {test_name}")
        raise SystemExit(1)

    print("\nTodas las pruebas locales pasaron.")


if __name__ == "__main__":
    main()
