import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Running from a PyInstaller-built exe: bundled files live under the
    # extracted _MEIPASS folder instead of next to this script.
    BASE_DIR = Path(sys._MEIPASS)
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
