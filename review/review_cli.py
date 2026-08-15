from review.review_manager import (
    load_pending,
    approve_translation
)


LANGUAGE_PAIR = "en_es"


def show_pending():

    pending = load_pending(
        LANGUAGE_PAIR
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


def review():

    pending = load_pending(
        LANGUAGE_PAIR
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
        LANGUAGE_PAIR
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


if __name__ == "__main__":
    review()