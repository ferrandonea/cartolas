from cartolas.update import update_parquet
from eco.bcentral import update_bcch_parquet

if __name__ == "__main__":
    update_parquet()
    update_bcch_parquet()
