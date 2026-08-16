from concurrent.futures import ThreadPoolExecutor, as_completed

from analyzer.translation_validator import validate_translation


def translate_items_concurrently(
    items,
    service,
    source_language="en",
    target_language="es",
    concurrency=4,
    on_progress=None
):
    """
    Translates a list of {"text", "path", "parent_path"} items using the
    given TranslationService, submitting them to a thread pool since each
    call is network-bound. Results are collected into a list matching the
    original item order regardless of which worker finishes first.

    on_progress(completed, total), if given, is called after each item
    finishes.
    """

    total = len(items)
    results = [None] * total

    def translate_item(item):
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

    return results
