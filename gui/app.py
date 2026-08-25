import os
import sys
from pathlib import Path

# A windowed .exe (no visible console) has no real console attached, so
# Windows hands Python a stdout/stderr that either doesn't exist or falls
# back to the system's legacy codepage (cp1252 here) instead of UTF-8.
# Anything -- our own code or a dependency's (Argos Translate's install/
# logging path in particular) -- that tries to print an emoji or other
# non-cp1252 character then crashes the whole run with a
# UnicodeEncodeError. Force UTF-8 (or a harmless discard stream when
# there's truly no stream at all) before anything else runs.
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name)
    if _stream is None:
        setattr(sys, _stream_name, open(os.devnull, "w", encoding="utf-8"))
    elif hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

def _unblock_bundled_dotnet_files(base_dir):
    """
    Windows tags every file extracted from a zip that was downloaded
    off the internet with a hidden "Mark of the Web" marker, and .NET
    refuses to load an assembly carrying one -- which is exactly what
    breaks pythonnet's Python.Runtime.dll the moment someone downloads
    a release, unzips it and runs the exe, with a cryptic "Failed to
    resolve Python.Runtime.Loader.Initialize" crash before the window
    ever opens. It only reproduces on a machine that actually downloaded
    the zip (unblocking isn't needed running from source, or from a
    build that was never zipped), which is why this can pass every
    local test and still break for every single person you send it to.
    Strip the marker from the handful of files pythonnet needs before
    anything gets a chance to load them.
    """

    for subfolder in ("pythonnet", "clr_loader"):
        folder = base_dir / subfolder
        if not folder.is_dir():
            continue

        for path in folder.rglob("*"):
            if path.is_file():
                try:
                    os.remove(f"{path}:Zone.Identifier")
                except OSError:
                    pass


if getattr(sys, "frozen", False):
    # Running from a PyInstaller-built exe: bundled files live under the
    # extracted _MEIPASS folder instead of next to this script.
    BASE_DIR = Path(sys._MEIPASS)
    _unblock_bundled_dotnet_files(BASE_DIR)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE_DIR))

import webview

from gui.api import Api


def main():
    api = Api()
    web_dir = BASE_DIR / "gui" / "web"

    window = webview.create_window(
        "Traductor de Modpacks",
        str(web_dir / "index.html"),
        js_api=api,
        width=1000,
        height=700,
        min_size=(820, 600),
        frameless=True,
        easy_drag=True,
        background_color="#1b1712"
    )

    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
