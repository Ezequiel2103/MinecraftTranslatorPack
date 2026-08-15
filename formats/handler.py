from formats.json_handler import JsonHandler
from formats.lang_handler import LangHandler
from formats.snbt_handler import SnbtHandler


HANDLERS = {
    ".json": JsonHandler(),
    ".lang": LangHandler(),
    ".snbt": SnbtHandler(),
}


def get_handler(path):
    suffix = path.suffix.lower()

    try:
        return HANDLERS[suffix]
    except KeyError as error:
        raise ValueError(
            f"Unsupported localization format: {suffix}"
        ) from error
