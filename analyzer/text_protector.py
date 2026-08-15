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


def protect_text(text):
    protected = {}
    counter = 0

    combined_pattern = "|".join(
        f"({pattern})"
        for pattern in PROTECTED_PATTERNS
    )

    def replace(match):
        nonlocal counter

        placeholder = f"__MTP_PROTECTED_{counter}__"

        protected[placeholder] = match.group(0)

        counter += 1

        return placeholder

    protected_text = re.sub(
        combined_pattern,
        replace,
        text
    )

    return protected_text, protected


def restore_text(text, protected):
    for placeholder, original in protected.items():
        text = text.replace(
            placeholder,
            original
        )

    return text