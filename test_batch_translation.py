import shutil
import threading
from pathlib import Path

from ai.ai_translator import AITranslator, QuotaExceededError
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_batchtest"

TRANSLATIONS = {
    "Diamond Ore": "Mineral de Diamante",
    "Iron Ore": "Mineral de Hierro",
    "Gold Ore": "Mineral de Oro",
    "Dropped Text": "Texto Perdido",
    "Press %s to open": "Presiona %s para abrir",
    # protect_text() swaps %s for this token before either translator
    # method ever sees the text.
    "Press __MTP_PROTECTED_0__ to open": "Presiona __MTP_PROTECTED_0__ para abrir",
    "A": "Ah",
    "B": "Be",
    "C": "Ce",
    "D": "De",
    "E": "Eh",
    "Brand New Item": "Objeto Nuevo",
    "First": "Primero",
    "Second": "Segundo"
}


class FakeBatchAITranslator(AITranslator):
    """
    Simulates a real batch-capable provider: one call answers many ids at
    once. `drop_ids` are silently missing from the response (as if the AI
    forgot them); `bad_ids` come back with a placeholder mismatch.
    """

    def __init__(self, drop_ids=(), bad_ids=()):
        self.drop_ids = set(drop_ids)
        self.bad_ids = set(bad_ids)
        self.batch_calls = []
        self.single_calls = []

    def translate(self, text, source_language, target_language,
                  terminology=None, context=None,
                  previous_translation=None, validation_error=None):
        self.single_calls.append(text)
        return {"translation": TRANSLATIONS[text], "source": "fake_single"}

    def translate_batch(self, texts_by_id, source_language, target_language,
                         terminology=None, context=None):
        self.batch_calls.append(dict(texts_by_id))
        results = {}
        for item_id, text in texts_by_id.items():
            if item_id in self.drop_ids:
                continue
            if item_id in self.bad_ids:
                results[item_id] = {"translation": "traduccion rota sin el placeholder", "source": "fake_batch"}
            else:
                results[item_id] = {"translation": TRANSLATIONS[text], "source": "fake_batch"}
        return results


class QuotaBatchTranslator(AITranslator):
    def translate(self, *args, **kwargs):
        raise AssertionError("single translate should not be called")

    def translate_batch(self, *args, **kwargs):
        raise QuotaExceededError("limite alcanzado")


def _items(*texts):
    return [{"text": text, "path": f"path/{i}"} for i, text in enumerate(texts)]


def main():
    memory_dir = Path("translation") / LANGUAGE_PAIR

    try:
        # 1. Plain batch success: one call handles everything.
        fake = FakeBatchAITranslator()
        service = TranslationService(LANGUAGE_PAIR, ai_translator=fake)

        results = service.translate_batch(
            _items("Diamond Ore", "Iron Ore", "Gold Ore"),
            source_language="en", target_language="es"
        )

        assert len(fake.batch_calls) == 1, fake.batch_calls
        assert len(fake.batch_calls[0]) == 3
        assert [r["translation"] for r in results] == [
            "Mineral de Diamante", "Mineral de Hierro", "Mineral de Oro"
        ]
        assert all(r["valid"] for r in results)
        assert fake.single_calls == []

        # 2. A missing id and a placeholder-broken id both fall back to
        # the individual retry path instead of being silently accepted
        # or lost.
        fake2 = FakeBatchAITranslator(drop_ids={"0"}, bad_ids={"1"})
        service2 = TranslationService(LANGUAGE_PAIR, ai_translator=fake2)

        results2 = service2.translate_batch(
            _items("Dropped Text", "Press %s to open"),
            source_language="en", target_language="es"
        )

        assert results2[0]["translation"] == "Texto Perdido"
        assert results2[0]["source"] == "fake_single"
        # The bad batch answer dropped the %s placeholder -> falls back,
        # and the single-item mock always echoes back a valid answer.
        assert results2[1]["translation"] == "Presiona %s para abrir"
        # single_calls holds what the translator actually saw, i.e. the
        # placeholder-protected form for the second one.
        assert set(fake2.single_calls) == {
            "Dropped Text", "Press __MTP_PROTECTED_0__ to open"
        }

        # 3. Chunking respects batch_size.
        fake3 = FakeBatchAITranslator()
        service3 = TranslationService(LANGUAGE_PAIR, ai_translator=fake3)
        service3.translate_batch(
            _items("A", "B", "C", "D", "E"),
            source_language="en", target_language="es",
            batch_size=2
        )
        assert len(fake3.batch_calls) == 3, fake3.batch_calls
        assert [len(call) for call in fake3.batch_calls] == [2, 2, 1]

        # 4. A quota error during the batch call stops the run and marks
        # remaining chunks as cancelled instead of hammering the API.
        cancel_event = threading.Event()
        service4 = TranslationService(
            LANGUAGE_PAIR, ai_translator=QuotaBatchTranslator(),
            cancel_event=cancel_event
        )
        results4 = service4.translate_batch(
            _items("First", "Second"),
            source_language="en", target_language="es",
            batch_size=1
        )
        assert results4[0]["source"] == "quota_exceeded"
        assert cancel_event.is_set()
        # Second chunk never even attempted the API once cancel_event was set.
        assert results4[1]["source"] in ("quota_exceeded", "cancelled")

        # 5. Items already resolvable from memory never reach the AI at all.
        fake5 = FakeBatchAITranslator()
        service5 = TranslationService(LANGUAGE_PAIR, ai_translator=fake5)
        service5.translate("Diamond Ore", source_language="en", target_language="es")
        service5.save_new_translations()

        results5 = service5.translate_batch(
            _items("Diamond Ore", "Brand New Item"),
            source_language="en", target_language="es"
        )
        # save_new_translations() flushed and cleared the in-run cache, so
        # this now comes back from disk memory instead — either way, no
        # AI call was needed for it.
        assert results5[0]["source"] == "memory"
        assert len(fake5.batch_calls) == 1
        assert list(fake5.batch_calls[0].values()) == ["Brand New Item"]

        print("Batch translation OK")

    finally:
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
