def apply_translations(data, translations):
    for item in translations:

        translation = item["translation"]

        if translation is None:
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
        data[path] = new_value
        return

    parts = path.split(".")

    current = data

    for part in parts[:-1]:

        if isinstance(current, dict):

            if part not in current:
                return

            current = current[part]

        elif isinstance(current, list):

            if not part.isdigit():
                return

            index = int(part)

            if index >= len(current):
                return

            current = current[index]

        else:
            return

    final_part = parts[-1]

    if isinstance(current, dict):

        if final_part in current:
            current[final_part] = new_value

    elif isinstance(current, list):

        if final_part.isdigit():

            index = int(final_part)

            if index < len(current):
                current[index] = new_value