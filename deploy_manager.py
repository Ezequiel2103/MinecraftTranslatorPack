import shutil
from datetime import datetime
from pathlib import Path


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
