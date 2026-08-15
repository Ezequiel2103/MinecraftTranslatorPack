import json


class JsonHandler:
    def read(self, path):
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write(self, data, path, **kwargs):
        with path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )
