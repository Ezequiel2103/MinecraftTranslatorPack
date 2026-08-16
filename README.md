# MinecraftTranslatorPack

Herramienta modular para traducir archivos JSON de idioma de Minecraft.

## Estructura del proyecto

```text
ai/             Proveedores y construcción de prompts
analyzer/       Extracción, protección y validación de textos
formats/        Handlers para JSON, SNBT y archivos .lang
localization/   Interfaces de usuario
review/         Pending y revisión humana
translation/    Servicio, memoria, terminología y retry
test_modpack/   JSON de prueba de Minecraft
test_*.py       Pruebas deterministas por componente
run_tests.py    Suite local unificada
main.py         Punto de entrada de la aplicación
```

El núcleo (`formats`, `analyzer`, `translation` y `review`) no depende de un proveedor
concreto. `MockAITranslator` se usa para pruebas, `OllamaTranslator` es un
backend local opcional, y `OpenAITranslator`, `ClaudeTranslator` y
`DeepSeekTranslator` son proveedores cloud alternativos.

Los formatos iniciales soportados son:

- `.json`, mediante `JsonHandler`;
- `.lang`, mediante `LangHandler`;
- `.snbt`, mediante `SnbtHandler` y `nbtlib`.

## Estado actual

El flujo implementado y probado incluye extracción recursiva, clasificación,
terminología, memoria por combinación de idiomas, protección de placeholders,
validación de calidad, retry automático, fallback a `pending.json`, revisión
manual y los proveedores `mock`, `ollama`, `openai`, `claude` y `deepseek`.

Con `--mods-folder` se puede indicar la carpeta `mods` de un modpack: el
programa lee el nombre real de cada mod desde su propio `.jar` (sin depender
del nombre de archivo) y protege esos nombres para que la IA nunca los
traduzca (por ejemplo, el mod "Create" no se traduce como "Crear"). La lista
detectada queda guardada en `translation/<idioma>/protected_terms.json`,
editable a mano para sacar nombres ambiguos (palabras comunes del idioma
de origen) antes de traducir el modpack completo.

El soporte de formatos forma parte de la primera versión: JSON, `.lang` y SNBT.
El lector SNBT acepta la variante que genera FTB Quests (campos separados por
saltos de línea y listas de compounds sin comas). Para SNBT se conserva el
archivo original como plantilla y se reemplazan únicamente los valores
traducidos, manteniendo indentación, orden y estructura.

La suite local actual pasa completamente con `python run_tests.py`.

La ejecución predeterminada usa el proveedor mock y no realiza llamadas de red.

## Instalación

```powershell
python -m pip install -r requirements.txt
```

Para usar OpenAI, configurá la clave fuera del código. En PowerShell:

```powershell
$env:OPENAI_API_KEY = "tu_clave"
$env:OPENAI_MODEL = "gpt-5"
```

También podés copiar `.env.example` como referencia. El archivo `.env` está
ignorado por Git y nunca debe subirse al repositorio.

## Ejecución con mock

```powershell
python main.py
```

El mismo flujo selecciona el handler por extensión. Por ejemplo:

```powershell
python main.py --input config/en_us.lang --output config/es_es.lang
python main.py --input data/example.snbt --output data/example_es.snbt
```

Para traducir una carpeta completa y conservar su estructura:

```powershell
python main.py `
  --input-folder modpack/lang `
  --output-folder translated_modpack/lang
```

Para que los nombres de mods no se traduzcan, sumá `--mods-folder` apuntando
a la carpeta `mods` del modpack:

```powershell
python main.py `
  --input-folder modpack/lang `
  --output-folder translated_modpack/lang `
  --mods-folder modpack/mods
```

Si en cambio preferís que la IA sí traduzca los nombres de mods (por ejemplo,
para otro idioma donde eso tenga sentido), agregá `--translate-mod-names`.
Ese flag ignora la protección para esa corrida puntual, sin necesidad de
editar `protected_terms.json`:

```powershell
python main.py `
  --input-folder modpack/lang `
  --output-folder translated_modpack/lang `
  --mods-folder modpack/mods `
  --translate-mod-names
```

Si la fuente se llama `en_us.json`, la salida se genera como `es_es.json`.
Podés indicar otra variante con `--target-locale`. La carpeta de entrada debe
contener las fuentes; evitá incluir dentro de ella los archivos de salida ya
traducidos.

## Ejecución configurable

```powershell
python main.py `
  --input test_modpack/lang/en_us.json `
  --output test_modpack/lang/es_es.json `
  --source-language en `
  --target-language es `
  --interface-language es `
  --ai-provider mock
```

## Proveedor OpenAI

Una vez configurada `OPENAI_API_KEY`, se puede seleccionar explícitamente:

```powershell
python main.py --ai-provider openai --ai-model gpt-5
```

Antes de traducir un modpack completo, usar la prueba controlada:

```powershell
python test_openai_live.py --live
```

La prueba realiza una sola solicitud y muestra si la traducción pasó la
validación de placeholders.

## Proveedor Ollama local

Con Ollama instalado y el modelo descargado, se puede ejecutar sin API key:

```powershell
python main.py --ai-provider ollama --ai-model qwen2.5:3b-instruct
```

El proveedor usa el endpoint local `http://localhost:11434/api/generate`.

## Pruebas locales sin API

```powershell
python run_tests.py
```

## Revisión manual

Listar pendientes de una combinación de idiomas:

```powershell
python review/review_cli.py --language-pair en_es --list
```

Para revisar y aprobar una entrada:

```powershell
python review/review_cli.py --language-pair en_es
```

## Prueba controlada con un modpack real

Antes de modificar una instancia de Minecraft, trabajar siempre sobre una
carpeta de prueba y conservar la instancia original intacta. Por ejemplo:

```powershell
$source = "C:\Users\Ezequiel\curseforge\minecraft\Instances\All of Create - Aeronautics\config\ftbquests\quests\lang"
$sample = "C:\Users\Ezequiel\MinecraftTranslatorLangTest\input"
$output = "C:\Users\Ezequiel\MinecraftTranslatorLangTest\output"

New-Item -ItemType Directory -Force $sample | Out-Null
New-Item -ItemType Directory -Force $output | Out-Null
Get-ChildItem -LiteralPath $source -File |
  Where-Object { $_.Extension.ToLower() -in @('.snbt', '.json', '.lang') } |
  Select-Object -First 3 |
  Copy-Item -Destination $sample -Force

python main.py `
  --input-folder $sample `
  --output-folder $output `
  --source-language en `
  --target-language es `
  --ai-provider mock
```

`mock` valida lectura, escritura y estructura, pero no traduce textos nuevos.
Para usar el modelo local:

```powershell
python main.py `
  --input-folder $sample `
  --output-folder $output `
  --source-language en `
  --target-language es `
  --ai-provider ollama `
  --ai-model qwen2.5:3b-instruct
```

Ollama procesa cada texto secuencialmente; un archivo de idioma grande puede
tardar varios minutos y la salida se escribe al finalizar el archivo completo.
Las entradas rechazadas quedan en `review/en_es/pending.json`.

## Roadmap y cómo continuar

### Completado

1. Arquitectura modular y CLI para archivo único o carpeta.
2. Soporte inicial de JSON, `.lang` y SNBT.
3. Compatibilidad con SNBT real de FTB Quests y preservación de formato.
4. Protección de placeholders como `%s` y `\\n`.
5. Memoria, terminología, validación, retry y revisión manual.
6. Adaptadores `mock`, Ollama local, OpenAI, Claude y DeepSeek opcionales.
7. Pruebas deterministas y prueba de extremo a extremo de los tres formatos.
8. Progreso visible (`texto N de M`, `archivo N de M`) durante carpetas grandes.
9. Protección automática de nombres de mods vía `--mods-folder`, leyendo el
   nombre real desde los metadatos de cada `.jar` (Forge/NeoForge/Fabric),
   con `--translate-mod-names` para desactivarla en una corrida puntual.
10. Revisión de pendientes asistida por IA (`review_cli.py --ai-filter`)
    para filtrar automáticamente traducciones "sin cambios" correctas.
11. Traducción del contenido de los mods (objetos, bloques, logros) vía
    `translate_mods.py`, con un único resource pack de salida y un caché
    por mod (`mod_lang_cache/`) reutilizable entre modpacks distintos.
12. Filtro `--content-only` para saltar mods sin contenido real
    (optimización/configuración), con la clasificación de cada mod
    guardada una sola vez (`content_classification.json`, editable a mano).
13. `--pack-icon` para poner una imagen propia como ícono del resource pack.
14. Empaquetado en el formato real de CurseForge (`manifest.json` +
    `overrides/`) vía `deploy_manager.build_curseforge_import_zip`, para
    que importar no pierda la configuración generada (como las misiones).
15. Respaldo automático y aplicación explícita a una copia de la instancia
    (`deploy_manager.apply_to_modpack_copy` / `apply_to_modpack.py`).
16. Reutilización automática de traducciones exitosas (memoria + caché en
    proceso) y traducción en paralelo (`--concurrency`) para acelerar
    corridas grandes.
17. Corrección de un bug de fondo: `extract_texts` ignoraba las
    descripciones de misión en varias líneas, lo que además desalineaba
    la escritura del SNBT y mezclaba traducciones entre misiones. Se
    agregó además una alarma de seguridad que frena la escritura si
    vuelve a detectarse una desalineación así en otro modpack.

### Próximos pasos

1. Revisar a mano los textos que quedaron pendientes (misiones y mods).
2. Investigar el contenido de mods como "Create Aeronautics" que no usan
   el formato estándar de lang (parece venir de un sistema de datapacks
   propio del modpack) — hoy fuera del alcance del traductor de mods.
3. Un resumen/informe final consolidado al terminar una corrida grande
   (cuántos textos, cuántos pendientes, dónde quedó cada archivo).
4. Revisar la colisión de `pending.json`: hoy se guarda por texto
   original, así que dos mods distintos con el mismo texto sin traducir
   pisan la misma entrada en vez de guardarse por separado.

El orden recomendado es: prueba pequeña con `mock`, prueba pequeña con Ollama,
revisión de pendientes, traducción completa a una carpeta separada y prueba
del modpack con esa copia. No usar la carpeta original de CurseForge como
salida durante las primeras pruebas.
