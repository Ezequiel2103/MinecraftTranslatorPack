import json
from pathlib import Path


def templates_path(language_pair="en_es"):
    return Path("translation") / language_pair / "templates.json"


def load_templates(language_pair="en_es"):
    """
    A template is a fixed prefix/suffix pair known to always translate
    the same way regardless of what sits between them (e.g. "&eKill&f: "
    always becomes "&eMatar&f: "), so only the variable middle part needs
    an actual translation lookup. Keep this file to patterns that are
    truly invariant — no gender/number agreement with the variable part —
    since the pieces are just concatenated back together with no grammar
    check beyond placeholder preservation.
    """

    path = templates_path(language_pair)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
