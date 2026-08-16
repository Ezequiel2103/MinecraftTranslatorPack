import argparse
import sys
from pathlib import Path

from deploy_manager import apply_to_modpack_copy, build_curseforge_import_zip


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
    parser.add_argument(
        "--build-zip",
        default=None,
        help=(
            "Optional output .zip path. Packages the result in the "
            "manifest.json + overrides format CurseForge expects for "
            "importing, so mods, config and the translated quests all "
            "come through correctly instead of a fresh reinstall."
        )
    )
    parser.add_argument(
        "--pack-name",
        default=None,
        help="Name to use inside the zip's manifest.json (--build-zip only)."
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

    if args.build_zip:
        zip_path = build_curseforge_import_zip(
            result["destination"],
            args.build_zip,
            pack_name=args.pack_name,
            manifest_source=Path(args.instance) / "manifest.json"
        )
        print(f"📦 Paquete para importar en CurseForge: {zip_path}")


if __name__ == "__main__":
    main()
