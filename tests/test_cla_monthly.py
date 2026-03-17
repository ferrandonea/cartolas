"""Tests para comparador/cla_monthly.py — firma y deprecation de generate_cla_data"""

import inspect
import warnings
from unittest.mock import patch

import pytest

from comparador.cla_monthly import generate_cla_data


class _StopPipeline(Exception):
    """Excepción centinela para cortar el pipeline antes de tocar datos."""


# Patch que detiene la ejecución justo después del check de excel_steps
_PATCH_TARGET = "comparador.cla_monthly.generate_cla_dates"


class TestExcelStepsDeprecation:
    def test_no_warning_when_none(self):
        """excel_steps=None (default) no emite warning."""
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with patch(_PATCH_TARGET, side_effect=_StopPipeline):
                with pytest.raises(_StopPipeline):
                    generate_cla_data(excel_steps=None)

    def test_warning_when_value_passed(self):
        """excel_steps con valor distinto de None emite DeprecationWarning."""
        with patch(_PATCH_TARGET, side_effect=_StopPipeline):
            with pytest.warns(DeprecationWarning, match="excel_steps está deprecated"):
                with pytest.raises(_StopPipeline):
                    generate_cla_data(excel_steps="minimal")

    def test_custom_mapping_is_sixth_positional(self):
        """custom_mapping es el 6to parámetro POSITIONAL_OR_KEYWORD."""
        params = inspect.signature(generate_cla_data).parameters
        keys = list(params.keys())
        assert keys[5] == "custom_mapping"
        assert keys[6] == "excel_steps"
        assert params["custom_mapping"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

    def test_dict_by_position_does_not_hit_excel_steps(self):
        """Un dict pasado como 6to argumento cae en custom_mapping, no en excel_steps."""
        mapping = {9810: 17}
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with patch(_PATCH_TARGET, side_effect=_StopPipeline):
                with pytest.raises(_StopPipeline):
                    generate_cla_data(None, None, None, False, "x.xlsx", mapping)
