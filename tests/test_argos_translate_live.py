"""
Live test for the Argos Translate provider — needs the argostranslate
package installed and, the first time it runs for a given language pair,
an internet connection to download that pair's model (a few hundred MB,
cached locally afterward). Not part of run_tests.py for that reason, same
as the other *_live.py tests for real providers.
"""

from ai.ai_translator import ArgosTranslateTranslator


def main():
    translator = ArgosTranslateTranslator()

    result = translator.translate(
        "Kill the Ender Dragon to complete this quest.",
        "en", "es"
    )
    print("Traduccion:", result["translation"])
    assert result["translation"]
    assert result["source"] == "argos_translate"

    print("Argos Translate live test OK")


if __name__ == "__main__":
    main()
