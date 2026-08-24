from unittest.mock import patch

from translation.curseforge_search import (
    CurseForgeError,
    search_translation_packs
)


FAKE_CATEGORIES_RESPONSE = {
    "data": [
        {"id": 6, "slug": "mc-mods", "name": "Mods"},
        {"id": 12, "slug": "texture-packs", "name": "Resource Packs"},
    ]
}

FAKE_SEARCH_RESPONSE = {
    "data": [
        {
            "id": 111,
            "name": "ATM10 Spanish Translation",
            "summary": "Traduccion al espanol de All the Mods 10",
            "downloadCount": 5000,
            "links": {"websiteUrl": "https://www.curseforge.com/minecraft/texture-packs/atm10-es"},
            "latestFiles": [
                {"downloadUrl": "https://edge.forgecdn.net/files/1/1/atm10-es.zip", "fileName": "atm10-es.zip"}
            ]
        },
        {
            # No download URL available: must be skipped, not crash.
            "id": 222,
            "name": "Broken Entry",
            "summary": "",
            "downloadCount": 1,
            "links": {},
            "latestFiles": []
        }
    ]
}


def main():
    def fake_request(path, api_key, params=None):
        if path == "/categories":
            return FAKE_CATEGORIES_RESPONSE
        if path == "/mods/search":
            assert params["classId"] == "12", params
            assert "ATM10" in params["searchFilter"]
            return FAKE_SEARCH_RESPONSE
        raise AssertionError(f"unexpected path: {path}")

    with patch("translation.curseforge_search._request", side_effect=fake_request):
        results = search_translation_packs("ATM10", api_key="fake-key")

    assert len(results) == 1, results
    assert results[0]["name"] == "ATM10 Spanish Translation"
    assert results[0]["download_url"] == "https://edge.forgecdn.net/files/1/1/atm10-es.zip"
    assert results[0]["download_count"] == 5000

    # Category lookup failing must not crash the whole search — it just
    # searches without narrowing by category.
    def fake_request_no_categories(path, api_key, params=None):
        if path == "/categories":
            return {"data": []}
        if path == "/mods/search":
            assert "classId" not in params, params
            return {"data": []}
        raise AssertionError(f"unexpected path: {path}")

    with patch("translation.curseforge_search._request", side_effect=fake_request_no_categories):
        results2 = search_translation_packs("Some Modpack", api_key="fake-key")
    assert results2 == []

    print("CurseForge search OK")


if __name__ == "__main__":
    main()
