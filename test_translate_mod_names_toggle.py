from translation.protected_terms_manager import load_protected_terms
from translator_app import resolve_protected_terms


def main():
    saved_terms = load_protected_terms("en_es")
    assert saved_terms, "expected translation/en_es/protected_terms.json to have entries"

    protected = resolve_protected_terms(
        "en_es",
        mods_folder=None,
        translate_mod_names=False
    )
    assert protected == saved_terms

    translated = resolve_protected_terms(
        "en_es",
        mods_folder=None,
        translate_mod_names=True
    )
    assert translated == []

    print("Translate mod names toggle OK")


if __name__ == "__main__":
    main()
