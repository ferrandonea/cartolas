from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet

if __name__ == "__main__":
    update_parquet_by_year()
    update_bcch_parquet()
