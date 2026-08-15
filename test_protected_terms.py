from analyzer.text_protector import protect_text, restore_text


def main():
    text = "Create your first Machine using Create: New Age parts."

    protected_text, protected = protect_text(
        text,
        extra_terms=["Create", "Create: New Age"]
    )

    assert "Create" not in protected_text
    assert len(protected) == 2
    assert restore_text(protected_text, protected) == text

    plain_text, plain_protected = protect_text(text)
    assert "Create" in plain_text
    assert plain_protected == {}

    print("Protected terms OK")


if __name__ == "__main__":
    main()
