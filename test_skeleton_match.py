import json
import shutil
from pathlib import Path

from ai.ai_translator import AITranslator
from translation.translation_memory import memory_path
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_skeletontest"


class FailingAITranslator(AITranslator):
    """Proves the AI is never called when the skeleton match already
    has the answer."""

    def translate(self, *args, **kwargs):
        raise AssertionError("AI should not be called for a skeleton-match hit")

    def translate_batch(self, *args, **kwargs):
        raise AssertionError("AI should not be called for a skeleton-match hit")


def _seed_memory(entries):
    path = memory_path(LANGUAGE_PAIR)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries), encoding="utf-8")


def main():
    memory_dir = Path("translation") / LANGUAGE_PAIR

    try:
        _seed_memory({
            "Craft the &6Mekanism&r Wrench": {
                "translation": "Fabrica la Llave de &6Mekanism&r",
                "type": "manual",
                "source": "manual"
            },
            # A decoy with a differently-shaped translation (different
            # protected-token count) must be skipped, not misapplied.
            "Weird &6Mekanism&r Entry": {
                "translation": "&6Mekanism&r es &6Mekanism&r otra vez",
                "type": "manual",
                "source": "manual"
            }
        })

        protected_terms = ["Mekanism", "Applied Energistics"]
        service = TranslationService(
            LANGUAGE_PAIR,
            ai_translator=FailingAITranslator(),
            protected_terms=protected_terms
        )

        result = service.translate(
            "Craft the &6Applied Energistics&r Wrench",
            source_language="en", target_language="es"
        )

        assert result["valid"] is True, result
        assert result["source"] == "skeleton_match"
        assert result["translation"] == "Fabrica la Llave de &6Applied Energistics&r", result

        # It gets memoized too, so a repeat of the exact same text is a
        # plain memory/run-cache hit next time, not another skeleton scan.
        service.save_new_translations()
        memory = json.loads(memory_path(LANGUAGE_PAIR).read_text(encoding="utf-8"))
        assert memory["Craft the &6Applied Energistics&r Wrench"]["translation"] == (
            "Fabrica la Llave de &6Applied Energistics&r"
        )

        # Text with no protected content at all never enters this tier.
        service2 = TranslationService(
            LANGUAGE_PAIR,
            ai_translator=FailingAITranslator(),
            protected_terms=protected_terms
        )
        no_match = service2._try_skeleton_match("Some completely unrelated plain sentence")
        assert no_match is None

        print("Skeleton match OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
