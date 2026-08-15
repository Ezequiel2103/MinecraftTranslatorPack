from analyzer.json_reader import read_json
from analyzer.text_extractor import extract_texts



from translation.translation_service import TranslationService

from localization.localization_manager import load_interface

from analyzer.json_writer import write_json
from analyzer.text_replacer import apply_translations
from analyzer.translation_decision import decide_translation

# Application language
interface = load_interface("es")

translation_service = TranslationService("en_es")

# Modpack language configuration
source_language = "en"
target_language = "es"

file_path = "test_modpack/lang/en_us.json"


# Read JSON
data = read_json(file_path)

if data is None:
    print(f"❌ {interface['error']}")
    exit()


# Extract texts
texts = extract_texts(data)


# Classify texts
translatable_texts = []
technical_texts = []
uncertain_texts = []


for item in texts:

    decision = decide_translation(item)

    action = decision["action"]

    if action == "translate":

        translatable_texts.append(item)

    elif action == "ignore":

        technical_texts.append(item)

    elif action == "review":

        uncertain_texts.append(item)


# Search translation memory
results = []

for item in translatable_texts:

    result = translation_service.translate(
        item["text"],
        item["path"]
    )

    results.append({
        "path": item["path"],
        "original": item["text"],
        "translation": result["translation"],
        "source": result["source"]
    })

# Apply translations
data = apply_translations(
    data,
    results
)

# Write translated JSON
output_path = "test_modpack/lang/es_es.json"

write_json(
    data,
    output_path
)

# Interface
print("===================================")
print(f"     {interface['app_title']}")
print("===================================")
print()

print(
    f"📝 {interface['texts_found']}: "
    f"{len(texts)}"
)

print(
    f"🌎 {interface['translatable_texts']}: "
    f"{len(translatable_texts)}"
)

print(
    f"🔒 {interface['technical_texts']}: "
    f"{len(technical_texts)}"
)

print(
    f"❓ {interface['uncertain_texts']}: "
    f"{len(uncertain_texts)}"
)

print()

for result in results:

    original = result["original"]
    translation = result["translation"]

    if translation:

        print(f"✅ {original}")
        print(f"   → {translation}")

    else:

        print(f"❓ {original}")
        print(
            f"   → "
            f"{interface['translation_not_found']}"
        )

    print()

print(f"✅ Archivo traducido creado: {output_path}")