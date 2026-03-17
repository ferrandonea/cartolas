import click
import logging
from utiles.logging_config import setup_logging

logger = logging.getLogger(__name__)


@click.group()
def main():
    """Cartolas — Análisis de fondos mutuos chilenos."""
    setup_logging()


@main.command()
@click.option("--all", "monolithic", is_flag=True, help="Actualizar parquet monolítico en vez de por año.")
def update(monolithic):
    """Descarga cartolas CMF y actualiza datos BCCh."""
    from eco.bcentral import update_bcch_parquet

    if monolithic:
        from cartolas.update import update_parquet

        update_parquet()
    else:
        from cartolas.update_by_year import update_parquet_by_year

        update_parquet_by_year()

    update_bcch_parquet()


@main.group()
def report():
    """Genera reportes de análisis."""


@report.command()
@click.option("--output", type=click.Path(), default=None, help="Ruta del archivo Excel.")
@click.option("--no-update", is_flag=True, help="Saltar actualización de datos antes de generar.")
def cla(output, no_update):
    """Genera reporte CLA mensual (Excel).

    Por defecto actualiza datos (by-year + BCCh) antes de generar.
    """
    from datetime import date
    from pathlib import Path

    from utiles.fechas import ultimo_dia_mes_anterior

    if not no_update:
        from cartolas.update_by_year import update_parquet_by_year
        from eco.bcentral import update_bcch_parquet

        logger.info("Actualizando parquet por año")
        update_parquet_by_year()
        logger.info("Actualizando BCCh parquet")
        update_bcch_parquet()

    from comparador.cla_monthly import generate_cla_data

    report_date = ultimo_dia_mes_anterior(date.today())
    if output is None:
        output = Path("cla_mensual") / f"cla_{report_date.strftime('%Y%m%d')}.xlsx"
    else:
        output = Path(output)

    logger.info(f"Reporte CLA: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_cla_data(save_xlsx=True, xlsx_name=output)


@report.command()
def soyfocus():
    """Genera parquets SoyFocus (detalle, por RUN y TAC)."""
    from cartolas.soyfocus import (
        create_soyfocus_parquet,
        create_tac_report,
        soy_focus_by_run,
    )

    lazy_df = create_soyfocus_parquet()
    create_tac_report(lazy_df)
    lazy_df_by_run = soy_focus_by_run(lazy_df)
    create_tac_report(lazy_df_by_run, run_only=True)


@report.command()
@click.option("--output", type=click.Path(), default="apv.csv", help="Ruta del CSV de salida.")
def apv(output):
    """Exporta datos APV de fondos SoyFocus a CSV."""
    import polars as pl

    from cartolas.config import PARQUET_FOLDER_YEAR
    from cartolas.read import read_parquet_cartolas_lazy
    from eco.bcentral import PARQUET_PATH as BCCH_PARQUET
    from utiles.fechas import date_n_years_ago

    df = (
        read_parquet_cartolas_lazy(parquet_path=PARQUET_FOLDER_YEAR)
        .filter(pl.col("RUN_FM").is_in([9809, 9810, 9811]))
        .select("RUN_FM", "FECHA_INF", "SERIE", "VALOR_CUOTA")
        .collect()
    )
    df_apv = df.filter(pl.col("SERIE").is_in(["APV", "APV-FREE"])).sort("FECHA_INF")
    max_date = df_apv.select(pl.col("FECHA_INF").max()).item()
    df_apv.filter(pl.col("FECHA_INF") > date_n_years_ago(1, max_date)).write_csv(output)
    logger.info(f"APV exportado: {output}")

    uf_output = "uf.csv"
    df_bcch = pl.read_parquet(BCCH_PARQUET)
    df_bcch.select(pl.col(["FECHA_INF", "UF"])).filter(
        pl.col("FECHA_INF") > date_n_years_ago(1, max_date)
    ).write_csv(uf_output)
    logger.info(f"UF exportado: {uf_output}")
