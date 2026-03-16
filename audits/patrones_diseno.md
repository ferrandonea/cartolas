# Auditoría de Patrones de Diseño

**Proyecto**: Cartolas - Análisis de Fondos Mutuos Chilenos
**Fecha**: 2026-03-16
**Alcance**: Todo el codebase (`cartolas/`, `comparador/`, `eco/`, `utiles/`, scripts raíz)

---

## Resumen Ejecutivo

El proyecto sigue un **paradigma funcional con pipelines lazy** (Polars LazyFrames). No utiliza clases ni OOP tradicional, por lo que muchos patrones GoF clásicos no aplican directamente. Sin embargo, se identifican patrones funcionales equivalentes, algunos bien implementados y otros con oportunidades de mejora.

---

## 1. PATRONES CREACIONALES

### 1.1 Singleton — Conexión BCCh (module-level)

**Ubicación**: `eco/bcentral.py:13-17`
**Implementación**: La conexión a la API del Banco Central se crea como variable de módulo:

```python
BCCh = bcchapi.Sieci(usr=BCCH_USER, pwd=BCCH_PASS)
DATOS_JSON = read_bcentral_tickers()
NOMBRES = list(DATOS_JSON.keys())
TICKERS = [DATOS_JSON[nombre]["TICKER"] for nombre in NOMBRES]
```

**Evaluación**: Es un "module-level singleton" implícito — Python garantiza que el módulo se ejecuta una sola vez. Funciona, pero tiene problemas:

- La conexión se crea **al importar el módulo**, incluso si no se usa.
- Si las credenciales fallan, el import completo falla sin contexto claro.
- No hay forma de recrear la conexión sin recargar el módulo.

**Importancia**: 5/10
**Remediación**:

```python
# eco/bcentral.py — lazy initialization
_bcch_client = None

def get_bcch_client() -> bcchapi.Sieci:
    global _bcch_client
    if _bcch_client is None:
        env = dotenv_values(".env")
        _bcch_client = bcchapi.Sieci(usr=env["BCCH_USER"], pwd=env["BCCH_PASS"])
    return _bcch_client
```

---

### 1.2 Factory Pattern — Ausente

**Evaluación**: No hay factories. La creación de objetos (LazyFrames, DataFrames) es directa vía `pl.scan_parquet()`, `pl.scan_csv()`, etc. Dado el paradigma funcional del proyecto, **no se necesitan factories**. Polars ya actúa como factory de DataFrames.

**Importancia**: 1/10 — No aplica.

---

### 1.3 Builder Pattern — Ausente

**Evaluación**: No hay builders explícitos. Sin embargo, las cadenas de `.with_columns()` en `cartolas/soyfocus.py:50-150` y `comparador/merge.py:40-120` actúan como un **builder implícito** de LazyFrames. Esto es idiomático en Polars y correcto.

**Importancia**: 1/10 — El patrón de encadenamiento de Polars es el builder natural aquí.

---

## 2. PATRONES ESTRUCTURALES

### 2.1 Decorator Pattern — Bien implementado

**Ubicación**: `utiles/decorators.py`
**Implementación**: Tres decoradores: `@retry_function`, `@exp_retry_function`, `@timer`.

**Uso en el código**:
| Decorador | Archivo | Función |
|-----------|---------|---------|
| `@retry_function` | `cartolas/download.py` | `goto_with_retry()` |
| `@exp_retry_function` + `@retry_function` | `cartolas/download.py` | `get_cartola_from_cmf()` |
| `@timer` | `cartolas/save.py` | `save_lazyframe_to_parquet()` |
| `@timer` | `cartolas/update.py` | `update_parquet()` |
| `@timer` | `cartolas/update_by_year.py` | `update_parquet_by_year()` |
| `@timer` | `comparador/cla_monthly.py` | Múltiples funciones |

**Evaluación**: Correctamente implementado. El stacking de decoradores en `download.py` es apropiado para scraping con captchas.

**Problema menor**: `@retry_function` y `@exp_retry_function` no usan `@wraps(func)`, lo que pierde metadata de la función original.

**Importancia**: 3/10

**Remediación**:

```python
# utiles/decorators.py — agregar @wraps en retry_function
from functools import wraps

def retry_function(func=None, max_attempts=10, delay=10):
    def decorator(f):
        @wraps(f)  # <-- agregar esto
        def wrapper(*args, **kwargs):
            # ... lógica existente
        return wrapper
    if func is not None:
        return decorator(func)
    return decorator
```

---

### 2.2 Facade Pattern — Presente en múltiples niveles

**Ubicaciones**:

| Facade | Archivo | Complejidad oculta |
|--------|---------|-------------------|
| `update_parquet()` | `cartolas/update.py` | Download + Transform + Read + Concat + Save + Cleanup |
| `update_parquet_by_year()` | `cartolas/update_by_year.py` | Lo mismo, particionado por año |
| `merge_cartolas_with_categories()` | `comparador/merge.py` | Cartolas + BCCh + Elmer merge |
| `generate_cla_data()` | `comparador/cla_monthly.py` | Pipeline completo de 9 pasos |
| `update_bcch_for_cartolas()` | `eco/bcentral.py` | API BCCh + transform + unpivot |

**Evaluación**: Excelente uso del patrón. Los scripts raíz (`actualiza_parquet.py`, `cla_mensual.py`) son orquestradores de 3-5 líneas gracias a estas facades.

**Importancia**: 2/10 — Bien implementado, sin cambios necesarios.

---

### 2.3 Adapter Pattern — Parcial

**Ubicación**: `eco/bcentral.py`
**Evaluación**: `baja_bcch_as_polars()` adapta la salida de `bcchapi` (pandas DataFrame) al ecosistema Polars del proyecto. `update_bcch_for_cartolas()` además transforma el esquema (rename + unpivot) para hacerlo compatible con el join de cartolas.

```python
# eco/bcentral.py — adapter bcchapi (pandas) → Polars
def baja_bcch_as_polars(...):
    df_pandas = baja_datos_bcch(...)          # API → pandas
    df_polars = pl.from_pandas(df_pandas, include_index=True)  # pandas → Polars
    return df_polars
```

**Problema**: `comparador/elmer.py` también adapta una API externa (El Mercurio JSON → Polars), pero la conversión es menos limpia: pasa por `list[dict]` intermedio en vez de ir directo a LazyFrame.

**Importancia**: 4/10

**Remediación para `elmer.py`**:

```python
# comparador/elmer.py — evitar paso intermedio list[dict]
def get_all_elmer_data_as_polars(max_number: int = 30) -> pl.LazyFrame:
    """Descarga y convierte directamente a LazyFrame."""
    all_data = get_all_elmer_data(max_number)
    if not all_data:
        return pl.LazyFrame()
    return pl.LazyFrame(all_data).cast({"RUN_FM": pl.UInt16})
```

Actualmente `last_elmer_data_as_polars()` ya hace esto pero **siempre pasa por disco** (guarda JSON y luego lee). Para datos que cambian mensualmente, esto es aceptable pero innecesariamente acoplado.

---

### 2.4 Proxy Pattern / Lazy Loading — Nativo de Polars

**Evaluación**: Todo el pipeline usa `pl.scan_parquet()` y `pl.scan_csv()` que son **lazy proxies** nativos de Polars. Los datos no se cargan hasta `.collect()`. Esto es correcto e idiomático.

`cartolas/read.py:read_parquet_cartolas_lazy()` es explícitamente un proxy lazy:

```python
def read_parquet_cartolas_lazy(parquet_path, sorted=True) -> pl.LazyFrame:
    return pl.scan_parquet(parquet_path)  # No lee datos aún
```

**Importancia**: 1/10 — Perfecto, no necesita cambios.

---

## 3. PATRONES DE COMPORTAMIENTO

### 3.1 Strategy Pattern — Ausente (oportunidad)

**Evaluación**: No hay strategy pattern explícito. Se podría beneficiar de él en:

1. **Estrategias de retry**: `retry_function` y `exp_retry_function` son funciones separadas en vez de estrategias intercambiables.
2. **Estrategias de export**: `cla_monthly.py` tiene `excel_steps: Literal["all", "minimal", "none"]` implementado con `if/elif`, no como estrategia.

**Importancia**: 2/10 — La complejidad actual no justifica Strategy formal. Los `if/elif` son suficientes.

---

### 3.2 Observer Pattern — Ausente

**Evaluación**: No hay sistema de eventos. Los decoradores `@timer` imprimen directamente a stdout. No hay logging estructurado ni notificaciones.

**Importancia**: 3/10

**Remediación sugerida** (no urgente):

```python
# Reemplazar prints por logging estándar
import logging
logger = logging.getLogger(__name__)

# En vez de: print(f"Guardado en {filename}")
# Usar:     logger.info(f"Guardado en {filename}")
```

Esto permitiría después conectar handlers (archivo, email, etc.) sin modificar código.

---

### 3.3 Chain of Responsibility — Ausente

**Evaluación**: No hay cadena de responsabilidad. El stacking de decoradores `@exp_retry_function` + `@retry_function` en `download.py` podría verse como una mini-cadena, pero es más un patrón de decoradores anidados.

**Importancia**: 1/10 — No aplica al dominio.

---

### 3.4 Command Pattern — Ausente (oportunidad menor)

**Evaluación**: Los scripts raíz (`actualiza_parquet.py`, `cla_mensual.py`, etc.) son comandos ejecutables pero no siguen el patrón Command formal. Cada script es un procedimiento lineal.

**Importancia**: 2/10 — Para un proyecto de análisis de datos sin UI, Command pattern no aporta valor.

---

## 4. PATRONES DE DOMINIO

### 4.1 Repository Pattern — Parcial e inconsistente

**Evaluación**: Las funciones de acceso a datos están distribuidas en múltiples módulos sin una interfaz unificada:

| Operación | Función | Archivo |
|-----------|---------|---------|
| Read cartolas | `read_parquet_cartolas_lazy()` | `cartolas/read.py` |
| Save cartolas | `save_lazyframe_to_parquet()` | `cartolas/save.py` |
| Read BCCh | `load_bcch_from_parquet()` | `eco/bcentral.py` |
| Save BCCh | `save_bcch_as_parquet()` | `eco/bcentral.py` |
| Read Elmer | `last_elmer_data()` / `leer_json()` | `comparador/elmer.py` / `utiles/file_tools.py` |
| Save Elmer | `save_elmer_data()` | `comparador/elmer.py` |

**Problemas**:
- No hay interfaz común para lectura/escritura
- BCCh tiene read/save en el mismo archivo; cartolas los separa en `read.py`/`save.py`
- Elmer usa JSON como almacenamiento, el resto usa Parquet
- Las rutas de archivos están hardcodeadas en `config.py` pero se pasan como parámetros inconsistentemente

**Importancia**: 5/10

**Remediación**: Unificar la convención de acceso a datos. No necesita un Repository formal, pero sí consistencia:

```python
# Convención sugerida: cada módulo de datos tiene read/save pareados
# eco/bcentral.py ya lo hace bien:
#   save_bcch_as_parquet() + load_bcch_from_parquet()
#
# cartolas/ lo separa innecesariamente en dos archivos:
#   read.py (read_parquet_cartolas_lazy) + save.py (save_lazyframe_to_parquet)
#
# Mover save.py → dentro de read.py (o crear cartolas/storage.py)
# para tener read + save pareados en un solo lugar.
```

---

### 4.2 Service Layer — Implícito en scripts raíz

**Evaluación**: Los scripts raíz actúan como "servicios" de orquestación:

```
actualiza_parquet.py    → servicio de actualización diaria
actualiza_parquet_year.py → servicio de actualización histórica
cla_mensual.py          → servicio de reporte mensual
soyfocus.py             → servicio de análisis SoyFocus
```

Cada uno sigue el patrón: **update data → process → export**. Esto es correcto para el contexto.

**Problema**: `cla_mensual.py` y `cla_mensual2.py` duplican lógica de orquestación (ambos hacen update + update_bcch + generate_cla_data). La única diferencia es el `custom_mapping`.

**Importancia**: 4/10

**Remediación**:

```python
# cla_mensual.py — función reutilizable
def run_cla_report(
    custom_mapping: dict[int, int] | None = None,
    output_folder: str = "cla_mensual",
    prefix: str = "cla",
):
    report_date = ultimo_dia_mes_anterior(date.today())
    folder = Path(output_folder)
    folder.mkdir(exist_ok=True)
    excel_path = folder / f"{prefix}_{report_date.strftime('%Y%m%d')}.xlsx"

    update_parquet_by_year()
    update_bcch_parquet()
    generate_cla_data(
        custom_mapping=custom_mapping,
        save_xlsx=True,
        xlsx_name=str(excel_path),
        excel_steps="minimal",
    )

# cla_mensual.py: run_cla_report()
# cla_mensual2.py: run_cla_report(custom_mapping={9810: 17}, output_folder="cla_mensual2", prefix="cla2")
```

---

### 4.3 DTO / Value Objects — Ausente

**Evaluación**: No hay DTOs ni Value Objects. Todo se maneja como LazyFrames/DataFrames sin tipado de dominio. Las columnas se referencian por strings mágicos (`"RUN_FM"`, `"FECHA_INF"`, etc.) dispersos por todo el código.

**Problema concreto**: El nombre de columna `"FECHA_INF"` aparece en al menos 15 archivos. Un typo causaría un error silencioso en Polars (columna no encontrada en runtime).

**Importancia**: 6/10

**Remediación**: Centralizar nombres de columnas como constantes (ya hay precedente parcial en `config.py`):

```python
# cartolas/config.py — agregar constantes de columnas
class Col:
    """Nombres de columnas centralizados."""
    FECHA = "FECHA_INF"
    RUN_FM = "RUN_FM"
    RUN_ADM = "RUN_ADM"
    SERIE = "SERIE"
    VALOR_CUOTA = "VALOR_CUOTA"
    PATRIMONIO = "PATRIMONIO_NETO"
    MONEDA = "MONEDA"
    # ... etc

# Uso: pl.col(Col.FECHA) en vez de pl.col("FECHA_INF")
```

---

### 4.4 Domain Model — No aplica

**Evaluación**: El proyecto no tiene modelo de dominio OOP (no hay clases `Fund`, `Cartola`, `Series`, etc.). Todo se modela como filas en DataFrames. Esto es **correcto para un pipeline de datos** — un modelo de dominio OOP agregaría complejidad sin beneficio dado que Polars ya maneja la lógica relacional eficientemente.

**Importancia**: 1/10 — No se necesita.

---

## 5. PATRONES ADICIONALES IDENTIFICADOS

### 5.1 Pipeline Pattern — Columna vertebral del proyecto

**Evaluación**: El patrón más importante del proyecto. Todo sigue el flujo:

```
Download → Transform → Save → Read → Analyze → Export
```

Cada paso recibe y retorna LazyFrames, permitiendo composición funcional. Implementado correctamente.

**Importancia**: 1/10 — Bien hecho.

---

### 5.2 Smart Cache — Elmer con refresh mensual

**Ubicación**: `comparador/elmer.py:last_elmer_data()`

```python
def last_elmer_data(elmerfolder, verbose):
    archivo = obtener_archivo_mas_reciente(elmerfolder)
    if archivo and es_mismo_mes(obtener_fecha_creacion(archivo)):
        return leer_json(archivo)       # Cache hit
    return get_and_save_elmer_data()    # Cache miss → download
```

**Evaluación**: Funciona, pero la lógica de caché está mezclada con la lógica de negocio. El criterio "mismo mes" está hardcodeado.

**Importancia**: 3/10

---

### 5.3 Idempotent Update — Bien implementado

**Ubicación**: `cartolas/update.py`, `cartolas/update_by_year.py`

**Evaluación**: Las funciones de actualización calculan `missing_dates = all_dates - existing_dates` y solo descargan lo faltante. Pueden ejecutarse múltiples veces sin duplicar datos. Correcto y robusto.

**Importancia**: 1/10 — Excelente implementación.

---

### 5.4 Expression Factory — Polars idiomático

**Ubicación**: `cartolas/polars_utils.py`

```python
def map_s_n_to_bool(column_name: str) -> pl.Expr:
    return pl.when(pl.col(column_name) == "S").then(True)...

def replace_null_with_one(column_name: str) -> pl.Expr:
    return pl.col(column_name).fill_null(1).alias(column_name)
```

**Evaluación**: Patrón factory para expresiones Polars. Correcto y reutilizable. Solo tiene 2 funciones — podría expandirse para las expresiones repetidas en `soyfocus.py` y `merge.py`.

**Importancia**: 3/10

**Remediación**: Extraer expresiones financieras repetidas:

```python
# cartolas/polars_utils.py — agregar expresiones financieras comunes
def shifted_over(col_name: str, group_cols: list[str], n: int = 1) -> pl.Expr:
    """Valor del período anterior, particionado por grupo."""
    return pl.col(col_name).shift(n).over(group_cols).alias(f"{col_name}_ANTERIOR")
```

---

## 6. PATRONES AUSENTES QUE MEJORARÍAN EL CÓDIGO

### 6.1 Configuration Object en vez de módulo plano

**Problema**: `cartolas/config.py` es un módulo con ~30 variables globales. Algunas se calculan dinámicamente al importar (`FECHA_MAXIMA`, `DIAS_ATRAS`), lo que hace testing difícil.

**Importancia**: 4/10

**Remediación**:

```python
# cartolas/config.py — encapsular en dataclass para testabilidad
from dataclasses import dataclass, field

@dataclass
class Config:
    fecha_minima: date = date(2007, 12, 31)
    initial_date_range: int = 33
    verbose: bool = True

    @property
    def dias_atras(self) -> int:
        return 1 if datetime.now().hour > 10 else 2

    @property
    def fecha_maxima(self) -> date:
        return datetime.now().date() - timedelta(days=self.dias_atras)

# Singleton por defecto, pero overrideable en tests
config = Config()
```

---

### 6.2 Logging estructurado en vez de print()

**Problema**: Todo el proyecto usa `print()` para feedback. Esto dificulta filtrar niveles de verbosidad, redirigir a archivos, o integrar con sistemas de monitoreo.

**Archivos afectados**: `download.py`, `update.py`, `update_by_year.py`, `save.py`, `elmer.py`, `cla_monthly.py`, `merge.py`.

**Importancia**: 5/10

**Remediación**: Migrar gradualmente a `logging`:

```python
import logging
logger = logging.getLogger("cartolas")

# Reemplazar print("Guardado exitosamente")
# Por:       logger.info("Guardado exitosamente")
```

---

## Tabla Resumen

| # | Patrón | Estado | Importancia | Acción |
|---|--------|--------|:-----------:|--------|
| 1.1 | Singleton (BCCh) | Implícito, frágil | 5/10 | Lazy init con función |
| 1.2 | Factory | No necesario | 1/10 | Ninguna |
| 1.3 | Builder | Implícito (Polars chains) | 1/10 | Ninguna |
| 2.1 | Decorator | Bien implementado | 3/10 | Agregar `@wraps` |
| 2.2 | Facade | Excelente | 2/10 | Ninguna |
| 2.3 | Adapter | Parcial | 4/10 | Limpiar adapter Elmer |
| 2.4 | Proxy/Lazy | Nativo Polars | 1/10 | Ninguna |
| 3.1 | Strategy | No necesario | 2/10 | Ninguna |
| 3.2 | Observer | Ausente | 3/10 | Migrar a `logging` |
| 3.3 | Chain of Resp. | No aplica | 1/10 | Ninguna |
| 3.4 | Command | No aplica | 2/10 | Ninguna |
| 4.1 | Repository | Inconsistente | 5/10 | Unificar read/save |
| 4.2 | Service Layer | Duplicado | 4/10 | Extraer función común CLA |
| 4.3 | DTO/Value Objects | Strings mágicos | 6/10 | Constantes de columnas |
| 4.4 | Domain Model | No necesario | 1/10 | Ninguna |
| 5.1 | Pipeline | Excelente | 1/10 | Ninguna |
| 5.2 | Smart Cache | Funcional | 3/10 | Aceptable |
| 5.3 | Idempotent Update | Excelente | 1/10 | Ninguna |
| 5.4 | Expression Factory | Correcto, expandible | 3/10 | Agregar expr. financieras |
| 6.1 | Config Object | Ausente | 4/10 | Dataclass config |
| 6.2 | Logging | Ausente (usa print) | 5/10 | Migrar a `logging` |

---

## Top 5 Acciones Prioritarias

1. **[6/10] Constantes de columnas** — Eliminar strings mágicos con clase `Col` en `config.py`
2. **[5/10] Lazy init BCCh** — Evitar conexión al importar módulo
3. **[5/10] Repository consistente** — Unificar convención read/save por dominio
4. **[5/10] Logging** — Reemplazar `print()` por `logging` estándar
5. **[4/10] Deduplicar CLA** — Extraer función `run_cla_report()` compartida
