import argparse
import os

from ai.ai_translator import OpenAITranslator
from translation.translation_service import TranslationService


def main():
    parser = argparse.ArgumentParser(
        description="Optional live OpenAI translation smoke test."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Allow the real API call."
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional OpenAI model override."
    )
    args = parser.parse_args()

    if not args.live:
        print("Live test skipped. Run with --live to allow an API call.")
        return

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Configure it before using --live."
        )

    service = TranslationService(
        "en_es",
        ai_translator=OpenAITranslator(model=args.model)
    )
    result = service.translate(
        "Press %s to open the machine.\\nWelcome!",
        source_language="en",
        target_language="es",
        context="Controlled smoke test"
    )

    print(f"Translation: {result['translation']}")
    print(f"Source: {result['source']}")
    print(f"Valid: {result['valid']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Reason: {result['validation_reason']}")


if __name__ == "__main__":
    main()
