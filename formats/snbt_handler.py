import re
import json


_NEXT_COMPOUND_KEY = re.compile(r"[A-Za-z0-9_.+\-]+\s*:")
_QUOTED_VALUE = re.compile(r'"(?:\\.|[^"\\])*"')


def _normalize_ftb_snbt(text):
    """Add optional commas omitted by FTB Quests' SNBT writer.

    FTB Quests emits one compound member per line and adjacent compounds in
    lists without commas.  Minecraft accepts this representation, while
    nbtlib expects strict SNBT commas.
    """
    result = []
    length = len(text)
    for index, char in enumerate(text):
        result.append(char)
        if char != "\n":
            continue

        previous = index - 1
        while previous >= 0 and text[previous].isspace():
            previous -= 1
        following = index + 1
        while following < length and text[following].isspace():
            following += 1
        if previous < 0 or following >= length:
            continue

        previous_char = text[previous]
        next_text = text[following:]
        starts_key = bool(_NEXT_COMPOUND_KEY.match(next_text))
        starts_compound = text[following] == "{" and previous_char == "}"
        starts_string_value = text[following] == '"' and previous_char == '"'
        if (starts_key or starts_compound or starts_string_value) and previous_char not in "{[,":
            result.insert(len(result) - 1, ",")
    return "".join(result)


class SnbtHandler:
    def read(self, path):
        try:
            from nbtlib import parse_nbt
        except ImportError as error:
            raise RuntimeError(
                "SNBT support requires nbtlib. "
                "Install it with: pip install nbtlib"
            ) from error

        source = path.read_text(encoding="utf-8")
        return parse_nbt(_normalize_ftb_snbt(source))

    def write(
        self,
        data,
        path,
        source_text=None,
        replacements=None,
        expected_value_count=None
    ):
        try:
            from nbtlib import serialize_tag
        except ImportError as error:
            raise RuntimeError(
                "SNBT support requires nbtlib. "
                "Install it with: pip install nbtlib"
            ) from error

        if source_text is not None:
            path.write_text(
                self._replace_preserving_format(
                    source_text,
                    replacements or {},
                    expected_value_count
                ),
                encoding="utf-8"
            )
            return

        path.write_text(serialize_tag(data), encoding="utf-8")

    @staticmethod
    def _replace_preserving_format(
        source_text,
        replacements,
        expected_value_count=None
    ):
        """Replace translated string values while retaining original layout."""
        value_index = 0

        def replace(match):
            nonlocal value_index
            token = match.group(0)
            replacement = replacements.get(value_index)
            value_index += 1
            if replacement is None:
                return token
            return json.dumps(replacement, ensure_ascii=False)

        result = _QUOTED_VALUE.sub(replace, source_text)

        # Every quoted value found in the raw text must line up 1:1 with
        # the parsed structure's traversal order, since replacements are
        # matched by position. If they diverge (an unhandled SNBT shape
        # the parser and the raw scan disagree on), translations would
        # silently land on the wrong lines instead of failing loudly.
        if (
            expected_value_count is not None
            and value_index != expected_value_count
        ):
            raise RuntimeError(
                "SNBT quoted-value count mismatch: found "
                f"{value_index} quoted value(s) in the source text but "
                f"the parsed structure has {expected_value_count}. "
                "Refusing to write, since translations could land on "
                "the wrong lines."
            )

        return result
