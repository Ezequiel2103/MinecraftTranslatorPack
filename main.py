from analyzer.json_reader import read_json
from analyzer.text_extractor import extract_texts
from analyzer.text_classifier import classify_text


from translation.translation_memory import translate_with_memory

from localization.localization_manager import load_interface

from analyzer.json_writer import write_json
from analyzer.text_replacer import apply_translations


# Application language
interface = load_interface("es")


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

    classification = classify_text(item["text"])

    if classification == "translatable":
        translatable_texts.append(item)

    elif classification == "technical":
        technical_texts.append(item)

    else:
        uncertain_texts.append(item)


# Search translation memory
results = translate_with_memory(translatable_texts)

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