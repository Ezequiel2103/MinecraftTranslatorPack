import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


# Entries that belong to the launcher's own bookkeeping (or, for "mods",
# are resolved through the manifest's file list instead) and must not be
# bundled into the "overrides" folder of a CurseForge-importable zip.
CURSEFORGE_EXCLUDED_ENTRIES = {
    "manifest.json",
    "minecraftinstance.json",
    "modlist.html",
    "usercache.json",
    "usernamecache.json",
    "mods",
    "logs",
    "downloads",
    "crash-reports",
    "_translator_backups",
}


def apply_to_modpack_copy(
    instance_path,
    destination_path,
    lang_relative_path,
    output_folder,
    copy_instance=None
):
    """
    Copies a Minecraft instance to destination_path (never touching the
    original instance), then overlays the already translated files from
    output_folder into the matching lang folder inside that copy. Any file
    about to be overwritten is backed up first with a timestamp.

    copy_instance controls whether the full instance is (re)copied:
    - None (default): copy only if destination_path does not exist yet.
    - True: always copy, even if destination_path already exists.
    - False: never copy; destination_path must already exist.
    """

    instance_path = Path(instance_path)
    destination_path = Path(destination_path)
    output_folder = Path(output_folder)

    destination_exists = destination_path.exists()

    if copy_instance is True or (copy_instance is None and not destination_exists):
        shutil.copytree(instance_path, destination_path, dirs_exist_ok=True)
    elif copy_instance is False and not destination_exists:
        raise FileNotFoundError(
            f"destination_path does not exist and copy_instance=False: "
            f"{destination_path}"
        )

    target_lang_dir = destination_path / lang_relative_path
    target_lang_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = destination_path / "_translator_backups" / timestamp

    applied_files = []
    backed_up_files = []

    for translated_file in sorted(output_folder.rglob("*")):
        if not translated_file.is_file():
            continue

        relative = translated_file.relative_to(output_folder)
        target_file = target_lang_dir / relative

        if target_file.exists():
            backup_target = backup_dir / relative
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_file, backup_target)
            backed_up_files.append(str(backup_target))

        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(translated_file, target_file)
        applied_files.append(str(target_file))

    return {
        "destination": str(destination_path),
        "backup_dir": str(backup_dir) if backed_up_files else None,
        "applied_files": applied_files,
        "backed_up_files": backed_up_files
    }


def build_curseforge_import_zip(
    instance_path,
    output_zip_path,
    pack_name=None,
    pack_version="1.0.0",
    manifest_source=None
):
    """
    Packages a Minecraft instance as a CurseForge-importable modpack zip:
    a manifest.json (so CurseForge re-downloads the exact mod versions,
    keeping the zip small) plus an "overrides" folder with everything
    else — config, saves, resource packs, the translated quest files,
    etc.

    Zipping a raw instance folder and importing it directly makes
    CurseForge install the pack from scratch instead, silently dropping
    anything not shipped with the base pack (like FTB Quests' own
    config, which is only generated after the pack has actually been
    played). Reusing the pack's own manifest.json for the mod list, with
    everything else under "overrides", is the format CurseForge expects
    and preserves that generated data.
    """

    instance_path = Path(instance_path)
    output_zip_path = Path(output_zip_path)
    manifest_source = (
        Path(manifest_source)
        if manifest_source
        else instance_path / "manifest.json"
    )

    if not manifest_source.exists():
        raise FileNotFoundError(
            "No se encontró manifest.json para armar el paquete "
            f"(se buscó en: {manifest_source}). Sin él, CurseForge no "
            "sabe qué versión de Minecraft ni qué mods instalar."
        )

    with manifest_source.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    if pack_name:
        manifest["name"] = pack_name

    manifest["version"] = pack_version
    manifest["overrides"] = "overrides"

    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=4)
        )

        for entry in sorted(instance_path.iterdir()):
            if entry.name in CURSEFORGE_EXCLUDED_ENTRIES:
                continue

            if entry.name.startswith("."):
                continue

            # A loose .zip sitting at the instance root is never real
            # modpack content (resource/shader packs live in their own
            # subfolders) — it is almost always a leftover from a
            # previous manual packaging attempt, including this same
            # output file if it lives inside instance_path.
            if entry.is_file() and entry.suffix.lower() == ".zip":
                continue

            if entry.is_file():
                archive.write(entry, f"overrides/{entry.name}")
                continue

            for file_path in sorted(entry.rglob("*")):
                if not file_path.is_file():
                    continue

                arcname = f"overrides/{file_path.relative_to(instance_path)}"
                archive.write(file_path, arcname)

    return str(output_zip_path)
