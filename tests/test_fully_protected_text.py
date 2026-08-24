from translation.translation_service import TranslationService


class ExplodingAITranslator:
    """Fails the test if the AI is ever called."""

    def translate(self, *args, **kwargs):
        raise AssertionError("AI should not be called for fully protected text")


def main():
    service = TranslationService(
        "en_es",
        ai_translator=ExplodingAITranslator(),
        protected_terms=["Create"]
    )

    result = service.translate(" &eCreate")

    assert result["translation"] == " &eCreate"
    assert result["valid"] is True
    assert result["source"] == "fully_protected"

    print("Fully protected text OK")


if __name__ == "__main__":
    main()
