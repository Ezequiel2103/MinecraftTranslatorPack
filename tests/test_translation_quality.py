from analyzer.translation_validator import validate_translation_quality


def main():
    cases = {
        "Translation: Presiona %s": "output_label",
        "Texto a traducir\n\nNested text": "explanation_detected",
        "Nested text": "unchanged_translation",
        "[AI] Nested text": "output_label",
        "Presiona %s para abrir la máquina": None,
    }

    for translation, expected_reason in cases.items():
        original = (
            "Nested text"
            if translation in ("Nested text", "[AI] Nested text")
            else "Press %s to open the machine"
        )
        result = validate_translation_quality(
            original,
            translation
        )

        if expected_reason is None:
            assert result["valid"] is True
        else:
            assert result["valid"] is False
            assert result["reason"] == expected_reason

    # A translation into a non-Latin-script target language must not be
    # rejected for containing that language's own script.
    assert validate_translation_quality(
        "Diamond", "Алмаз", target_language="ru"
    )["valid"] is True
    assert validate_translation_quality(
        "Diamond", "钻石", target_language="zh"
    )["valid"] is True
    assert validate_translation_quality(
        "Diamond", "다이아몬드", target_language="ko"
    )["valid"] is True

    # But a Spanish (or any other Latin-script target) translation that
    # comes back in the wrong script must still be rejected.
    result = validate_translation_quality(
        "Diamond", "钻石", target_language="es"
    )
    assert result["valid"] is False
    assert result["reason"] == "wrong_script"

    print("Translation quality OK")


if __name__ == "__main__":
    main()
