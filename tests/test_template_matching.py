import json
import shutil
from pathlib import Path

from ai.ai_translator import AITranslator
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_templatetest"

TEMPLATES = [
    {"en_prefix": "&eKill&f: ", "es_prefix": "&eMatar&f: ", "en_suffix": "", "es_suffix": ""}
]


TRANSLATIONS = {
    "Zombie": "Zombi",
    "Skeleton": "Esqueleto",
    "Something else entirely": "Otra cosa completamente distinta"
}


class RecordingAITranslator(AITranslator):
    def __init__(self):
        self.calls = []

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
        self.calls.append(text)
        return {"translation": TRANSLATIONS[text], "source": "recording_mock"}


def main():
    memory_dir = Path("translation") / LANGUAGE_PAIR

    try:
        translator = RecordingAITranslator()
        service = TranslationService(
            LANGUAGE_PAIR,
            ai_translator=translator,
            templates=TEMPLATES
        )

        result = service.translate(
            "&eKill&f: Zombie",
            source_language="en",
            target_language="es"
        )

        # Only the variable part should have gone to the AI, not the
        # whole templated string.
        assert translator.calls == ["Zombie"], translator.calls
        assert result["translation"] == "&eMatar&f: Zombi"
        assert result["source"] == "template"
        assert result["valid"]

        # A second, different monster reuses the same template and the
        # AI is called again only for the new variable part.
        result2 = service.translate(
            "&eKill&f: Skeleton",
            source_language="en",
            target_language="es"
        )
        assert translator.calls == ["Zombie", "Skeleton"]
        assert result2["translation"] == "&eMatar&f: Esqueleto"

        # Text that doesn't match any template prefix falls through to a
        # normal, whole-string AI translation.
        result3 = service.translate(
            "Something else entirely",
            source_language="en",
            target_language="es"
        )
        assert result3["translation"] == "Otra cosa completamente distinta"
        assert result3["source"] == "recording_mock"

        service.save_new_translations()
        memory = json.loads((memory_dir / "memory.json").read_text(encoding="utf-8"))
        # The combined template result gets memoized as a plain entry,
        # so next time it's an exact memory hit with no template work.
        assert memory["&eKill&f: Zombie"]["translation"] == "&eMatar&f: Zombi"

        print("Template matching OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
