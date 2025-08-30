"""! 
@file db.py
@brief load our cvs files as sqllite engines / databases 
and provide factories to start sessions for our sqllite engines
"""
# Per the user agreement I signed I cannot upload the databases I used to the internet
from config import COUNTRY_CVS, BLOCKS_CVS, DB_COUNTRY_PATH, DB_BLOCK_PATH

# Other libraries needed
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Boolean, MetaData, Table 
from sqlalchemy.orm import sessionmaker
# -----------------------
# Database setup
# -----------------------

# Two global engines for our main databases  
ENGINE_COUNTRIES = create_engine(f"sqlite:///{DB_COUNTRY_PATH}", echo=False)
ENGINE_BLOCKS  = create_engine(f"sqlite:///{DB_BLOCK_PATH}", echo=False)

# Two global session factories
""" Used with helper functions to create session query instances"""
SESS_COUNTRY_FACTORY = sessionmaker(bind=ENGINE_COUNTRIES)
SESS_BLOCK_FACTORY = sessionmaker(bind=ENGINE_BLOCKS)

"""!
@brief Load a passed csv_file into a engine
"""
def load_csv_to_sqlite(csv_file, table_name, engine):
    """Load CSV into SQLite using pandas"""
    df = pd.read_csv(csv_file)
    df.to_sql(table_name, engine, if_exists="replace", index=False)

"""!
@brief Initialize our two databases with our two csv files
"""
def initalize_engines(): 
    print("Loading engines with csv data")
    # 2. Load CSVs into DBs
    load_csv_to_sqlite(COUNTRY_CVS, "countries", ENGINE_COUNTRIES)
    load_csv_to_sqlite(BLOCKS_CVS, "blocks", ENGINE_BLOCKS)

"""!
@brief helper function to return a ENGINE_COUNTRIES session to 
query the engine
"""
def get_country_session():
    """Returns a new session bound to the countries database."""
    return SESS_COUNTRY_FACTORY()

"""!
@brief helper function to return a ENGINE_BLOCKS session to 
query the engine
"""
def get_block_session():
    """Returns a new session bound to the blocks database."""
    return SESS_BLOCK_FACTORY()