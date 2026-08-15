from review.review_manager import approve_translation


original = "Craft your first machine."

translation = "Construye tu primera máquina."


success = approve_translation(
    original,
    translation,
    "en_es"
)


print(
    "Translation approved:",
    success
)