import re


def apply_translations(data, translations):

    for item in translations:

        translation = item["translation"]

        # Skip missing translations
        if translation is None:
            continue

        # Skip invalid translations
        if not item.get("valid", True):
            continue

        path = item["path"]

        _replace_value(
            data,
            path,
            translation
        )

    return data

def _replace_value(data, path, new_value):

    # Try the complete path as a dictionary key first
    if isinstance(data, dict) and path in data:
        data[path] = _coerce_value(data[path], new_value)
        return

    parts = _split_path(path)

    if not parts:
        return

    current = data

    for part in parts[:-1]:

        if isinstance(current, dict):

            if not isinstance(part, str) or part not in current:
                return

            current = current[part]

        elif isinstance(current, list):

            if not isinstance(part, int):
                return

            if part >= len(current):
                return

            current = current[part]

        else:
            return

    final_part = parts[-1]

    if isinstance(current, dict):

        if isinstance(final_part, str) and final_part in current:
            current[final_part] = _coerce_value(
                current[final_part],
                new_value
            )

    elif isinstance(current, list):

        if isinstance(final_part, int) and final_part < len(current):
            current[final_part] = _coerce_value(
                current[final_part],
                new_value
            )


def _split_path(path):
    """Splits paths such as ``examples[2].name`` into usable segments."""

    parts = []

    for key, index in re.findall(r"([^\.\[\]]+)|\[(\d+)\]", path):
        parts.append(int(index) if index else key)

    return parts


def _coerce_value(existing_value, new_value):
    """Keeps typed string values such as nbtlib.String serializable."""

    if isinstance(existing_value, str) and type(existing_value) is not str:
        try:
            return type(existing_value)(new_value)
        except (TypeError, ValueError):
            return new_value

    return new_value
