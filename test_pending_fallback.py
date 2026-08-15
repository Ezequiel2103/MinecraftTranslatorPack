import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ai.ai_translator import AITranslator
from review.pending_manager import save_pending
from translation.translation_service import TranslationService


class AlwaysInvalidAITranslator(AITranslator):
    """Provider used to verify the final retry fallback."""

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
        return {
            "translation": "Broken translation",
            "source": "ai_always_invalid"
        }


def main():
    service = TranslationService(
        "en_es",
        ai_translator=AlwaysInvalidAITranslator()
    )

    original = "Press %s to open %sMachine\\nWelcome!"
    result = service.translate(original)

    assert result["translation"] is None
    assert result["source"] == "ai_failed"
    assert result["valid"] is False
    assert result["validation_reason"] == "placeholder_mismatch"
    assert result["attempts"] == 3

    pending_item = {
        "path": "message",
        "original": original,
        "translation": result["translation"],
        "source": result["source"],
        "attempts": result["attempts"],
        "reason": result["validation_reason"]
    }

    with TemporaryDirectory() as temporary_directory:
        save_pending(
            [pending_item],
            "en_es",
            replace=True,
            review_root=temporary_directory
        )

        pending_path = (
            Path(temporary_directory)
            / "en_es"
            / "pending.json"
        )
        pending = json.loads(
            pending_path.read_text(encoding="utf-8")
        )
        entry = pending[original]

        assert entry["reason"] == "placeholder_mismatch"
        assert entry["source"] == "ai_failed"
        assert entry["attempts"] == 3

    print("Pending fallback OK")


if __name__ == "__main__":
    main()
