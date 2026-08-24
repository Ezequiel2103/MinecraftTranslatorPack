import json
import shutil
from pathlib import Path

from ai.ai_translator import AITranslator
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_memtest"


class CountingAITranslator(AITranslator):
    def __init__(self):
        self.calls = 0

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None,
        previous_translation=None,
        validation_error=None
    ):
        self.calls += 1
        return {
            "translation": "Traduccion de prueba",
            "source": "counting_mock"
        }


def main():
    memory_dir = Path("translation") / LANGUAGE_PAIR

    try:
        translator = CountingAITranslator()
        service = TranslationService(
            LANGUAGE_PAIR,
            ai_translator=translator
        )

        first = service.translate("Repeated Quest Title")
        second = service.translate("Repeated Quest Title")

        assert translator.calls == 1, "AI should only be called once for repeated text"
        assert first["translation"] == "Traduccion de prueba"
        assert second["translation"] == "Traduccion de prueba"
        assert second["source"] == "run_cache"

        assert not memory_dir.exists(), "nothing should be written before save_new_translations()"

        service.save_new_translations()

        memory = json.loads(
            (memory_dir / "memory.json").read_text(encoding="utf-8")
        )
        assert memory["Repeated Quest Title"]["translation"] == "Traduccion de prueba"

        print("Service memory reuse OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
