from concurrent.futures import ThreadPoolExecutor, as_completed

from analyzer.translation_validator import validate_translation


def translate_items_concurrently(
    items,
    service,
    source_language="en",
    target_language="es",
    concurrency=4,
    on_progress=None,
    cancel_event=None,
    resume_event=None,
    flush_callback=None,
    flush_every=20
):
    """
    Translates a list of {"text", "path", "parent_path"} items using the
    given TranslationService, submitting them to a thread pool since each
    call is network-bound. Results are collected into a list matching the
    original item order regardless of which worker finishes first.

    on_progress(completed, total), if given, is called after each item
    finishes.

    cancel_event (threading.Event): if set before a worker starts an item,
    that item is skipped (left untranslated) instead of calling the AI.
    Already-running calls are allowed to finish rather than being killed
    mid-request.

    resume_event (threading.Event): workers block on it before starting
    each item, so clearing it pauses new work without losing anything
    already done; setting it again resumes.

    flush_callback, if given, is called every flush_every completed items
    (and once more at the end) so progress already paid for survives a
    crash, a cancellation, or running out of API credits instead of only
    being saved once the whole batch finishes.
    """

    total = len(items)
    results = [None] * total

    def is_cancelled():
        return cancel_event is not None and cancel_event.is_set()

    def translate_item(item):
        if is_cancelled():
            return _skipped_result(item)

        if resume_event is not None:
            resume_event.wait()

        if is_cancelled():
            return _skipped_result(item)

        result = service.translate(
            item["text"],
            item["path"],
            source_language=source_language,
            target_language=target_language,
            context=item.get("parent_path")
        )
        validation = validate_translation(
            item["text"],
            result["translation"]
        )
        return {
            "path": item["path"],
            "original": item["text"],
            "translation": result["translation"],
            "source": result["source"],
            "valid": result["valid"] and validation["valid"],
            "validation_reason": (
                result.get("validation_reason")
                or validation["reason"]
            ),
            "attempts": result.get("attempts", 0)
        }

    completed = 0

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        future_to_index = {
            executor.submit(translate_item, item): index
            for index, item in enumerate(items)
        }

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            results[index] = future.result()
            completed += 1

            if on_progress:
                on_progress(completed, total)

            if flush_callback and completed % flush_every == 0:
                flush_callback()

    if flush_callback:
        flush_callback()

    return results


def _skipped_result(item):
    return {
        "path": item["path"],
        "original": item["text"],
        "translation": None,
        "source": "cancelled",
        "valid": False,
        "validation_reason": "cancelled",
        "attempts": 0
    }
