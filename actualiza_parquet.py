from cartolas.update import update_parquet
from eco.bcentral import update_bcch_parquet
from utiles.logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    update_parquet()
    update_bcch_parquet()
