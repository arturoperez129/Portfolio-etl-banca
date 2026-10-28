# Resultados de los cuatro pipelines ETL

Datos bancarios sintéticos con errores inyectados a propósito. Cada sección muestra qué entró, qué se corrigió y qué se rechazó. Cifras tomadas del reporte de métricas (`reports/metricas.json`) de cada proyecto.

## 1. Transacciones bancarias

Duplicados, fechas imposibles, montos con separador de miles y monedas inválidas. Lo rechazado se guarda con su motivo.

| Métrica | Valor |
|---|---:|
| Filas de entrada | **5.150** |
| Filas limpias | **4.896** |
| Filas rechazadas | **254** |
| Duplicados (% de la entrada) | **2,91** |
| Signos de monto corregidos | **13** |
| Sin categoría tras la limpieza | **146** |

### Motivos de rechazo

Filas rechazadas por regla de calidad.

| Categoría | Cantidad | |
|---|---:|---|
| Duplicados | 150 | ████████████████████ |
| Fechas inválidas | 60 | ████████ |
| Montos inválidos | 24 | ███ |
| Monedas inválidas | 20 | ███ |

## 2. Clientes y deduplicación (KYC)

Precisión: de los pares marcados como duplicados, cuántos lo eran. Recall: de los duplicados reales, cuántos se encontraron. Se miden contra la verdad conocida de los datos sintéticos.

| Métrica | Valor |
|---|---:|
| Registros de entrada | **920** |
| Clientes únicos | **805** |
| Precisión (%) | **100,0** |
| Recall (%) | **95,8** |
| Cédulas recuperadas desde el RUC | **47** |

### Pares duplicados por regla

Cédula exacta primero; nombre difuso solo dentro de la misma fecha de nacimiento.

| Categoría | Cantidad | |
|---|---:|---|
| Cédula exacta | 99 | ████████████████████ |
| Nombre difuso + fecha de nacimiento | 16 | ███ |

### Problemas de calidad detectados

Registros con dato inválido o vacío, antes de consolidar.

| Categoría | Cantidad | |
|---|---:|---|
| Cédulas inválidas o vacías | 35 | ███ |
| RUC con dígito verificador incorrecto | 25 | ██ |
| Teléfonos inválidos | 22 | ██ |
| Emails inválidos o vacíos | 270 | ████████████████████ |

## 3. Cartera de créditos y mora

Índice de morosidad: saldo con más de 90 días de atraso sobre el saldo total. La previsión usa porcentajes ilustrativos por tramo, no la normativa del BCP. Fecha de corte 30/06/2025.

| Métrica | Valor |
|---|---:|
| Créditos limpios | **2.971** |
| Créditos rechazados | **59** |
| Índice de morosidad (%) | **4,0** |
| Saldo de cartera (Gs.) | **257.048.733.000** |
| Previsión ilustrativa (Gs.) | **11.699.527.830** |

### Créditos por tramo de mora

Cantidad de créditos según días de atraso.

| Categoría | Cantidad | |
|---|---:|---|
| Al día | 2.452 | ████████████████████ |
| 1 a 30 días | 216 | ██ |
| 31 a 60 días | 113 | █ |
| 61 a 90 días | 74 | █ |
| 91 a 180 días | 74 | █ |
| Más de 180 días | 42 | █ |

### Correcciones aplicadas

Datos imputados o ajustados; cada uno queda marcado con una bandera.

| Categoría | Cantidad | |
|---|---:|---|
| Ingresos imputados | 238 | ████████████████████ |
| Ingresos atípicos ajustados | 42 | ████ |
| Edades corregidas | 74 | ██████ |

## 4. Conciliación bancaria

El cruce entre extracto y libro corre por etapas, de la regla más estricta a la más flexible. El pipeline falla si queda una diferencia de saldos sin explicar.

| Métrica | Valor |
|---|---:|
| Conciliado del libro (%) | **96,5** |
| Pendientes del libro | **42** |
| Pendientes del banco | **45** |
| Diferencia no explicada (Gs.) | **0** |

### Movimientos conciliados por etapa

Cada etapa trabaja solo con lo que dejaron las anteriores.

| Categoría | Cantidad | |
|---|---:|---|
| 1 · Referencia + monto + fecha exactos | 1.008 | ████████████████████ |
| 2 · Referencia + monto con desfase de fecha | 71 | █ |
| 3 · Monto + fecha sin referencia | 57 | █ |
| 4 · Referencia con diferencia de monto | 22 | █ |

### Partidas pendientes por causa

Causa probable asignada a cada partida sin conciliar.

| Categoría | Cantidad | |
|---|---:|---|
| Libro · Depósitos en tránsito | 24 | ███████████████ |
| Libro · Cheques o pagos en tránsito | 18 | ████████████ |
| Banco · Comisiones no registradas | 31 | ████████████████████ |
| Banco · Débitos automáticos no registrados | 7 | █████ |
| Banco · Intereses no registrados | 7 | █████ |

### Puente de saldos (Gs.)

Saldo según banco menos saldo según libro es igual a partidas solo en banco, menos partidas solo en libro, más diferencias de monto.

| Concepto | Gs. |
|---|---:|
| Saldo según banco | 3.403.581.500 |
| Saldo según libro | 3.495.298.000 |
| Diferencia de saldos | -91.716.500 |
| Partidas solo en banco | -4.089.500 |
| Partidas solo en libro | 87.639.000 |
| Diferencias de monto en conciliadas | 12.000 |

---

Datos sintéticos. Los porcentajes de previsión son ilustrativos y no reflejan normativa del BCP.
