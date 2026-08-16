import argparse
import sys

from deploy_manager import apply_to_modpack_copy


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Copy a Minecraft instance and overlay already translated "
            "files into it. The original instance is never modified."
        )
    )
    parser.add_argument(
        "--instance",
        required=True,
        help="Path to the original Minecraft instance."
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Path where the instance copy lives (or will be created)."
    )
    parser.add_argument(
        "--lang-relative-path",
        required=True,
        help=(
            "Path to the lang folder relative to the instance root, e.g. "
            "config/ftbquests/quests/lang"
        )
    )
    parser.add_argument(
        "--output-folder",
        required=True,
        help="Folder with the already translated files (from main.py)."
    )
    parser.add_argument(
        "--force-recopy",
        action="store_true",
        help="Re-copy the whole instance even if destination already exists."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    result = apply_to_modpack_copy(
        args.instance,
        args.destination,
        args.lang_relative_path,
        args.output_folder,
        copy_instance=True if args.force_recopy else None
    )

    print(f"✅ Copia lista en: {result['destination']}")
    print(f"📄 Archivos aplicados: {len(result['applied_files'])}")
    for path in result["applied_files"]:
        print(f"  {path}")

    if result["backup_dir"]:
        print(f"🗄️ Respaldo de archivos reemplazados en: {result['backup_dir']}")


if __name__ == "__main__":
    main()
