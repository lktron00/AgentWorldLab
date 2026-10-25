# Estudio grabado con agentes de IA

Esta es una grabación de una ejecución real en escenarios sintéticos. **Abrir los archivos no ejecuta modelos ni genera gasto.**

El estudio terminó el 25 de octubre de 2026 con **102 pares completos**, 20 cuentas Luna por mundo y diez turnos por condición. Se registraron **41.770 decisiones válidas**, de las cuales 41.720 se aplicaron. Los cuatro pares incompletos y las 50 propuestas sin aplicar permanecen identificados; no se cuentan como comparaciones completas.

## Empezar sin instalar los motores

1. Descarga o clona el repositorio.
2. Abre [index.html](index.html) en un navegador moderno compatible con `DecompressionStream`, o abre `web/recorded-study.html` desde la raíz del repositorio.
3. Revisa los nueve casos y filtra sus decisiones por condición, turno y cuenta. El visor muestra **3.600 decisiones** de la primera repetición completa de cada caso. La selección es determinista por semilla y no se eligió por el resultado.

GitHub muestra el código del HTML; para usar el visor hay que descargar el archivo y abrirlo. El HTML incluye sus datos y no necesita servidor, conexión al proveedor, clave de API ni bibliotecas externas. El tablero local también enlaza la grabación desde `/campaigns`.

Para una lectura directa en GitHub, abre [los resultados explicados](RESULTS.md) o la [presentación del proyecto](../../docs/presentacion/README.md).

## Archivos publicados

| Archivo | Contenido |
| --- | --- |
| `report.json` | Configuración, instrucciones comunes, casos, todos los agregados, costos y alcance de la publicación |
| `comparisons.json` | Las 102 comparaciones completas con trayectorias, acciones y costos por condición |
| `decisions.jsonl.gz` | Las **41.770 decisiones válidas completas**, observaciones limitadas originales, acciones, motivos públicos, uso de tokens y costo calculado; cada fila distingue si se aplicó |
| `sample-decisions.jsonl.gz` | Las 3.600 decisiones que utiliza el visor |
| `invalid-proposals.json` | Los tres intentos inválidos pagados con su uso y costo registrados |
| `unreceipted-requests.json` | Los 17 contextos sin recibo y sus reservas completas, sin inventar costo cero |
| `execution-audit.json` | Resumen guardado de la auditoría final de la ejecución original |
| `price-book.json` | Tarifas históricas registradas para calcular el costo de esta ejecución |
| `manifest.json` | Tamaños y SHA-256 de los artefactos públicos |

Los identificadores privados de llamadas y respuestas del proveedor y las rutas personales se omiten. Las observaciones y justificaciones describen solo el mundo ficticio. Las bases de los motores y los payloads originales del proveedor permanecen fuera de este paquete; **el resumen de auditoría original no equivale a una auditoría completa reproducible únicamente desde estos archivos**.

Leer una decisión con la biblioteca estándar de Python:

```python
import gzip
import json

with gzip.open("examples/recorded-study/decisions.jsonl.gz", "rt", encoding="utf-8") as stream:
    decision = json.loads(next(stream))
    print(decision["action"])
    print(decision["observation"])
```

## Resultados y costo

En los dos casos de seguridad con evidencia útil, el error fue menor con documento en los 11 pares de cada caso. En la falsa alarma de cobros con una muestra mínima, el error aumentó en 8 de 10 pares. La comparación completa incluye los resultados pequeños y desfavorables.

- Consumo nuevo confirmado según uso reportado: **US$9.1055598500**.
- Piloto anterior incluido: **US$0.8736880250**.
- Total acumulado confirmado: **US$9.9792478750**.
- Reservas completas sin recibo: **US$0.0197201250**.
- Máximo acumulado con esas reservas: **US$9.9989680000**, bajo el mismo tope de US$10.

El máximo no es un cargo confirmado ni una factura exacta. No se incluyen impuestos, infraestructura ni créditos de desarrollo.

## Verificar o reconstruir

Desde la raíz del repositorio, sin motores ni clave API:

```sh
python3 scripts/build-study-example.py --check
```

El verificador comprueba hashes de los archivos, las 45.770 decisiones públicas entre estudio y piloto, hashes de observaciones, acciones de los 102 pares completos, probabilidades y Brier finales, agregados, costos según tokens y el máximo acumulado con reservas. No consulta al proveedor y no reproduce la auditoría de los motores omitidos.

Para reconstruir la exportación necesitas el dataset original completo en el directorio privado `data/studies/nine-cases-10usd` y el piloto original. El comando siguiente solo lee grabaciones, sin generar nuevas decisiones:

```sh
python3 scripts/build-study-example.py
```

Los agentes de un mundo interactúan: una decisión no es una réplica independiente. La unidad de repetición es el par de mundos. Estos resultados no validan comportamiento humano, probabilidades reales ni ventajas comerciales. Consulta el [diseño y sus límites](../../docs/multi-case-study.md).
