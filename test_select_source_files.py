from pathlib import Path

from translator_app import select_source_files


def main():
    # No canonical en_us present, but two regional English variants of the
    # same file type: only one may be picked, or both would collide on the
    # same "es_es.json" output and silently overwrite each other.
    result = select_source_files(
        [Path("en_gb.json"), Path("en_za.json")], "en"
    )
    assert len(result) == 1, result

    # A locale-shaped filename for a DIFFERENT language than the one being
    # translated must never be treated as source content.
    result = select_source_files([Path("es_419.json")], "pt")
    assert result == [], result

    # The normal case: real English source plus fan translations already
    # bundled in the same folder — only the real source is kept.
    result = select_source_files(
        [Path("en_us.snbt"), Path("ko_kr.snbt"), Path("zh_cn.snbt")], "en"
    )
    assert [path.name for path in result] == ["en_us.snbt"], result

    # Same stem, different formats: these do NOT collide (different
    # extensions map to different output files), so both must survive.
    result = select_source_files(
        [Path("en_us.json"), Path("en_us.lang"), Path("example.snbt")], "en"
    )
    assert sorted(path.name for path in result) == [
        "en_us.json", "en_us.lang", "example.snbt"
    ], result

    print("Select source files OK")


if __name__ == "__main__":
    main()
