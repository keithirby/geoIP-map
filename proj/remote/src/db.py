"""! 
@file db.py
@brief load our cvs files as sqllite engines / databases 
and provide factories to start sessions for our sqllite engines
"""
# Per the user agreement I signed I cannot upload the databases I used to the internet
from config import COUNTRY_CVS, BLOCKS_CVS, GEO_IP_DB_PATH 

# Other libraries needed
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Boolean, MetaData, Table 
from sqlalchemy.orm import sessionmaker
# -----------------------
# Database setup
# -----------------------

# One  global engines for our main databases  
GEOIP_ENGINE = create_engine(f"sqlite:///{GEO_IP_DB_PATH}", echo=False)


# One global session factories
""" Used with helper functions to create session query instances"""
SESS_GEOIP_FACTORY = sessionmaker(bind=GEOIP_ENGINE)

"""!
@brief Load a passed csv_file into a engine
"""
def load_csv_to_sqlite(csv_file, table_name, engine):
    """Load CSV into SQLite using pandas"""
    df = pd.read_csv(csv_file)
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into table '{table_name}'")
    
    

"""!
@brief Initialize our two databases with our two csv files
"""
def initalize_engines(): 
    # 2. Load CSVs into DBs
    print("Loading GEOIP_ENGINE with CSV data")
    load_csv_to_sqlite(COUNTRY_CVS, "countries", GEOIP_ENGINE)
    load_csv_to_sqlite(BLOCKS_CVS, "blocks", GEOIP_ENGINE)
    print("Initialization complete.")

"""!
@brief helper function to return a  GEOIP_ENGINE session to 
query the engine
"""
def get_geoip_session():
    """Returns a new session bound to the combined GEOIP_ENGINE database."""
    return SESS_GEOIP_FACTORY()