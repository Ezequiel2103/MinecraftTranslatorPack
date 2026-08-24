from formats.snbt_handler import SnbtHandler


def main():
    handler = SnbtHandler()

    matching = handler._replace_preserving_format(
        '{title:"Hello",desc:"World"}',
        {0: "Hola", 1: "Mundo"},
        expected_value_count=2
    )
    assert matching == '{title:"Hola",desc:"Mundo"}'

    try:
        handler._replace_preserving_format(
            '{title:"Hello",desc:"World"}',
            {0: "Hola"},
            expected_value_count=3
        )
        raise AssertionError("Expected a count mismatch to raise")
    except RuntimeError as error:
        assert "mismatch" in str(error).lower()

    print("SNBT count guard OK")


if __name__ == "__main__":
    main()
