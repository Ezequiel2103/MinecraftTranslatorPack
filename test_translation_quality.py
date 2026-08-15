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

    print("Translation quality OK")


if __name__ == "__main__":
    main()
