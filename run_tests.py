import subprocess
import sys


TESTS = [
    "test_ai_review.py",
    "test_claude_translator.py",
    "test_deepseek_translator.py",
    "test_end_to_end_formats.py",
    "test_format_handlers.py",
    "test_fully_protected_text.py",
    "test_language_pair_memory.py",
    "test_mod_scanner.py",
    "test_ollama_translator.py",
    "test_openai_translator.py",
    "test_pending_fallback.py",
    "test_protected_terms.py",
    "test_retry.py",
    "test_terminology_context.py",
    "test_text_protection.py",
    "test_translation_quality.py",
    "test_translation_service_ai.py",
    "test_validator_service.py",
]


def main():
    failures = []

    for test_file in TESTS:
        print(f"\n=== {test_file} ===")
        result = subprocess.run(
            [sys.executable, test_file],
            text=True
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
