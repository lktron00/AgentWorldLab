# Primer piloto grabado con todos los agentes usando IA

El piloto Nube Norte ejecutó **20 cuentas Luna × 10 turnos × dos condiciones × 10 repeticiones**: **4.000 decisiones de IA**, todas aplicadas. Esta grabación no llama a modelos.

- `report.json` conserva configuración, instrucciones, métricas por condición y diferencias de los diez pares.
- `decisions.jsonl.gz` contiene las 4.000 observaciones limitadas, decisiones, justificaciones públicas, tokens y costos calculados. Los IDs privados del proveedor y las rutas personales están omitidos.
- `execution-audit.json` conserva el resumen de la auditoría original; las bases de los motores y los payloads originales no se publican aquí.

La probabilidad media declarada de pérdida permanente pasó de **15,6%** con el estado genérico a **5,035%** con diagnóstico. Las cuentas que compartieron el mensaje inicial permanecieron en **una en ambas condiciones** en todos los pares. Este resultado no demuestra una reducción de difusión: se conserva también la ausencia de cambio observado.

El consumo confirmado según uso reportado fue **US$0.8736880250**, incluido como débito previo en el [estudio posterior de nueve casos](../recorded-study/README.md). No es un presupuesto nuevo ni un cargo que deba sumarse de nuevo a su total acumulado. Excluye impuestos, infraestructura y créditos de desarrollo.

Verificación sin claves ni motores desde la raíz:

```sh
python3 scripts/build-study-example.py --check
```

El verificador público comprueba integridad de los archivos, observaciones y costo según tokens. El resumen de auditoría es evidencia registrada de la ejecución original; no permite reconstruir todas las bases de los motores desde este paquete. Los escenarios son ficticios y no representan predicciones de personas.

Más detalles en [el diseño del piloto](../../docs/all-ai-pilot.md).
