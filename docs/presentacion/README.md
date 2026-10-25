# Presentación de Agent World Lab

Documento de siete páginas para explicar el proyecto a una persona no técnica. Incluye diagramas, un ejemplo de Nube Norte, los resultados de los nueve casos, costos, posibles aplicaciones y límites de la primera prueba.

- **[Leer o descargar el PDF](Agent_World_Lab_presentacion.pdf)**.
- **[Descargar Word editable](Agent_World_Lab_presentacion.docx)**.
- [Explorar los resultados y decisiones del estudio](../../examples/recorded-study/README.md).

## Contenido

1. El proyecto y el valor de explorar decisiones colectivas.
2. Cómo interactúan los agentes y por qué importan sus observaciones limitadas.
3. Qué se probó y cuánto costó la ejecución.
4. Cuándo la información adicional ayudó o confundió.
5. Comparación de los nueve casos, incluidos los resultados desfavorables.
6. Posibles aplicaciones y una próxima prueba con equipos de agentes.
7. Componentes del laboratorio, desarrollo abierto y límites de las conclusiones.

Los resultados corresponden al estudio cerrado el 25 de octubre de 2026. Las aplicaciones futuras están identificadas como propuestas. El documento no presenta estas pruebas sintéticas como predicciones de personas.

## Reconstruir el Word

`build_document.py` utiliza los datos públicos incluidos en este repositorio. Requiere Python con `python-docx` y `Pillow`, y una de las familias de fuentes Arial, Liberation Sans o DejaVu Sans. No requiere motores ni clave de API.

```sh
python3 docs/presentacion/build_document.py
# O elige otro directorio de salida:
python3 docs/presentacion/build_document.py /ruta/a/una/carpeta
```

La salida por defecto va a `docs/presentacion/rebuilt/`, excluida de Git. La paginación puede variar con las fuentes o la aplicación de Word. Para un PDF consistente, usa el archivo publicado, que se renderizó y revisó página por página. Para volver a exportar, abre el Word generado con Word o LibreOffice y revisa su diseño antes de compartirlo.
