import json
import shutil
from pathlib import Path

from review.ai_review import ai_review_pending
from review.pending_manager import save_pending
from translation.translation_memory import load_memory


LANGUAGE_PAIR = "en_es_aitest"


class FakeJudgeTranslator:
    def __init__(self, verdicts):
        self.verdicts = verdicts
        self.asked = []

    def ask(self, prompt):
        self.asked.append(prompt)

        for text, verdict in self.verdicts.items():
            if text in prompt:
                return verdict

        raise AssertionError("Unexpected prompt: " + prompt)


def main():
    review_dir = Path("review") / LANGUAGE_PAIR
    memory_dir = Path("translation") / LANGUAGE_PAIR

    try:
        save_pending(
            [
                {
                    "path": "chapter.title",
                    "original": "Tutorial",
                    "reason": "unchanged_translation"
                },
                {
                    "path": "quest.title",
                    "original": "Fix the Machine",
                    "reason": "placeholder_mismatch"
                },
                {
                    "path": "quest.title2",
                    "original": "Weird Untranslated Phrase",
                    "reason": "unchanged_translation"
                }
            ],
            LANGUAGE_PAIR,
            replace=True
        )

        translator = FakeJudgeTranslator({
            "Tutorial": "CORRECT",
            "Weird Untranslated Phrase": "INCORRECT"
        })

        result = ai_review_pending(LANGUAGE_PAIR, translator)

        assert result["approved"] == ["Tutorial"]
        assert result["kept"] == ["Weird Untranslated Phrase"]
        assert len(translator.asked) == 2

        pending = json.loads(
            (review_dir / "pending.json").read_text(encoding="utf-8")
        )
        assert "Tutorial" not in pending
        assert "Weird Untranslated Phrase" in pending
        assert "Fix the Machine" in pending

        memory = load_memory(LANGUAGE_PAIR)
        assert memory["Tutorial"]["translation"] == "Tutorial"

        print("AI review OK")

    finally:
        shutil.rmtree(review_dir, ignore_errors=True)
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
