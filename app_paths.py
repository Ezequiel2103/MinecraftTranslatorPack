import os
import sys
from pathlib import Path


def resource_dir():
    """
    Base folder for files shipped WITH the app -- curated, read-only at
    runtime (hand-written translation templates/terminology).

    Running from source, that's just the project root. Packaged as a
    .exe, PyInstaller extracts bundled data next to the executable
    (sys._MEIPASS at runtime), not the project folder the app was
    originally built from.
    """

    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parent


def data_dir():
    """
    Base folder for everything the app accumulates while running and
    reads back later: translation memory, the mod glossary/cache,
    settings, the pending-review queue, usage tracking.

    Running from source, that's the current folder, same as always --
    every existing dev/test workflow is unaffected.

    Packaged as a .exe, writing next to the program itself means a
    rebuild or reinstall wipes it out (PyInstaller recreates that whole
    folder from scratch each time), and a Program Files-style install
    location may not even be writable by a regular user. Windows' own
    per-user data folder (%LOCALAPPDATA%) survives both of those and is
    where desktop apps are expected to keep this kind of thing.
    """

    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "MinecraftTranslatorPack"
        return Path.home() / "MinecraftTranslatorPack"

    return Path(".")
