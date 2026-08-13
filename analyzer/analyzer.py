from pathlib import Path


EXTENSIONES_TRADUCIBLES = {
    ".json",
    ".snbt",
    ".lang",
}


def analizar_carpeta(ruta):
    carpeta = Path(ruta)

    if not carpeta.exists():
        print("❌ La carpeta no existe.")
        return

    archivos = [
        archivo
        for archivo in carpeta.rglob("*")
        if archivo.is_file()
    ]

    traducibles = [
        archivo
        for archivo in archivos
        if archivo.suffix.lower() in EXTENSIONES_TRADUCIBLES
    ]

    print(f"📁 Carpeta analizada: {carpeta}")
    print(f"📄 Archivos encontrados: {len(archivos)}")
    print(f"🌎 Archivos potencialmente traducibles: {len(traducibles)}")

    print("\nArchivos traducibles:")

    for archivo in traducibles:
        print(f"  🟢 {archivo}")