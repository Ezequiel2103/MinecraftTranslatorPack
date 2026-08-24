import json
import tempfile
import zipfile
from pathlib import Path

from analyzer.mod_scanner import scan_mod_names


NEOFORGE_TOML = """
modLoader="javafml"
loaderVersion="[2,)"
license="MIT"

[[mods]]
modId="create"
version="6.0.4"
displayName="Create"
"""

FABRIC_JSON = json.dumps({"schemaVersion": 1, "id": "sodium", "name": "Sodium"})


def main():
    with tempfile.TemporaryDirectory() as tmp:
        mods_folder = Path(tmp)

        with zipfile.ZipFile(mods_folder / "create.jar", "w") as archive:
            archive.writestr("META-INF/neoforge.mods.toml", NEOFORGE_TOML)

        with zipfile.ZipFile(mods_folder / "sodium.jar", "w") as archive:
            archive.writestr("fabric.mod.json", FABRIC_JSON)

        with zipfile.ZipFile(mods_folder / "unknown.jar", "w") as archive:
            archive.writestr("README.txt", "no mod metadata here")

        names, unresolved = scan_mod_names(mods_folder)

        assert names == ["Create", "Sodium"]
        assert unresolved == ["unknown.jar"]

    print("Mod scanner OK")


if __name__ == "__main__":
    main()
