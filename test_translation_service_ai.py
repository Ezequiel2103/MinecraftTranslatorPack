from translation.translation_service import (
    TranslationService
)


service = TranslationService(
    "en_es"
)


tests = [
    "Diamond",
    "Craft your first machine."
]


for text in tests:

    result = service.translate(
        text
    )

    print("--------------------------------")
    print(f"Text:        {text}")
    print(
        f"Translation: "
        f"{result['translation']}"
    )
    print(
        f"Source:      "
        f"{result['source']}"
    )
