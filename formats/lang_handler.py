class LangDocument(dict):
    def __init__(self, values, original_lines):
        super().__init__(values)
        self.original_lines = original_lines


class LangHandler:
    def read(self, path):
        values = {}
        original_lines = path.read_text(encoding="utf-8").splitlines(
            keepends=True
        )

        for line in original_lines:
            stripped = line.strip()

            if not stripped or stripped.startswith(("#", "!")):
                continue

            if "=" not in line:
                continue

            key, value = line.rstrip("\r\n").split("=", 1)
            values[key.strip()] = value

        return LangDocument(values, original_lines)

    def write(self, data, path, **kwargs):
        with path.open("w", encoding="utf-8") as file:
            written_keys = set()

            for line in getattr(data, "original_lines", []):
                if "=" not in line:
                    file.write(line)
                    continue

                key, _ = line.rstrip("\r\n").split("=", 1)
                normalized_key = key.strip()

                if normalized_key not in data:
                    file.write(line)
                    continue

                newline = "\n" if line.endswith("\n") else ""
                file.write(
                    f"{key}={data[normalized_key]}{newline}"
                )
                written_keys.add(normalized_key)

            for key, value in data.items():
                if key not in written_keys:
                    file.write(f"{key}={value}\n")
