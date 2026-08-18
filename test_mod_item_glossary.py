import json
import shutil
from pathlib import Path

from ai.ai_translator import AITranslator
from translation.mod_lang_cache import (
    build_mod_item_glossary,
    build_text_glossary,
    glossary_path,
    merge_into_item_glossary
)
from translation.translation_service import TranslationService


LANGUAGE_PAIR = "en_es_glossarytest"


class FailingAITranslator(AITranslator):
    """Used to prove the AI is never called when the glossary already
    has the answer."""

    def translate(self, *args, **kwargs):
        raise AssertionError("AI should not be called for a glossary hit")


def _merge_mod(lang_en, lang_es):
    merge_into_item_glossary(build_text_glossary(lang_en, lang_es), LANGUAGE_PAIR)


def main():
    cache_dir = Path("mod_lang_cache") / LANGUAGE_PAIR
    memory_dir = Path("translation") / LANGUAGE_PAIR

    try:
        _merge_mod(
            {"block.mekanism.energy_cube": "Energy Cube"},
            {"block.mekanism.energy_cube": "Cubo de Energía"}
        )
        # Identical en/es text must not be included (nothing to reuse).
        _merge_mod(
            {"item.sameword.thing": "AE2"},
            {"item.sameword.thing": "AE2"}
        )
        # Two mods that disagree on the translation of the same English
        # text: neither answer should be trusted, so it must be excluded
        # rather than silently picking whichever was merged first.
        _merge_mod(
            {"item.alphamod.core": "Energy Core"},
            {"item.alphamod.core": "Núcleo de Energía"}
        )
        _merge_mod(
            {"item.zetamod.core": "Energy Core"},
            {"item.zetamod.core": "Núcleo Energético"}
        )
        # A later mod that happens to agree with one of the two earlier
        # conflicting values must NOT silently resurrect the entry.
        _merge_mod(
            {"item.thirdmod.core": "Energy Core"},
            {"item.thirdmod.core": "Núcleo de Energía"}
        )

        glossary = build_mod_item_glossary(LANGUAGE_PAIR)
        assert glossary["Energy Cube"] == "Cubo de Energía"
        assert "AE2" not in glossary
        assert "Energy Core" not in glossary

        # A corrupted glossary file must be treated as empty, not crash.
        glossary_path(LANGUAGE_PAIR).write_text("{truncated", encoding="utf-8")
        assert build_mod_item_glossary(LANGUAGE_PAIR) == {}
        glossary_path(LANGUAGE_PAIR).unlink()

        # Re-merge for the rest of the test (the corruption check above
        # wiped the file).
        _merge_mod(
            {"block.mekanism.energy_cube": "Energy Cube"},
            {"block.mekanism.energy_cube": "Cubo de Energía"}
        )
        glossary = build_mod_item_glossary(LANGUAGE_PAIR)

        service = TranslationService(
            LANGUAGE_PAIR,
            ai_translator=FailingAITranslator(),
            mod_item_glossary=glossary
        )

        result = service.translate(
            "Energy Cube",
            source_language="en",
            target_language="es"
        )
        assert result["translation"] == "Cubo de Energía"
        assert result["source"] == "mod_glossary"
        assert result["valid"]

        service.save_new_translations()
        memory = json.loads((memory_dir / "memory.json").read_text(encoding="utf-8"))
        assert memory["Energy Cube"]["translation"] == "Cubo de Energía"

        print("Mod item glossary OK")

    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)
        shutil.rmtree(memory_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
