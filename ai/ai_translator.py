class AITranslator:
    """
    Base interface for AI translation providers.
    """

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        raise NotImplementedError(
            "AI translation provider not configured."
        )
class MockAITranslator(AITranslator):
    """
    Temporary translator used for testing.
    """

    def translate(
        self,
        text,
        source_language,
        target_language,
        terminology=None,
        context=None
    ):
        return {
            "translation": f"[AI] {text}",
            "source": "ai_mock"
        }