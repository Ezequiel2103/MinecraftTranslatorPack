import json
import tomllib
import zipfile
from pathlib import Path


METADATA_CANDIDATES = (
    "META-INF/neoforge.mods.toml",
    "META-INF/mods.toml",
)


def _names_from_toml(raw_bytes):
    data = tomllib.loads(raw_bytes.decode("utf-8", errors="replace"))
    names = []

    for mod in data.get("mods", []):
        display = mod.get("displayName") or mod.get("modId")

        if display:
            names.append(display)

    return names


def _names_from_fabric_json(raw_bytes):
    data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    display = data.get("name") or data.get("id")

    return [display] if display else []


def _names_from_quilt_json(raw_bytes):
    data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    metadata = data.get("quilt_loader", {}).get("metadata", {})
    display = metadata.get("name") or data.get("quilt_loader", {}).get("id")

    return [display] if display else []


def scan_mod_names(mods_folder):
    """
    Reads every .jar in a Minecraft mods folder and extracts each mod's
    display name from its own metadata (Forge/NeoForge mods.toml,
    Fabric or Quilt json), so it can later be protected from translation.

    Returns a (names, unresolved) tuple: a sorted list of unique display
    names and a list of jar filenames whose metadata could not be read.
    """

    mods_folder = Path(mods_folder)
    names = set()
    unresolved = []

    for jar_path in sorted(mods_folder.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar_path) as archive:
                entries = archive.namelist()

                toml_entry = next(
                    (
                        candidate
                        for candidate in METADATA_CANDIDATES
                        if candidate in entries
                    ),
                    None
                )

                if toml_entry:
                    names.update(_names_from_toml(archive.read(toml_entry)))
                    continue

                if "fabric.mod.json" in entries:
                    names.update(
                        _names_from_fabric_json(
                            archive.read("fabric.mod.json")
                        )
                    )
                    continue

                if "quilt.mod.json" in entries:
                    names.update(
                        _names_from_quilt_json(
                            archive.read("quilt.mod.json")
                        )
                    )
                    continue

                unresolved.append(jar_path.name)

        except (zipfile.BadZipFile, KeyError, ValueError, UnicodeDecodeError):
            unresolved.append(jar_path.name)

    return sorted(names), unresolved
