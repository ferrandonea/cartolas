# Plan de mejoras — Cartolas

## Diagnóstico

### Propósito

Sistema de análisis financiero para **fondos mutuos chilenos**, orientado a los fondos **SoyFocus** (Moderado/Conservador/Arriesgado). Pipeline completo: scraping CMF con resolución de captcha → transformación a Parquet → enriquecimiento con datos BCCh y categorización El Mercurio → generación de reportes CLA mensuales en Excel.

### Corazón del sistema

1. **`cartolas/config.py`** — Todo parte de aquí: rutas, esquema, constantes
2. **`cartolas/download.py` + `captcha.py`** — Scraping con Playwright + ONNX, la parte más técnicamente compleja
3. **`comparador/cla_monthly.py`** (606 líneas) — Generador de reportes CLA, lógica de negocio más densa
4. **`comparador/merge.py`** — Join entre cartolas, BCCh y categorías Elmer; si falla, todo el análisis cae
5. **`cartolas/soyfocus.py`** (429 líneas) — Cálculos financieros (TAC, TDC, rentabilidades)

### Fragilidades

- **`download.py`**: No valida que el archivo descargado tenga contenido real (`"ACA FALTA CHEQUEAR EL TAMAÑO"`). Retry doble (exponencial + fijo) apilado, potencialmente redundante.
- **`eco/bcentral.py`**: Inicializa conexión a BCCh **al importar el módulo**. Si falta `.env` o la API está caída, el import crashea y arrastra todo lo que dependa de `eco`.
- **`comparador/elmer.py`**: Errores de la API se tragan silenciosamente (retorna `None`). `MAX_NUMBER_OF_CATEGORIES=30` sin documentar.
- **`fund_identifica.py`**: Función `cmf_to_pl()` nunca usada, ~60 líneas de debug comentado, firma `-> str` que retorna `DataFrame`.

### Inconsistencias

**Duplicación de código (problema más grave):**
- `add_cumulative_returns()` copiada en 3 archivos: `cla_monthly.py`, `cla_monthly_new_conservador.py`, `tablas.py`
- `cla_monthly_new_conservador.py` es copy-paste del 95% de `cla_monthly.py`

**Mezcla de paradigmas de datos:**
- Pipeline dice "Polars LazyFrames everywhere", pero `bcentral.py` retorna Pandas y convierte. `tablas.py` usa NumPy. `cla_monthly.py` alterna LazyFrame/DataFrame/Pandas en la misma función.

**Error handling inconsistente:**
- `file_tools.py` y `elmer.py`: defensivo, con try/except y fallbacks
- `merge.py`, `cla_monthly.py`, `soyfocus.py`: cero validación, asumen datos perfectos
- `decorators.py`: captura **todas** las excepciones — puede ocultar bugs

**Otros:**
- `__init__.py` vacíos en todos los paquetes
- `listas.py` tiene 1 función de 3 líneas
- Archivos borrados en git pero presentes: `cla_monthly_new_conservador.py`, `cla_new.py`
- Reportes Excel de 94-341MB (Parquet + template sería más eficiente)
- Fechas hardcodeadas de 2024 en `tablas.py` y `resumen_apv.py`

---

## Quick Wins (< 1 hora cada uno)

| # | Mejora | Impacto | Esfuerzo | Archivos |
|---|--------|---------|----------|----------|
| Q1 | ~~Eliminar `economy.py`~~ **DONE** | Bajo | 5 min | `cartolas/economy.py` |
| Q2 | ~~Eliminar archivos huérfanos~~ **DONE**: se eliminó `cla_mensual copy.py` y `cla_mensual/datostablacla_new.xlsx`. `cla_monthly_custom.py` y `cla_new.py` ya no existían. | Bajo | 5 min | raíz + `cla_mensual/` |
| Q3 | ~~Borrar `cla_monthly_new_conservador.py`~~ **DONE** | Medio | 15 min | `comparador/` |
| Q4 | ~~Mover `add_cumulative_returns()` a `utiles/polars_utils.py`~~ **DONE** | Medio | 20 min | `cla_monthly.py`, `tablas.py` |
| Q5 | ~~Limpiar código de debug~~ **DONE**: eliminada `cmf_to_pl()` muerta y `__main__` de `fund_identifica.py` y `tablas.py` | Bajo | 15 min | 2 archivos |
| Q6 | ~~Corregir firma `-> str` a `-> pl.DataFrame`~~ **DONE** | Bajo | 5 min | `fund_identifica.py` |
| Q7 | ~~Absorber `listas.py` en `merge.py`~~ **DONE**: inlined con `reduce(mul, ...)`, eliminado `utiles/listas.py` | Bajo | 10 min | `comparador/merge.py` |

---

## Mejoras medianas (1-4 horas cada una)

| # | Mejora | Impacto | Esfuerzo | Archivos |
|---|--------|---------|----------|----------|
| M1 | ~~**Lazy-load de BCCh**~~ **DONE**: credenciales, cliente y tickers con `lru_cache`, login solo al primer uso | Alto | 1h | `eco/bcentral.py` |
| M2 | ~~**Manejo de errores en Elmer**~~ **DONE**: retry con backoff exponencial, timeout, logging, reporte de categorías fallidas | Alto | 1.5h | `comparador/elmer.py` |
| M3 | ~~**Validación en `download.py`**~~ **DONE**: valida tamaño post-descarga, retry explícito con backoff (5 intentos), elimina doble decorador, logging | Alto | 2h | `cartolas/download.py` |
| M4 | **Eliminar mezcla Pandas/NumPy** — **DESCARTADO**: `bcentral.py` no tocable (Pandas viene de bcchapi), `tablas.py` sin cambios (NumPy correcto para semántica NaN en estadísticas por fila) | Medio | — | — |
| M5 | ~~**Parametrizar fechas hardcodeadas**~~ **DONE**: fechas dinámicas con funciones de `utiles/fechas.py` | Medio | 1h | `tablas.py`, `resumen_apv.py` |
| M6 | ~~**Email a `.env`**~~ **DONE**: config.py lee SENDER_MAIL, SENDER_NAME, TO_EMAILS desde `.env` con fallback | Bajo | 30 min | `cartolas/config.py` |
| M7 | **Consolidar `update.py` y `update_by_year.py`**: 80% de lógica duplicada, refactorizar a una función parametrizada | Medio | 2h | `cartolas/update.py`, `cartolas/update_by_year.py` |

---

## Cambios estructurales (1+ días)

| # | Mejora | Impacto | Esfuerzo | Alcance |
|---|--------|---------|----------|---------|
| E1 | **Tests**: agregar tests unitarios para funciones puras (transform, fechas, polars_utils, merge) — el proyecto no tiene ninguno | Muy alto | 2-3 días | Nuevo directorio `tests/` |
| E2 | **Reportes livianos**: reemplazar Excel de 94-341MB por Parquet + template Excel pequeño, o exportar solo los datos necesarios | Alto | 1 día | `comparador/cla_monthly.py` |
| E3 | **CLI unificado**: reemplazar 5 scripts raíz sueltos por un CLI con `click` o `typer` (`cartolas update`, `cartolas report cla`, etc.) | Medio | 1 día | Scripts raíz + nuevo `cli.py` |
| E4 | **Logging**: reemplazar `print()` en decoradores y pipeline por `logging` con niveles configurables | Medio | 0.5 día | Todos los módulos |
| E5 | **`__init__.py` con exports**: definir API pública de cada paquete para simplificar imports | Bajo | 2h | 4 `__init__.py` |
| E6 | **Resolver imports circulares**: eliminar el late-import de `file_tools` en `config.py` reestructurando dependencias | Medio | 3h | `config.py`, `file_tools.py` |

---

## Orden sugerido de ejecución

1. **Primero los quick wins** Q1→Q3→Q4 (limpiar el ruido antes de tocar lógica)
2. **Luego M1 + M2 + M3** (las fragilidades que pueden causar fallos en producción)
3. **Después M4 + M7** (consistencia interna del pipeline)
4. **Finalmente E1** (tests antes de hacer cambios estructurales mayores)
