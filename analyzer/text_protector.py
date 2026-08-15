import re


PROTECTED_PATTERNS = [
    # Minecraft formatting codes
    r'§[0-9a-fk-orA-FK-OR]',
    r'&[0-9a-fk-orA-FK-OR]',

    # Percent placeholders
    r'%\d*\$?[sdif]',

    # Curly-brace placeholders
    r'\{\{[^{}]+\}\}',
    r'\{[^{}]+\}',

    # Escaped characters
    r'\\n',
    r'\\t',
]


def protect_text(text, extra_terms=None):
    protected = {}
    counter = 0

    def replace(match):
        nonlocal counter

        placeholder = f"__MTP_PROTECTED_{counter}__"

        protected[placeholder] = match.group(0)

        counter += 1

        return placeholder

    base_pattern = "|".join(
        f"({pattern})"
        for pattern in PROTECTED_PATTERNS
    )

    protected_text = re.sub(
        base_pattern,
        replace,
        text
    )

    if extra_terms:
        # Longest terms first so a full mod name (e.g. "Create: New Age")
        # is protected as a whole instead of a shorter name inside it
        # (e.g. "Create") matching first and leaving the rest exposed.
        # The boundary check treats letters/digits as word characters but
        # not underscores, so a term glued to a formatting code that was
        # already replaced by a "__MTP_PROTECTED_N__" placeholder (e.g.
        # "&eCreate") is still recognized as a separate word.
        sorted_terms = sorted(set(extra_terms), key=len, reverse=True)
        terms_pattern = "|".join(
            rf"(?<![^\W_]){re.escape(term)}(?![^\W_])"
            for term in sorted_terms
        )

        protected_text = re.sub(
            terms_pattern,
            replace,
            protected_text
        )

    return protected_text, protected


def restore_text(text, protected):
    for placeholder, original in protected.items():
        text = text.replace(
            placeholder,
            original
        )

    return text