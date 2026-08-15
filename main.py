import argparse
import sys
from pathlib import Path

from translator_app import print_report, translate_file, translate_folder


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Translate Minecraft localization files or folders."
    )
    parser.add_argument("--input", default="test_modpack/lang/en_us.json")
    parser.add_argument("--output", default="test_modpack/lang/es_es.json")
    parser.add_argument("--input-folder", default=None)
    parser.add_argument("--output-folder", default="translated_modpack")
    parser.add_argument(
        "--mods-folder",
        default=None,
        help=(
            "Optional mods folder. Its jar metadata is scanned so mod "
            "display names are never translated."
        )
    )
    parser.add_argument("--source-language", default="en")
    parser.add_argument("--target-language", default="es")
    parser.add_argument("--target-locale", default=None)
    parser.add_argument("--interface-language", default="es")
    parser.add_argument(
        "--ai-provider",
        choices=("mock", "ollama", "openai", "claude", "deepseek"),
        default="mock"
    )
    parser.add_argument("--ai-model", default=None)
    return parser.parse_args()


def main():
    args = parse_args()

    if args.input_folder:
        reports = translate_folder(
            args.input_folder,
            args.output_folder,
            source_language=args.source_language,
            target_language=args.target_language,
            interface_language=args.interface_language,
            ai_provider=args.ai_provider,
            ai_model=args.ai_model,
            target_locale_name=args.target_locale,
            mods_folder=args.mods_folder
        )
        for report in reports:
            print_report(report)
        print(f"Archivos traducidos: {len(reports)}")
        return

    report = translate_file(
        Path(args.input),
        Path(args.output),
        source_language=args.source_language,
        target_language=args.target_language,
        interface_language=args.interface_language,
        ai_provider=args.ai_provider,
        ai_model=args.ai_model,
        mods_folder=args.mods_folder
    )
    print_report(report)


if __name__ == "__main__":
    main()
