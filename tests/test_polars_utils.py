"""Tests para cartolas/polars_utils.py y utiles/polars_utils.py"""

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from cartolas.polars_utils import map_s_n_to_bool, replace_null_with_one
from utiles.polars_utils import add_cumulative_returns


# --- map_s_n_to_bool ---


class TestMapSNToBool:
    def test_s_maps_to_true(self):
        df = pl.DataFrame({"col": ["S"]})
        result = df.with_columns(map_s_n_to_bool("col"))
        assert result["col"].to_list() == [True]

    def test_n_maps_to_false(self):
        df = pl.DataFrame({"col": ["N"]})
        result = df.with_columns(map_s_n_to_bool("col"))
        assert result["col"].to_list() == [False]

    def test_other_value_maps_to_null(self):
        df = pl.DataFrame({"col": ["X"]})
        result = df.with_columns(map_s_n_to_bool("col"))
        assert result["col"].to_list() == [None]

    def test_empty_string_maps_to_null(self):
        df = pl.DataFrame({"col": [""]})
        result = df.with_columns(map_s_n_to_bool("col"))
        assert result["col"].to_list() == [None]

    def test_lowercase_maps_to_null(self):
        df = pl.DataFrame({"col": ["s", "n"]})
        result = df.with_columns(map_s_n_to_bool("col"))
        assert result["col"].to_list() == [None, None]

    def test_mixed_values(self):
        df = pl.DataFrame({"col": ["S", "N", "S", "X"]})
        result = df.with_columns(map_s_n_to_bool("col"))
        assert result["col"].to_list() == [True, False, True, None]

    def test_preserves_column_name(self):
        df = pl.DataFrame({"MI_COL": ["S", "N"]})
        result = df.with_columns(map_s_n_to_bool("MI_COL"))
        assert "MI_COL" in result.columns


# --- replace_null_with_one ---


class TestReplaceNullWithOne:
    def test_null_becomes_one(self):
        df = pl.DataFrame({"col": [1.5, None, 2.0]})
        result = df.with_columns(replace_null_with_one("col"))
        assert result["col"].to_list() == [1.5, 1.0, 2.0]

    def test_no_nulls_unchanged(self):
        df = pl.DataFrame({"col": [1.5, 2.0, 3.0]})
        result = df.with_columns(replace_null_with_one("col"))
        assert result["col"].to_list() == [1.5, 2.0, 3.0]

    def test_all_nulls(self):
        df = pl.DataFrame({"col": [None, None, None]}, schema={"col": pl.Float64})
        result = df.with_columns(replace_null_with_one("col"))
        assert result["col"].to_list() == [1.0, 1.0, 1.0]

    def test_preserves_column_name(self):
        df = pl.DataFrame({"FACTOR DE AJUSTE": [None, 1.5]})
        result = df.with_columns(replace_null_with_one("FACTOR DE AJUSTE"))
        assert "FACTOR DE AJUSTE" in result.columns


# --- add_cumulative_returns ---


class TestAddCumulativeReturns:
    def test_single_fund_series(self):
        df = pl.DataFrame({
            "RUN_FM": [1, 1, 1],
            "SERIE": ["A", "A", "A"],
            "FECHA_INF": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "RENTABILIDAD_DIARIA_PESOS": [1.01, 1.02, 1.03],
        }).with_columns(pl.col("FECHA_INF").str.strptime(pl.Date, "%Y-%m-%d"))
        result = add_cumulative_returns(df)
        assert "RENTABILIDAD_ACUMULADA" in result.columns
        acum = result["RENTABILIDAD_ACUMULADA"].to_list()
        assert acum[0] == pytest.approx(1.01)
        assert acum[1] == pytest.approx(1.01 * 1.02)
        assert acum[2] == pytest.approx(1.01 * 1.02 * 1.03)

    def test_multiple_funds_partitioned(self):
        df = pl.DataFrame({
            "RUN_FM": [1, 1, 2, 2],
            "SERIE": ["A", "A", "A", "A"],
            "FECHA_INF": ["2024-01-01", "2024-01-02", "2024-01-01", "2024-01-02"],
            "RENTABILIDAD_DIARIA_PESOS": [1.10, 1.20, 1.05, 1.03],
        }).with_columns(pl.col("FECHA_INF").str.strptime(pl.Date, "%Y-%m-%d"))
        result = add_cumulative_returns(df)
        # Fondo 1: 1.10, 1.10*1.20=1.32
        fund1 = result.filter(pl.col("RUN_FM") == 1)["RENTABILIDAD_ACUMULADA"].to_list()
        assert fund1[0] == pytest.approx(1.10)
        assert fund1[1] == pytest.approx(1.10 * 1.20)
        # Fondo 2: 1.05, 1.05*1.03=1.0815
        fund2 = result.filter(pl.col("RUN_FM") == 2)["RENTABILIDAD_ACUMULADA"].to_list()
        assert fund2[0] == pytest.approx(1.05)
        assert fund2[1] == pytest.approx(1.05 * 1.03)

    def test_nan_propagates_then_fills_one(self):
        # NaN en cum_prod propaga NaN a filas siguientes; fill_nan(1) las reemplaza
        df = pl.DataFrame({
            "RUN_FM": [1, 1],
            "SERIE": ["A", "A"],
            "FECHA_INF": ["2024-01-01", "2024-01-02"],
            "RENTABILIDAD_DIARIA_PESOS": [float("nan"), 1.05],
        }).with_columns(pl.col("FECHA_INF").str.strptime(pl.Date, "%Y-%m-%d"))
        result = add_cumulative_returns(df)
        acum = result["RENTABILIDAD_ACUMULADA"].to_list()
        assert acum[0] == 1.0  # NaN → fill 1
        assert acum[1] == 1.0  # NaN propagado por cum_prod → fill 1

    def test_null_filled_with_one(self):
        df = pl.DataFrame({
            "RUN_FM": [1, 1],
            "SERIE": ["A", "A"],
            "FECHA_INF": ["2024-01-01", "2024-01-02"],
            "RENTABILIDAD_DIARIA_PESOS": [None, 1.05],
        }, schema={
            "RUN_FM": pl.Int64,
            "SERIE": pl.Utf8,
            "FECHA_INF": pl.Utf8,
            "RENTABILIDAD_DIARIA_PESOS": pl.Float64,
        }).with_columns(pl.col("FECHA_INF").str.strptime(pl.Date, "%Y-%m-%d"))
        result = add_cumulative_returns(df)
        acum = result["RENTABILIDAD_ACUMULADA"].to_list()
        assert acum[0] == 1.0  # null → fill 1
