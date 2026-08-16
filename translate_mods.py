import argparse
import sys

from mod_lang_translator import translate_mod_lang_files


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Translate every mod's own text (items, blocks, GUI, "
            "tooltips) into a resource pack, without touching any mod "
            "jar. Mods that already ship a translation for the target "
            "language are left untouched, and translations are cached "
            "per mod so a future modpack reusing the same mod skips the "
            "AI entirely."
        )
    )
    parser.add_argument(
        "--mods-folder",
        required=True,
        help="Path to the modpack's mods folder."
    )
    parser.add_argument(
        "--output-resourcepack",
        required=True,
        help="Folder where the resource pack will be generated."
    )
    parser.add_argument("--source-language", default="en")
    parser.add_argument("--target-language", default="es")
    parser.add_argument(
        "--ai-provider",
        choices=("mock", "ollama", "openai", "claude", "deepseek"),
        default="mock"
    )
    parser.add_argument("--ai-model", default=None)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="How many texts to translate at the same time (default: 4)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    stats = translate_mod_lang_files(
        args.mods_folder,
        args.output_resourcepack,
        source_language=args.source_language,
        target_language=args.target_language,
        ai_provider=args.ai_provider,
        ai_model=args.ai_model,
        concurrency=args.concurrency
    )

    print(f"✅ Resource pack generado en: {args.output_resourcepack}")
    print(f"📦 Mods incluidos: {len(stats['mods'])}")
    print(
        f"🟢 Ya tenían traducción propia (sin tocar): "
        f"{stats['already_translated_by_mod']}"
    )
    print(f"♻️ Reutilizados desde el caché: {stats['reused_from_cache']}")
    print(f"🌎 Traducidos ahora: {stats['translated_fresh']}")
    print(f"❓ Pendientes de revisión manual: {stats['pending_items']}")


if __name__ == "__main__":
    main()
