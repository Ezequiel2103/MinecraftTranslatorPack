import os
import subprocess
import sys


TESTS = [
    "test_ai_review.py",
    "test_api_usage.py",
    "test_batch_translation.py",
    "test_concurrency_order.py",
    "test_concurrent_control.py",
    "test_claude_translator.py",
    "test_community_import.py",
    "test_curseforge_search.py",
    "test_curseforge_zip.py",
    "test_deepseek_translator.py",
    "test_deploy_manager.py",
    "test_dictionary_io.py",
    "test_end_to_end_formats.py",
    "test_extract_texts_lists.py",
    "test_format_handlers.py",
    "test_fully_protected_text.py",
    "test_google_translate_translator.py",
    "test_language_pair_memory.py",
    "test_mod_classification_cache.py",
    "test_mod_content_filter.py",
    "test_mod_lang_cache.py",
    "test_mod_lang_scanner.py",
    "test_mod_item_glossary.py",
    "test_mod_lang_translator.py",
    "test_mod_scanner.py",
    "test_modpack_locator.py",
    "test_ollama_translator.py",
    "test_openai_translator.py",
    "test_pending_fallback.py",
    "test_placeholder_repair.py",
    "test_protected_terms.py",
    "test_quota_stop.py",
    "test_resourcepack_merger.py",
    "test_retry.py",
    "test_select_source_files.py",
    "test_service_memory_reuse.py",
    "test_skeleton_match.py",
    "test_snbt_count_guard.py",
    "test_template_matching.py",
    "test_terminology_context.py",
    "test_text_protection.py",
    "test_translate_mod_names_toggle.py",
    "test_translation_quality.py",
    "test_translation_service_ai.py",
    "test_validator_service.py",
    "test_vanilla_glossary_import.py",
]


def main():
    failures = []
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    for test_file in TESTS:
        print(f"\n=== {test_file} ===")
        result = subprocess.run(
            [sys.executable, test_file],
            text=True,
            env=env
        )

        if result.returncode != 0:
            failures.append(test_file)

    if failures:
        print("\nFallaron:")
        for test_file in failures:
            print(f"- {test_file}")
        raise SystemExit(1)

    print("\nTodas las pruebas locales pasaron.")


if __name__ == "__main__":
    main()
