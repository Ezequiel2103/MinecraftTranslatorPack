from translation.translation_service import (
    _diff_single_word,
    _infer_word_translations
)


def main():
    # _diff_single_word: the core building block.

    # Clean single-word swap -> both sides returned.
    assert _diff_single_word("Lingote de Hierro", "Lingote de Cobre") == (
        "Hierro", "Cobre"
    )

    # More than one differing word -> can't isolate either safely.
    assert _diff_single_word("Lingote de Hierro", "Placa de Cobre") == (
        None, None
    )

    # Different word count (e.g. an article added) -> rejected rather
    # than guessed at.
    assert _diff_single_word("Lingote de Hierro", "El Lingote de Hierro") == (
        None, None
    )

    # Identical strings -> nothing to isolate.
    assert _diff_single_word("Lingote de Hierro", "Lingote de Hierro") == (
        None, None
    )

    # _infer_word_translations: minimal-pair mining across many entries.

    pairs = [
        ("Iron Ingot", "Lingote de Hierro"),
        ("Copper Ingot", "Lingote de Cobre"),
        ("Iron Ore", "Mineral de Hierro"),
        ("Copper Ore", "Mineral de Cobre"),
        # Too short to ever pair against anything -> ignored, not a crash.
        ("Stick", "Palo"),
    ]

    inferred = _infer_word_translations(pairs)

    assert inferred["iron"] == "Hierro", inferred
    assert inferred["copper"] == "Cobre", inferred
    assert inferred["ingot"] == "Lingote", inferred
    assert inferred["ore"] == "Mineral", inferred

    # Conflicting evidence for the same English word must drop it
    # instead of guessing -- here "Plate" is implied to be "Placa" by
    # one pair ("Iron Plate"/"Iron Sheet") and "Losa" by another
    # ("Gold Plate"/"Gold Ingot"), so neither guess is trustworthy.
    conflicting_pairs = [
        ("Iron Plate", "Placa de Hierro"),
        ("Iron Sheet", "Chapa de Hierro"),
        ("Gold Plate", "Losa de Oro"),
        ("Gold Ingot", "Lingote de Oro"),
    ]

    inferred2 = _infer_word_translations(conflicting_pairs)

    assert "plate" not in inferred2, inferred2
    # "Sheet" and "Ingot" each only ever came from one clean pair, so
    # the Plate conflict doesn't take them down too.
    assert inferred2["sheet"] == "Chapa", inferred2
    assert inferred2["ingot"] == "Lingote", inferred2

    print("Word inference OK")


if __name__ == "__main__":
    main()
