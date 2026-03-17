from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet
from utiles.logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    update_parquet_by_year()
    update_bcch_parquet()
