from dotenv import dotenv_values

config = dotenv_values(".env")

BCCH_USER = config["BCCH_USER"]
BCCH_PASS = config["BCCH_PASS"]
