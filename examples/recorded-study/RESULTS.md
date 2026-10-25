# Estudio terminado: nueve casos con agentes de IA

102 comparaciones completas con 20 agentes Luna por mundo, 10 turnos y dos condiciones. Los nueve casos tienen entre 10 y 12 pares completos. Cada par parte del mismo mundo; cambia la información pública consultable desde el minuto 2. Los agentes eligen sus acciones con IA y observaciones limitadas.

Se registraron 41.770 decisiones válidas; 41.720 se aplicaron a los motores. Las 50 propuestas válidas sin aplicar siguen identificadas. Hay 3 propuestas inválidas pagadas y 4 pares incompletos conservados, excluidos de las comparaciones.

## Qué ocurrió

En el falso positivo de seguridad, la probabilidad media declarada de un problema bajó de 33,2% a 21,6% con el documento consultable; el error Brier fue menor en los 11 pares. Con un paquete realmente modificado, la probabilidad subió de 81,8% a 91,8% y también bajó el error en los 11 pares.

La muestra mínima de cobros tuvo el efecto contrario: aunque el fixture era una falsa alarma, la probabilidad declarada subió de 13,8% a 16,9%; el error aumentó en 8 de 10 pares. La auditoría de otra versión tuvo un cambio medio casi nulo, con 6 pares mejores y 5 peores. Ofrecer un documento no garantiza mejores decisiones.

En los archivos, el borrado real siguió siendo difícil de reconocer: 43,0% frente a 45,2% de probabilidad media declarada. El reporte anterior al incidente produjo 41,6% frente a 49,9%. Son resultados observados, no una regla programada de reducción de reenvíos ni prueba de que un documento antiguo sea fiable.

## Comparación completa

Las probabilidades son las medias finales declaradas por los agentes. El Brier mide el error frente al estado sintético conocido; un delta negativo favorece la condición con documento. Los agentes no reciben el estado real ni esa puntuación.

| Caso | Pares | Probabilidad genérico | Con documento | Δ Brier | Pares con menor error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Carpetas ocultas por un índice atrasado | 12 | 9.95% | 10.33% | +0.001009 | 4/12 |
| Borrado real sin copia recuperable | 12 | 42.99% | 45.25% | -0.031799 | 8/12 |
| Un reporte antiguo tranquiliza durante un borrado real | 12 | 41.59% | 49.88% | -0.084522 | 9/12 |
| Una autorización parece un segundo cobro | 12 | 12.03% | 10.18% | -0.007732 | 9/12 |
| Dos cobros definitivos del mismo pedido | 11 | 90.20% | 94.32% | -0.014879 | 9/11 |
| Una muestra mínima no resuelve la alarma de cobros | 10 | 13.78% | 16.86% | +0.011210 | 2/10 |
| Una alerta del escáner con artefacto íntegro | 11 | 33.20% | 21.56% | -0.067368 | 11/11 |
| El paquete descargado no coincide con el manifiesto firmado | 11 | 81.85% | 91.84% | -0.031934 | 11/11 |
| Una auditoría de otra versión contradice la alerta actual | 11 | 82.34% | 82.32% | -0.000721 | 6/11 |

## Costo y reservas

Los importes confirmados se calculan con los tokens y las tarifas registradas; no son una factura final del proveedor. No incluyen impuestos, infraestructura local ni créditos de Codex.

| Concepto | US$ |
| --- | ---: |
| Piloto anterior incluido | 0.8736880250 |
| Consumo confirmado de este estudio | 9.1055598500 |
| Total acumulado confirmado | 9.9792478750 |
| Reservas completas de 17 solicitudes sin recibo | 0.0197201250 |
| Máximo acumulado, incluidas esas reservas | 9.9989680000 |
| Tope autorizado | 10.0000000000 |

Las 17 solicitudes sin recibo no se repitieron ni se contabilizaron como costo cero. Su máximo completo se retuvo durante cada nueva reserva. Por ello, el costo acumulado está entre US$9.9792478750 y US$9.9989680000 según los registros disponibles; el extremo superior no es un cargo confirmado.

El mayor total simultáneo de consumo confirmado más reservas durante la ejecución fue US$9.9999775500, también inferior a US$10. La ejecución cerró cuando otra solicitud acotada no cabía en el presupuesto; no se generaron tokens para gastar el saldo exacto.

## Verificación y límites

La reconstrucción independiente de cierre coincidió con audit.json: verified=true, budget_bounds_verified=true y usage_complete=false. Se verificaron 2.296 estados del motor, 210 bases OASIS, las observaciones limitadas, las propuestas y las acciones aplicadas. La comparación de los nueve casos se recalculó desde SQLite; report.json y completion.json coinciden. El prefijo original del ledger permanece intacto.

Las cuentas de un mundo interactúan entre sí; 41.770 decisiones no equivalen a 41.770 réplicas independientes. La unidad de repetición es el par de mundos. Las diferencias entre casos también cambian el dominio, las instrucciones y la topología; no son una comparación causal controlada entre dominios. Este estudio describe un modelo en escenarios sintéticos y no valida comportamiento humano ni predicciones comerciales.

[Explorar el visor grabado](index.html) después de descargarlo. Los archivos públicos contienen todas las decisiones válidas comprimidas y las 102 comparaciones. Consulta [el alcance y el verificador](README.md): las bases originales de los motores y los payloads del proveedor no se incluyen. El supervisor terminó; abrir esta grabación no inicia una nueva ejecución pagada.
