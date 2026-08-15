from translation.translation_memory import translate_with_memory


def main():
    english_to_spanish = translate_with_memory(
        [{"text": "Diamond", "path": "item"}],
        "en_es"
    )
    english_to_portuguese = translate_with_memory(
        [{"text": "Diamond", "path": "item"}],
        "en_pt"
    )

    assert english_to_spanish[0]["translation"] == "Diamante"
    assert english_to_portuguese[0]["translation"] is None

    print("Language-pair memory OK")


if __name__ == "__main__":
    main()
