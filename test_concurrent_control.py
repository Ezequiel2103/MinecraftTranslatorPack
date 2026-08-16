import threading
import time

from translation.concurrent_translate import translate_items_concurrently
from translation.translation_service import TranslationService
from ai.ai_translator import AITranslator


class CountingSlowTranslator(AITranslator):
    def __init__(self, delay=0.02):
        self.delay = delay
        self.calls = 0
        self.lock = threading.Lock()

    def translate(self, text, source_language, target_language, terminology=None,
                  context=None, previous_translation=None, validation_error=None):
        with self.lock:
            self.calls += 1
        time.sleep(self.delay)
        return {"translation": f"T-{text}", "source": "counting_slow_mock"}


def make_items(count):
    return [{"text": f"item{i}", "path": f"path{i}"} for i in range(count)]


def test_flush_callback_runs_periodically():
    translator = CountingSlowTranslator(delay=0.001)
    service = TranslationService("en_es_concurrenttest", ai_translator=translator)
    flush_calls = []

    translate_items_concurrently(
        make_items(20),
        service,
        concurrency=3,
        flush_callback=lambda: flush_calls.append(1),
        flush_every=7
    )

    # At least the periodic flushes inside the loop plus the guaranteed
    # final flush after it.
    assert len(flush_calls) >= 3


def test_cancel_stops_remaining_work():
    translator = CountingSlowTranslator(delay=0.03)
    service = TranslationService("en_es_concurrenttest", ai_translator=translator)
    cancel_event = threading.Event()

    def on_progress(completed, total):
        if completed == 2:
            cancel_event.set()

    items = make_items(10)
    results = translate_items_concurrently(
        items,
        service,
        concurrency=2,
        on_progress=on_progress,
        cancel_event=cancel_event
    )

    assert len(results) == 10
    cancelled = [r for r in results if r["source"] == "cancelled"]
    real_attempts = [r for r in results if r["source"] != "cancelled"]

    assert len(cancelled) > 0
    assert len(real_attempts) + len(cancelled) == 10
    # Not every item should have reached the AI once cancellation kicked in.
    assert translator.calls < 10
    for result in cancelled:
        assert result["valid"] is False
        assert result["translation"] is None


def test_pause_blocks_until_resumed():
    translator = CountingSlowTranslator(delay=0.001)
    service = TranslationService("en_es_concurrenttest", ai_translator=translator)
    resume_event = threading.Event()  # starts cleared: paused

    results_holder = {}

    def run():
        results_holder["results"] = translate_items_concurrently(
            make_items(5),
            service,
            concurrency=2,
            resume_event=resume_event
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    time.sleep(0.1)
    assert "results" not in results_holder, "work should not finish while paused"
    assert translator.calls == 0, "no AI calls should happen while paused"

    resume_event.set()
    thread.join(timeout=5)

    assert "results" in results_holder
    assert len(results_holder["results"]) == 5
    assert translator.calls == 5


def main():
    test_flush_callback_runs_periodically()
    test_cancel_stops_remaining_work()
    test_pause_blocks_until_resumed()
    print("Concurrent control (pause/cancel/flush) OK")


if __name__ == "__main__":
    main()
