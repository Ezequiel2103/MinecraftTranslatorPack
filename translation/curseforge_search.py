import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = "https://api.curseforge.com/v1"
MINECRAFT_GAME_ID = 432


class CurseForgeError(Exception):
    """Raised when the CurseForge API can't be reached or answers with
    something unexpected — callers should show this message to the user
    and fall back to translating normally, never fail the whole run."""


def _request(path, api_key, params=None):
    query = f"?{urlencode(params)}" if params else ""

    request = Request(
        f"{API_BASE}{path}{query}",
        headers={"x-api-key": api_key, "Accept": "application/json"}
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == 401 or error.code == 403:
            raise CurseForgeError(
                "La API key de CurseForge no es válida o no tiene permiso."
            ) from error
        raise CurseForgeError(
            f"CurseForge respondió con un error ({error.code})."
        ) from error
    except URLError as error:
        raise CurseForgeError(
            f"No se pudo conectar a CurseForge: {error.reason}"
        ) from error
    except json.JSONDecodeError as error:
        raise CurseForgeError(
            "CurseForge devolvió una respuesta que no se pudo leer."
        ) from error


def _resourcepack_class_id(api_key):
    """
    Looks up the numeric classId CurseForge currently uses for its
    "Resource Packs" category, instead of hardcoding a guessed number
    that could silently be wrong or change. Returns None (search without
    narrowing by category) if it can't be found, rather than failing.
    """

    data = _request("/categories", api_key, {"gameId": str(MINECRAFT_GAME_ID)})

    for category in data.get("data", []):
        if category.get("slug") == "texture-packs":
            return category.get("id")

    return None


def search_translation_packs(modpack_name, api_key, page_size=10):
    """
    Searches CurseForge's Minecraft resource packs for an existing
    community translation matching this modpack's name (e.g. "ATM10
    spanish translation"), so it can potentially be used directly
    instead of spending any AI budget translating the same mods from
    scratch. Returns a list of candidates for a human to review and pick
    from — never applied automatically, since name-matching a modpack to
    a translation pack is inherently approximate.
    """

    class_id = _resourcepack_class_id(api_key)

    params = {
        "gameId": str(MINECRAFT_GAME_ID),
        "searchFilter": f"{modpack_name} spanish",
        "pageSize": str(page_size),
        "sortField": "2",
        "sortOrder": "desc"
    }

    if class_id:
        params["classId"] = str(class_id)

    data = _request("/mods/search", api_key, params)

    results = []

    for mod in data.get("data", []):
        latest_files = mod.get("latestFiles") or []
        download_url = latest_files[0].get("downloadUrl") if latest_files else None

        if not download_url:
            continue

        results.append({
            "id": mod.get("id"),
            "name": mod.get("name"),
            "summary": mod.get("summary", ""),
            "download_count": mod.get("downloadCount", 0),
            "page_url": (mod.get("links") or {}).get("websiteUrl", ""),
            "download_url": download_url,
            "file_name": latest_files[0].get("fileName", "")
        })

    return results


def download_translation_pack(download_url, destination_path):
    request = Request(download_url, headers={"Accept": "application/octet-stream"})

    try:
        with urlopen(request, timeout=120) as response:
            data = response.read()
    except (HTTPError, URLError) as error:
        raise CurseForgeError(
            f"No se pudo descargar el archivo: {error}"
        ) from error

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_bytes(data)

    return destination_path
