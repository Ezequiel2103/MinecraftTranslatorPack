import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent)
    )

from review.review_manager import (
    load_pending,
    approve_translation
)


def show_pending(language_pair):

    pending = load_pending(
        language_pair
    )

    if not pending:

        print("No hay traducciones pendientes.")
        return

    print()
    print("===================================")
    print("       Translation Review")
    print("===================================")
    print()

    items = list(pending.items())

    for index, (text, data) in enumerate(
        items,
        start=1
    ):

        print(
            f"[{index}] {text}"
        )

        print(
            f"    Path: {data['path']}"
        )

        print(
            f"    Reason: {data['reason']}"
        )

        print()


def review(language_pair):

    pending = load_pending(
        language_pair
    )

    if not pending:

        print("No hay traducciones pendientes.")
        return

    items = list(pending.items())

    print()
    print("===================================")
    print("       Translation Review")
    print("===================================")
    print()

    for index, (text, data) in enumerate(
        items,
        start=1
    ):

        print(
            f"[{index}] {text}"
        )

        print(
            f"    Path: {data['path']}"
        )

        print(
            f"    Reason: {data['reason']}"
        )

        print()

    selection = input(
        "Seleccioná una entrada: "
    )

    try:

        index = int(selection)

        if index < 1 or index > len(items):

            print("❌ Selección inválida.")
            return

    except ValueError:

        print("❌ Debés introducir un número.")
        return

    original, data = items[index - 1]

    print()
    print(f"Texto original:")
    print(original)
    print()

    translation = input(
        "Traducción: "
    ).strip()

    if not translation:

        print(
            "❌ La traducción no puede estar vacía."
        )

        return

    print()
    print("===================================")
    print()
    print(f"Original:    {original}")
    print(f"Traducción:  {translation}")
    print()

    confirmation = input(
        "¿Aprobar traducción? [S/N]: "
    ).strip().lower()

    if confirmation != "s":

        print("❌ Traducción descartada.")
        return

    success = approve_translation(
        original,
        translation,
        language_pair
    )

    if success:

        print()
        print(
            "✅ Traducción aprobada."
        )

        print(
            "📚 Agregada a translation memory."
        )

        print(
            "🗑️ Eliminada de pendientes."
        )

    else:

        print(
            "❌ No se pudo aprobar la traducción."
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Review pending Minecraft translations."
    )
    parser.add_argument(
        "--language-pair",
        default="en_es",
        help="Language pair, for example en_es or en_pt."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List pending translations without reviewing one."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.list:
        show_pending(args.language_pair)
    else:
        review(args.language_pair)
