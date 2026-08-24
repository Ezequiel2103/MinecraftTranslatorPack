from ai.ai_translator import GoogleTranslateTranslator, QuotaExceededError
from translation import api_usage


def main():
    backup = (
        api_usage.USAGE_PATH.read_text(encoding="utf-8")
        if api_usage.USAGE_PATH.exists() else None
    )

    try:
        if api_usage.USAGE_PATH.exists():
            api_usage.USAGE_PATH.unlink()

        # Missing API key must fail fast and clearly instead of trying
        # (and failing) an actual network call.
        try:
            GoogleTranslateTranslator(api_key=None)
            assert False, "Debia pedir una API key"
        except RuntimeError:
            pass

        # Already over the configured limit: translate() must refuse
        # before ever touching the network, so no real API call happens
        # in this test.
        api_usage.record_usage(500)
        translator = GoogleTranslateTranslator(api_key="fake-key", char_limit=100)

        try:
            translator.translate("Diamond", "en", "es")
            assert False, "Debia lanzar QuotaExceededError"
        except QuotaExceededError:
            pass

        print("Google Translate quota guard OK")

    finally:
        if backup is not None:
            api_usage.USAGE_PATH.write_text(backup, encoding="utf-8")
        elif api_usage.USAGE_PATH.exists():
            api_usage.USAGE_PATH.unlink()


if __name__ == "__main__":
    main()
