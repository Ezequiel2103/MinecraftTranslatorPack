from translation.translation_service import TranslationService


class EchoAITranslator:
    def __init__(self):
        self.received_text = None

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
        self.received_text = text
        return {
            "translation": text.replace("Press", "Presiona"),
            "source": "echo_protection_test"
        }


def main():
    translator = EchoAITranslator()
    service = TranslationService(
        "en_es",
        ai_translator=translator
    )

    result = service.translate(
        "Press %s to open %sMachine\\nWelcome!"
    )

    assert "__MTP_PROTECTED_" in translator.received_text
    assert result["translation"] == (
        "Presiona %s to open %sMachine\\nWelcome!"
    )
    assert result["valid"] is True
    assert result["attempts"] == 1

    print("Text protection OK")


if __name__ == "__main__":
    main()
