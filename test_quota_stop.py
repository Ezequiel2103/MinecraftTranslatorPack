import threading

from ai.ai_translator import AITranslator, QuotaExceededError
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_quotatest"


class QuotaExceededTranslator(AITranslator):
    """Simulates a provider whose usage cap has been reached."""

    def translate(self, *args, **kwargs):
        raise QuotaExceededError("limite alcanzado")


def main():
    import shutil
    from pathlib import Path
    memory_dir = Path("translation") / LANGUAGE_PAIR

    try:
        cancel_event = threading.Event()
        service = TranslationService(
            LANGUAGE_PAIR,
            ai_translator=QuotaExceededTranslator(),
            cancel_event=cancel_event
        )

        assert service.quota_exceeded is False
        assert not cancel_event.is_set()

        result = service.translate(
            "Some brand new quest text",
            source_language="en",
            target_language="es"
        )

        assert result["translation"] is None
        assert result["valid"] is False
        assert result["source"] == "quota_exceeded"
        assert result["validation_reason"] == "quota_exceeded"

        # The service must flag itself AND signal the shared cancel_event
        # so the rest of a concurrent batch stops instead of hammering a
        # provider that will keep failing.
        assert service.quota_exceeded is True
        assert cancel_event.is_set()

        print("Quota stop-on-limit OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
