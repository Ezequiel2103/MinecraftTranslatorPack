from analyzer.text_extractor import extract_texts
from analyzer.text_replacer import apply_translations


def main():
    data = {
        "quest": {
            "quest_desc": [
                "First line.",
                "",
                "Second line."
            ]
        }
    }

    texts = extract_texts(data)
    paths = {item["path"]: item["text"] for item in texts}

    assert paths["quest.quest_desc[0]"] == "First line."
    assert paths["quest.quest_desc[1]"] == ""
    assert paths["quest.quest_desc[2]"] == "Second line."

    results = [
        {
            "path": "quest.quest_desc[0]",
            "translation": "Primera línea.",
            "valid": True
        },
        {
            "path": "quest.quest_desc[2]",
            "translation": "Segunda línea.",
            "valid": True
        }
    ]

    updated = apply_translations(data, results)

    assert updated["quest"]["quest_desc"] == [
        "Primera línea.",
        "",
        "Segunda línea."
    ]

    print("Extract texts from lists OK")


if __name__ == "__main__":
    main()
