"""Tests para utiles/fechas.py"""

from datetime import date, datetime

import pytest

from utiles.fechas import (
    consecutive_date_ranges,
    date_n_months_ago,
    date_n_years_ago,
    date_range,
    format_date_cmf,
    from_date_to_datetime,
    ultimo_dia_año_anterior,
    ultimo_dia_mes_anterior,
)


# --- from_date_to_datetime ---


class TestFromDateToDatetime:
    def test_datetime_returns_date(self):
        dt = datetime(2024, 3, 15, 10, 30)
        assert from_date_to_datetime(dt) == date(2024, 3, 15)

    def test_date_returns_same(self):
        d = date(2024, 3, 15)
        assert from_date_to_datetime(d) == d

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            from_date_to_datetime("2024-03-15")

        with pytest.raises(ValueError):
            from_date_to_datetime(12345)


# --- format_date_cmf ---


class TestFormatDateCmf:
    def test_basic_format(self):
        assert format_date_cmf(date(2024, 3, 15)) == "15/03/2024"

    def test_single_digit_day_month(self):
        assert format_date_cmf(date(2024, 1, 5)) == "05/01/2024"

    def test_from_datetime(self):
        dt = datetime(2024, 12, 25, 8, 0)
        assert format_date_cmf(dt) == "25/12/2024"

    def test_new_year(self):
        assert format_date_cmf(date(2025, 1, 1)) == "01/01/2025"


# --- date_range ---


class TestDateRange:
    def test_normal_range(self):
        result = date_range(date(2024, 1, 1), date(2024, 1, 5))
        assert len(result) == 5
        assert result[0] == date(2024, 1, 1)
        assert result[-1] == date(2024, 1, 5)

    def test_same_date(self):
        d = date(2024, 6, 15)
        assert date_range(d, d) == [d]

    def test_start_after_end_raises(self):
        with pytest.raises(ValueError):
            date_range(date(2024, 1, 10), date(2024, 1, 1))

    def test_consecutive_days(self):
        result = date_range(date(2024, 1, 1), date(2024, 1, 3))
        expected = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        assert result == expected


# --- consecutive_date_ranges ---


class TestConsecutiveDateRanges:
    def test_empty_list(self):
        assert consecutive_date_ranges([]) == []

    def test_single_date(self):
        result = consecutive_date_ranges([date(2024, 1, 1)])
        assert result == [(date(2024, 1, 1), date(2024, 1, 1))]

    def test_consecutive_dates(self):
        dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
        result = consecutive_date_ranges(dates, max_days=29)
        assert result == [(date(2024, 1, 1), date(2024, 1, 3))]

    def test_gap_splits_range(self):
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 5),
            date(2024, 1, 6),
        ]
        result = consecutive_date_ranges(dates, max_days=29)
        assert result == [
            (date(2024, 1, 1), date(2024, 1, 2)),
            (date(2024, 1, 5), date(2024, 1, 6)),
        ]

    def test_max_days_splits(self):
        dates = date_range(date(2024, 1, 1), date(2024, 2, 15))  # 46 días consecutivos
        result = consecutive_date_ranges(dates, max_days=29)
        assert len(result) == 2
        # Primer rango: máximo 30 días (0-29)
        assert (result[0][1] - result[0][0]).days == 29

    def test_unsorted_input(self):
        dates = [date(2024, 1, 3), date(2024, 1, 1), date(2024, 1, 2)]
        result = consecutive_date_ranges(dates, max_days=29)
        assert result == [(date(2024, 1, 1), date(2024, 1, 3))]


# --- date_n_months_ago ---


class TestDateNMonthsAgo:
    def test_basic(self):
        assert date_n_months_ago(1, date(2024, 3, 15)) == date(2024, 2, 15)

    def test_cross_year(self):
        assert date_n_months_ago(1, date(2024, 1, 15)) == date(2023, 12, 15)

    def test_end_of_month_clamp(self):
        # 31 marzo - 1 mes = 29 feb (2024 bisiesto)
        assert date_n_months_ago(1, date(2024, 3, 31)) == date(2024, 2, 29)

    def test_end_of_month_non_leap(self):
        # 31 marzo - 1 mes = 28 feb (2023 no bisiesto)
        assert date_n_months_ago(1, date(2023, 3, 31)) == date(2023, 2, 28)

    def test_zero_months(self):
        d = date(2024, 6, 15)
        assert date_n_months_ago(0, d) == d

    def test_twelve_months(self):
        assert date_n_months_ago(12, date(2024, 3, 15)) == date(2023, 3, 15)


# --- date_n_years_ago ---


class TestDateNYearsAgo:
    def test_basic(self):
        assert date_n_years_ago(1, date(2024, 3, 15)) == date(2023, 3, 15)

    def test_leap_year(self):
        # 29 feb 2024 - 1 año = 28 feb 2023
        assert date_n_years_ago(1, date(2024, 2, 29)) == date(2023, 2, 28)

    def test_five_years(self):
        assert date_n_years_ago(5, date(2024, 3, 15)) == date(2019, 3, 15)

    def test_zero_years(self):
        d = date(2024, 6, 15)
        assert date_n_years_ago(0, d) == d


# --- ultimo_dia_año_anterior ---


class TestUltimoDiaAñoAnterior:
    def test_basic(self):
        assert ultimo_dia_año_anterior(date(2024, 6, 15)) == date(2023, 12, 31)

    def test_january_first(self):
        assert ultimo_dia_año_anterior(date(2024, 1, 1)) == date(2023, 12, 31)

    def test_december_31(self):
        assert ultimo_dia_año_anterior(date(2024, 12, 31)) == date(2023, 12, 31)


# --- ultimo_dia_mes_anterior ---


class TestUltimoDiaMesAnterior:
    def test_basic(self):
        assert ultimo_dia_mes_anterior(date(2024, 3, 15)) == date(2024, 2, 29)  # bisiesto

    def test_january(self):
        assert ultimo_dia_mes_anterior(date(2024, 1, 15)) == date(2023, 12, 31)

    def test_march_leap(self):
        assert ultimo_dia_mes_anterior(date(2024, 3, 1)) == date(2024, 2, 29)

    def test_march_non_leap(self):
        assert ultimo_dia_mes_anterior(date(2023, 3, 1)) == date(2023, 2, 28)
