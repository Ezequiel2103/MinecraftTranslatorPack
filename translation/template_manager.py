from app_paths import resource_dir
from json_io import load_json_safe


def templates_path(language_pair="en_es"):
    return resource_dir() / "translation" / language_pair / "templates.json"


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

    return load_json_safe(templates_path(language_pair), [])
