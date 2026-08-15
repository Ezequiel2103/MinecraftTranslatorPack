from translation.terminology_manager import (
    load_terminology,
    find_term
)

from translation.translation_memory import (
    translate_with_memory
)


class TranslationService:

    def __init__(self, language_pair):

        self.language_pair = language_pair

        self.terminology = load_terminology(
            language_pair
        )

    def translate(self, text, path=""):

        # 1. Terminology

        terminology_translation = find_term(
            text,
            self.terminology
        )

        if terminology_translation:

            return {
                "translation": terminology_translation,
                "source": "terminology"
            }

        # 2. Translation memory

        memory_results = translate_with_memory([
            {
                "text": text,
                "path": path
            }
        ])

        if memory_results:

            memory_translation = (
                memory_results[0]["translation"]
            )

            if memory_translation:

                return {
                    "translation": memory_translation,
                    "source": "memory"
                }

        # 3. Not found

        return {
            "translation": None,
            "source": "unknown"
        }