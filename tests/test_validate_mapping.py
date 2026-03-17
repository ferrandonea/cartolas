"""Tests para comparador/merge.py — _validate_custom_mapping"""

import polars as pl
import pytest

from comparador.merge import _validate_custom_mapping


def _make_elmer_df(rows: list[tuple[int, str]]) -> pl.LazyFrame:
    """Crea un LazyFrame fake de Elmer con NUM_CATEGORIA y CATEGORIA."""
    return pl.DataFrame(
        rows,
        schema={"NUM_CATEGORIA": pl.Int64, "CATEGORIA": pl.Utf8},
        orient="row",
    ).lazy()


# Categories mapping default (igual que en merge.py)
DEFAULT_CATEGORIES_MAPPING = {
    "BALANCEADO CONSERVADOR": 9810,
    "BALANCEADO MODERADO": 9809,
    "BALANCEADO AGRESIVO": 9811,
    "DEUDA CORTO PLAZO NACIONAL": 9810,
}


class TestValidateCustomMapping:
    def test_valid_mapping(self):
        elmer_df = _make_elmer_df([
            (17, "ACCIONARIO NACIONAL"),
            (20, "DEUDA LARGO PLAZO"),
        ])
        result = _validate_custom_mapping(
            custom_mapping={9810: 17},
            custom_categories=[17],
            categories_mapping=DEFAULT_CATEGORIES_MAPPING,
            elmer_df=elmer_df,
        )
        assert result == {17: "ACCIONARIO NACIONAL"}

    def test_duplicate_target_categories_raises(self):
        elmer_df = _make_elmer_df([
            (17, "ACCIONARIO NACIONAL"),
        ])
        with pytest.raises(ValueError, match="múltiples fondos"):
            _validate_custom_mapping(
                custom_mapping={9809: 17, 9810: 17},  # ambos apuntan a 17
                custom_categories=[17],
                categories_mapping=DEFAULT_CATEGORIES_MAPPING,
                elmer_df=elmer_df,
            )

    def test_conflict_with_default_category_raises(self):
        # Mapear fondo 9999 a categoría "BALANCEADO MODERADO" (default de 9809)
        elmer_df = _make_elmer_df([
            (50, "BALANCEADO MODERADO"),
        ])
        with pytest.raises(ValueError, match="categoría default"):
            _validate_custom_mapping(
                custom_mapping={9999: 50},
                custom_categories=[50],
                categories_mapping=DEFAULT_CATEGORIES_MAPPING,
                elmer_df=elmer_df,
            )

    def test_conflict_resolved_when_both_remapped(self):
        # Si el fondo default también está en custom_mapping, no hay conflicto
        elmer_df = _make_elmer_df([
            (50, "BALANCEADO MODERADO"),
            (17, "ACCIONARIO NACIONAL"),
        ])
        result = _validate_custom_mapping(
            custom_mapping={9999: 50, 9809: 17},  # 9809 también remapeado
            custom_categories=[50, 17],
            categories_mapping=DEFAULT_CATEGORIES_MAPPING,
            elmer_df=elmer_df,
        )
        assert 50 in result
        assert 17 in result

    def test_category_not_in_elmer_returns_empty(self):
        # NUM_CATEGORIA que no existe en elmer_df → no aparece en resultado
        elmer_df = _make_elmer_df([
            (17, "ACCIONARIO NACIONAL"),
        ])
        result = _validate_custom_mapping(
            custom_mapping={9810: 999},  # 999 no existe en elmer
            custom_categories=[999],
            categories_mapping=DEFAULT_CATEGORIES_MAPPING,
            elmer_df=elmer_df,
        )
        assert result == {}
