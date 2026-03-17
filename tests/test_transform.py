"""Tests para cartolas/transform.py"""

from pathlib import Path

import polars as pl
import pytest

from cartolas.config import SCHEMA, COLUMNAS_BOOLEAN, COLUMNAS_NULL, SORTING_ORDER
from cartolas.transform import transform_single_cartola, transform_cartola_folder

# Header del CSV tal como viene de CMF (separado por ;)
CSV_HEADER = ";".join(SCHEMA.keys())

# Fila de ejemplo con datos válidos
SAMPLE_ROW = ";".join([
    "1000",           # RUN_ADM
    "Admin Prueba",   # NOM_ADM
    "9809",           # RUN_FM
    "20240115",       # FECHA_INF
    "1000000.0",      # ACTIVO_TOT
    "PESOS",          # MONEDA
    "S",              # PARTICIPES_INST
    "500000.0",       # INVERSION_EN_FONDOS
    "A",              # SERIE
    "100.0",          # CUOTAS_APORTADAS
    "50.0",           # CUOTAS_RESCATADAS
    "1000.0",         # CUOTAS_EN_CIRCULACION
    "1500.50",        # VALOR_CUOTA
    "1500500.0",      # PATRIMONIO_NETO
    "200",            # NUM_PARTICIPES
    "5",              # NUM_PARTICIPES_INST
    "N",              # FONDO_PEN
    "0.01",           # REM_FIJA
    "0.02",           # REM_VARIABLE
    "0.005",          # GASTOS_AFECTOS
    "0.003",          # GASTOS_NO_AFECTOS
    "0.0",            # COMISION_INVERSION
    "0.0",            # COMISION_RESCATE
    "",               # FACTOR DE AJUSTE (null → 1)
    "",               # FACTOR DE REPARTO (null → 1)
])

SAMPLE_ROW_2 = ";".join([
    "1000", "Admin Prueba", "9810", "20240116", "2000000.0", "PESOS",
    "N", "800000.0", "B", "200.0", "100.0", "2000.0", "2500.75",
    "5001500.0", "300", "10", "S", "0.02", "0.03", "0.006", "0.004",
    "0.001", "0.001", "1.5", "1.2",
])


def _write_txt(path: Path, rows: list[str]) -> Path:
    """Escribe un archivo TXT tipo CMF."""
    content = CSV_HEADER + "\n" + "\n".join(rows) + "\n"
    path.write_text(content)
    return path


# --- transform_single_cartola ---


class TestTransformSingleCartola:
    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            transform_single_cartola(tmp_path / "no_existe.txt")

    def test_basic_transform(self, tmp_path):
        txt = _write_txt(tmp_path / "ffmm_test.txt", [SAMPLE_ROW])
        result = transform_single_cartola(txt).collect()

        assert result.shape[0] == 1
        # NOM_ADM debe estar dropeada
        assert "NOM_ADM" not in result.columns

    def test_fecha_parsed_as_date(self, tmp_path):
        txt = _write_txt(tmp_path / "ffmm_test.txt", [SAMPLE_ROW])
        result = transform_single_cartola(txt).collect()

        assert result["FECHA_INF"].dtype == pl.Date
        from datetime import date
        assert result["FECHA_INF"].to_list()[0] == date(2024, 1, 15)

    def test_boolean_columns_converted(self, tmp_path):
        txt = _write_txt(tmp_path / "ffmm_test.txt", [SAMPLE_ROW])
        result = transform_single_cartola(txt).collect()

        # PARTICIPES_INST = "S" → True, FONDO_PEN = "N" → False
        assert result["PARTICIPES_INST"].to_list() == [True]
        assert result["FONDO_PEN"].to_list() == [False]

    def test_null_columns_filled_with_one(self, tmp_path):
        txt = _write_txt(tmp_path / "ffmm_test.txt", [SAMPLE_ROW])
        result = transform_single_cartola(txt).collect()

        # Campos vacíos → null → fill 1
        assert result["FACTOR DE AJUSTE"].to_list() == [1.0]
        assert result["FACTOR DE REPARTO"].to_list() == [1.0]

    def test_run_fm_serie_concatenated(self, tmp_path):
        txt = _write_txt(tmp_path / "ffmm_test.txt", [SAMPLE_ROW])
        result = transform_single_cartola(txt).collect()

        assert "RUN_FM_SERIE" in result.columns
        assert result["RUN_FM_SERIE"].to_list() == ["9809-A"]


# --- transform_cartola_folder ---


class TestTransformCartolaFolder:
    def test_multiple_files_concatenated(self, tmp_path):
        _write_txt(tmp_path / "ffmm_a.txt", [SAMPLE_ROW])
        _write_txt(tmp_path / "ffmm_b.txt", [SAMPLE_ROW_2])

        result = transform_cartola_folder(
            cartola_folder=tmp_path,
            wildcard="ffmm*.txt",
            sorting_order=SORTING_ORDER,
        ).collect()

        assert result.shape[0] == 2

    def test_unique_deduplicates(self, tmp_path):
        # Mismo archivo con misma fila → unique elimina duplicado
        _write_txt(tmp_path / "ffmm_a.txt", [SAMPLE_ROW])
        _write_txt(tmp_path / "ffmm_b.txt", [SAMPLE_ROW])

        result = transform_cartola_folder(
            cartola_folder=tmp_path,
            wildcard="ffmm*.txt",
            sorting_order=SORTING_ORDER,
            unique=True,
        ).collect()

        assert result.shape[0] == 1

    def test_no_unique_keeps_duplicates(self, tmp_path):
        _write_txt(tmp_path / "ffmm_a.txt", [SAMPLE_ROW])
        _write_txt(tmp_path / "ffmm_b.txt", [SAMPLE_ROW])

        result = transform_cartola_folder(
            cartola_folder=tmp_path,
            wildcard="ffmm*.txt",
            sorting_order=SORTING_ORDER,
            unique=False,
        ).collect()

        assert result.shape[0] == 2
