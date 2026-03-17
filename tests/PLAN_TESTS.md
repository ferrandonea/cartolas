# E1 — Tests unitarios para funciones puras

## Context
El proyecto no tiene tests. Antes de cambios estructurales (E2-E6) necesitamos una red de seguridad. Nos enfocamos en funciones puras o casi-puras (sin I/O ni APIs externas).

---

## Inventario de funciones puras candidatas

### `utiles/fechas.py` — 9 funciones, 7 puras

| Función | Pura? | Casos borde clave |
|---------|-------|-------------------|
| `from_date_to_datetime(input_date)` | **Sí** | `datetime` → `date`, `date` → `date`, tipo inválido (`str`, `int`) → `ValueError` |
| `format_date_cmf(input_date)` | **Sí** | Formato correcto `dd/mm/yyyy`, fecha con `datetime` vs `date`, día/mes de un dígito (padding) |
| `date_range(start, end)` | **Sí** | Rango normal, `start == end` → lista de 1, `start > end` → `ValueError`, rango largo (365+ días) |
| `consecutive_date_ranges(dates, max_days)` | **Sí** | Lista vacía → `[]`, una sola fecha, gap en medio, rango que excede `max_days` (split), fechas desordenadas (debe ordenar), `max_days=0` |
| `es_mismo_mes(fecha)` | **No** (usa `datetime.now()`) | — skip o mock |
| `date_n_months_ago(n, base_date)` | **Sí*** (con `base_date`) | Cruce de año (ene→dic), 31 mar - 1 mes = 28/29 feb, `n=0`, mes con 28/29/30/31 días |
| `date_n_years_ago(n, base_date)` | **Sí*** (con `base_date`) | Año bisiesto (29 feb - 1 año), `n=0` |
| `ultimo_dia_año_anterior(base_date)` | **Sí*** (con `base_date`) | 1 enero (→ 31 dic año anterior), fecha normal |
| `ultimo_dia_mes_anterior(base_date)` | **Sí*** (con `base_date`) | 1 enero (→ 31 dic), 1 marzo año bisiesto (→ 29 feb), 1 marzo no bisiesto (→ 28 feb) |

### `cartolas/polars_utils.py` — 2 funciones puras

| Función | Pura? | Casos borde clave |
|---------|-------|-------------------|
| `map_s_n_to_bool(col)` | **Sí** | `"S"` → True, `"N"` → False, otro valor (`"X"`, `""`) → null, columna con nulls, minúsculas `"s"`/`"n"` |
| `replace_null_with_one(col)` | **Sí** | Valores normales intactos, nulls → 1, columna sin nulls (sin cambio), columna toda nulls |

### `utiles/polars_utils.py` — 1 función pura

| Función | Pura? | Casos borde clave |
|---------|-------|-------------------|
| `add_cumulative_returns(df)` | **Sí** | Un solo fondo/serie, múltiples fondos (partition correcta con `over`), NaN en rentabilidades → fill 1, null → fill 1 |

### `cartolas/transform.py` — 2 funciones con I/O

| Función | Pura? | Casos borde clave |
|---------|-------|-------------------|
| `transform_single_cartola(path, ...)` | **No** (lee disco) | Archivo válido, archivo inexistente → `FileNotFoundError`, esquema aplicado, columnas boolean, `RUN_FM_SERIE` concatenada, `NOM_ADM` dropeada |
| `transform_cartola_folder(...)` | **No** (lee disco) | Múltiples archivos → concat, dedup con `unique=True`, sin dedup con `unique=False` |

### `comparador/merge.py` — 1 función testeable

| Función | Pura? | Casos borde clave |
|---------|-------|-------------------|
| `_validate_custom_mapping(...)` | **Casi** | Mapping válido, duplicados en values → `ValueError`, conflicto con categoría default → `ValueError` |

---

## Estructura de `tests/`

```
tests/
├── conftest.py                    # Fixtures compartidas
├── test_fechas.py                 # utiles/fechas.py (7 funciones puras)
├── test_polars_utils.py           # cartolas/polars_utils.py + utiles/polars_utils.py
├── test_transform.py              # cartolas/transform.py (con fixture TXT)
└── test_validate_mapping.py       # comparador/merge.py (_validate_custom_mapping)
```

## Orden de implementación

1. **Ronda 1**: `conftest.py` + `test_fechas.py`
2. **Ronda 2**: `test_polars_utils.py`
3. **Ronda 3**: `test_transform.py`
4. **Ronda 4**: `test_validate_mapping.py`
