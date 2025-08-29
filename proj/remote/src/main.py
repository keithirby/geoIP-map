"""@package main.py

@brief load our cvs files as sqllite databases and start the 
scapy network sender in a anothe rfile

"""

# Per the user agreement I signed I cannot upload the databases I used to the internet
from config import COUNTRY_CVS, BLOCKS_CVS, DB_COUNTRY_PATH, DB_BLOCK_PATH

import pandas as pd
import random
import sys
from sqlalchemy import create_engine, Column, Integer, String, Boolean, MetaData, Table, text
from sqlalchemy.orm import sessionmaker

# -----------------------
# Database setup
# -----------------------
def load_csv_to_sqlite(csv_file, table_name, engine):
    """Load CSV into SQLite using pandas"""
    df = pd.read_csv(csv_file)
    df.to_sql(table_name, engine, if_exists="replace", index=False)


def main():
    # Create SQLite engines
    print("trying to create engines")
    engine_countries = create_engine(f"sqlite:///{DB_COUNTRY_PATH}", echo=False)
    engine_blocks = create_engine(f"sqlite:///{DB_BLOCK_PATH}", echo=False)
    print("created engines")
    print(f"engine 1 {engine_countries.url}")
    print(f"db path {COUNTRY_CVS}")
    # Load CSVs into DBs
    load_csv_to_sqlite(COUNTRY_CVS, "countries", engine_countries)
    load_csv_to_sqlite(BLOCKS_CVS, "blocks", engine_blocks)

    print("Databases initialized. Type 'yes' to continue...")
    user_input = input().strip().lower()

    if user_input != "yes":
        print("Exiting...")
        sys.exit(0)

    # Create sessions
    SessionCountries = sessionmaker(bind=engine_countries)
    session_countries = SessionCountries()

    SessionBlocks = sessionmaker(bind=engine_blocks)
    session_blocks = SessionBlocks()

    # Get country_name : geoname_id pairs
    stmt = text("SELECT country_name, geoname_id FROM countries")
    country_rows = session_countries.execute(stmt).fetchall()
    country_list = [(row[0], row[1]) for row in country_rows]

    # Pick a random (country, geoname_id)
    country_name, geoname_id = random.choice(country_list)
    print(f"Random country: {country_name} (geoname_id={geoname_id})")

    # Query blocks table using text()
    block_stmt = text("SELECT network FROM blocks WHERE geoname_id = :gid")
    block_rows = session_blocks.execute(block_stmt, {"gid": geoname_id}).fetchall()

    if not block_rows:
        print("No matching block entries found.")
    else:
        # Pick a random block entry
        random_network = random.choice(block_rows)[0]
        print(f"Random network for {country_name}: {random_network}")


if __name__ == "__main__":
    main()
