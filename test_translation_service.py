from translation.translation_service import (
    TranslationService
)


service = TranslationService(
    "en_es"
)


tests = [
    "Machine",
    "Diamond",
    "Getting Started",
    "Unknown Text"
]


for text in tests:

    result = service.translate(text)

    print("--------------------------------")

    print(f"Text:        {text}")
    print(f"Translation: {result['translation']}")
    print(f"Source:      {result['source']}")