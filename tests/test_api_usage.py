import json

from translation import api_usage


def main():
    backup = (
        api_usage.USAGE_PATH.read_text(encoding="utf-8")
        if api_usage.USAGE_PATH.exists() else None
    )

    try:
        if api_usage.USAGE_PATH.exists():
            api_usage.USAGE_PATH.unlink()

        assert api_usage.get_usage()["characters_used"] == 0

        api_usage.record_usage(1000)
        api_usage.record_usage(500)
        assert api_usage.get_usage()["characters_used"] == 1500

        assert api_usage.would_exceed(100, limit=1000) is True
        assert api_usage.would_exceed(100, limit=2000) is False
        assert api_usage.remaining_characters(limit=2000) == 500

        # A stored usage file from a previous month must reset instead of
        # carrying over — otherwise a run could refuse to translate
        # anything for the rest of a brand new month.
        api_usage.USAGE_PATH.write_text(
            json.dumps({"month": "2000-01", "characters_used": 999999}),
            encoding="utf-8"
        )
        assert api_usage.get_usage()["characters_used"] == 0

        print("API usage tracking OK")

    finally:
        if backup is not None:
            api_usage.USAGE_PATH.write_text(backup, encoding="utf-8")
        elif api_usage.USAGE_PATH.exists():
            api_usage.USAGE_PATH.unlink()


if __name__ == "__main__":
    main()
