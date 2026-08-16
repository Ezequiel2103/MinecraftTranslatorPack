import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import webview

from gui.api import Api


def main():
    api = Api()
    web_dir = Path(__file__).resolve().parent / "web"

    window = webview.create_window(
        "Traductor de Modpacks",
        str(web_dir / "index.html"),
        js_api=api,
        width=1000,
        height=700,
        min_size=(820, 600),
        frameless=True,
        easy_drag=False,
        background_color="#1b1712"
    )

    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
