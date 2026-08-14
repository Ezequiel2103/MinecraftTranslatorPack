import json
from pathlib import Path


def read_json(path):
    file = Path(path)

    try:
        with file.open("r", encoding="utf-8") as f:
            content = json.load(f)

        return content

    except json.JSONDecodeError:
        print(f"❌ Invalid JSON: {file}")
        return None

    except Exception as error:
        print(f"❌ Could not read {file}: {error}")
        return None