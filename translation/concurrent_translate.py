from concurrent.futures import ThreadPoolExecutor, as_completed

from analyzer.translation_validator import validate_translation


DEFAULT_BATCH_SIZE = 15


def translate_items_concurrently(
    items,
    service,
    source_language="en",
    target_language="es",
    concurrency=4,
    batch_size=DEFAULT_BATCH_SIZE,
    on_progress=None,
    cancel_event=None,
    resume_event=None,
    flush_callback=None,
    flush_every=20
):
    """
    Translates a list of {"text", "path", "parent_path"} items using the
    given TranslationService. Items are grouped into chunks of up to
    batch_size and each chunk is submitted to a thread pool as one unit
    of work (service.translate_batch), so up to `concurrency` chunks are
    in flight at once — the fixed cost of an AI provider's instructions
    is paid once per chunk instead of once per item. Results are
    collected into a list matching the original item order regardless of
    which worker finishes first or how items were grouped.

    on_progress(completed, total), if given, is called once per item as
    its chunk finishes (so calls arrive in bursts of up to batch_size
    rather than one at a time, but the total call count is unchanged).

    cancel_event (threading.Event): if set before a worker starts a
    chunk, every item in that chunk is skipped (left untranslated)
    instead of calling the AI. A chunk already in flight is allowed to
    finish rather than being killed mid-request.

    resume_event (threading.Event): workers block on it before starting
    each chunk, so clearing it pauses new work without losing anything
    already done; setting it again resumes.

    flush_callback, if given, is called once at least flush_every items
    have completed since the last flush (and once more at the end) so
    progress already paid for survives a crash, a cancellation, or
    running out of API credits instead of only being saved once the
    whole batch finishes.
    """

    total = len(items)
    results = [None] * total

    def is_cancelled():
        return cancel_event is not None and cancel_event.is_set()

    chunks = [
        list(enumerate(items))[start:start + batch_size]
        for start in range(0, total, max(1, batch_size))
    ]

    def translate_chunk(chunk):
        if is_cancelled():
            return [(index, _skipped_result(item)) for index, item in chunk]

        if resume_event is not None:
            resume_event.wait()

        if is_cancelled():
            return [(index, _skipped_result(item)) for index, item in chunk]

        chunk_items = [item for _, item in chunk]
        batch_results = service.translate_batch(
            chunk_items,
            source_language=source_language,
            target_language=target_language,
            batch_size=batch_size
        )

        paired = []

        for (index, item), result in zip(chunk, batch_results):
            validation = validate_translation(
                item["text"],
                result["translation"]
            )
            paired.append((index, {
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
            }))

        return paired

    completed = 0
    flushed_through = 0

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = [executor.submit(translate_chunk, chunk) for chunk in chunks]

        for future in as_completed(futures):
            for index, result in future.result():
                results[index] = result
                completed += 1

                if on_progress:
                    on_progress(completed, total)

            if flush_callback and completed - flushed_through >= flush_every:
                flush_callback()
                flushed_through = completed

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
