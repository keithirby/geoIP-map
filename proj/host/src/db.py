"""! 
@file db.py
@brief load our cvs files as sqllite engines / databases 
and provide factories to start sessions for our sqllite engines
"""
# Per the user agreement I signed I cannot upload the databases I used to the internet
from config import COUNTRY_CVS, BLOCKS_CVS, GEO_IP_DB_PATH

#Standards libraries needed 
import time
from threading import Lock

# Other libraries needed
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, MetaData, Table, text 
from sqlalchemy.orm import sessionmaker
# -----------------------
# Database setup
# -----------------------
# One  global engines for our main databases  
GEOIP_ENGINE = create_engine(f"sqlite:///{GEO_IP_DB_PATH}", echo=False)

# One global session for accessing geo IP data
""" Used with helper function to create session query instance"""
SESS_GEOIP_FACTORY = sessionmaker(bind=GEOIP_ENGINE)
# Another session for updating table frequency table
PACKET_SESSION_FACTORY = sessionmaker(bind=GEOIP_ENGINE)

# Common database statements (commands)
#-- Used by decrement_packet_frequencies()--#
# Search for all packet records and return the records with geoname_id and frequency
PACKET_SUB_SEARCH_FREQ_STMT = text(
    "SELECT geoname_id, frequency FROM packet"
)
# Subtract a packet table records frequency
PACKET_SUB_FREQU_STMT = text(
     "UPDATE packet SET frequency = :frequency WHERE geoname_id = :gid"
)
#-- Used by increment_packet_freq()--#
PACKET_ADD_SEARCH_FREQ_STMT = text(
    "SELECT frequency, request_time FROM packet WHERE geoname_id = :gid"
)
# Add a record to packet table
PACKET_ADD_STMT = text(
    "INSERT INTO packet (geoname_id, frequency, request_time) VALUES (:geoname_id, :frequency, :request_time)"
)
# Update a record from packet table
PACKET_UPDATE_STMT = text(
    "UPDATE packet SET frequency = :frequency, request_time = :request_time WHERE geoname_id = :gid"
)
#-- generic packet search query for packet table--# 
PACKET_SEARCH_ID_STMT = text(
    "SELECT geoname_id, frequency, request_time FROM packet WHERE geoname_id = :gid"
)

# Lock to be extra careful with threading
PACKET_LOCK = Lock()

"""!
@brief Load a passed csv_file into a engine
"""
def load_csv_to_sqlite(csv_file, table_name, engine):
    """Load CSV into SQLite using pandas"""
    df = pd.read_csv(csv_file)
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into table '{table_name}'")
    
"""!
@brief Load packet table to the database
"""
def load_packet_table_sqlite():
    """Load CSV into SQLite using pandas"""
    table_name = "packet"
    metadata = MetaData()

    # Define packet table schema 
    packet_table = Table(
        table_name, metadata,
        Column("geoname_id", Integer, primary_key=True),
        Column("frequency", Integer, default=0),
        Column("request_time", Float)
    )
    # Create the table in database
    metadata.create_all(GEOIP_ENGINE)
    print(f"Packet table '{table_name}' initialized.")


"""!
@brief Initialize our two databases with our two csv files
"""
def initalize_engines(): 
    # 2. Load CSVs into DBs
    print("Loading GEOIP_ENGINE with CSV data")
    load_csv_to_sqlite(COUNTRY_CVS, "countries", GEOIP_ENGINE)
    load_csv_to_sqlite(BLOCKS_CVS, "blocks", GEOIP_ENGINE)
    load_packet_table_sqlite()
    print("Initialization complete.")

"""!
@brief helper function to return a  GEOIP_ENGINE session to 
query the engine
"""
def get_geoip_session():
    """Returns a new session bound to the combined GEOIP_ENGINE database."""
    return SESS_GEOIP_FACTORY()


"""!
@brief Decrement all packet table record's frequency
"""
def decrement_packet_frequencies():
    # 1. Lock the packet table lock for thread safety
    with PACKET_LOCK:
        # 2. Start a session for the packet table
        session = PACKET_SESSION_FACTORY()
        # 3. Get a list all packet records in packet table
        packet_records = session.execute(PACKET_SUB_SEARCH_FREQ_STMT).fetchall()
        # 4. Go through the list of packet records and decrement by 1
        for geoname_id, freq in packet_records:
            try:
                # If the frequency isnt already one decrement the frequency by 1
                new_freq = max(freq - 1, 0)
                # Stage the change
                session.execute(
                    PACKET_SUB_FREQU_STMT,
                    {"frequency": new_freq, "gid": geoname_id},
                )
                # Push the changes to the table
                session.commit()

                #---DEBUG---#
                # Fetch and print the updated record 
                updated_row = session.execute(PACKET_SEARCH_ID_STMT, {"gid": geoname_id}).fetchone()
                if updated_row:
                    gid, freq_after, req_time_after = updated_row
                    if freq_after != new_freq:
                        print(f"   ✅ Updated row: geoname_id={gid}, freq={freq_after} vs old {new_freq}, request_time={req_time_after}")
                    else: 
                        print("Frequency wasnt updated when incrementing a packet")
                else: 
                    print("Cant find a packet record after incrementing?")

            except Exception as e:
                # If the changes werent accepted roll back what might have happened
                session.rollback()
                print("failed decrement a packet record frequency")
            finally:
                # Close the session
                session.close()

"""!
@brief Increment or create a record for a geonome_id  
"""
def increment_packet_freq(geoname_id):
    print("incrementing packet frequency")
    with PACKET_LOCK:
        session = PACKET_SESSION_FACTORY()
        try:
            # 1. Get the current time and see if a record for a current country already exists
            curr_time = time.time()
            result = session.execute(PACKET_ADD_SEARCH_FREQ_STMT, {"gid": geoname_id}).fetchone()

            freq = 1
            if result is None:
                # 2. If a record wasnt found, create one, stage the change
                session.execute(
                    PACKET_ADD_STMT,
                    {"geoname_id": geoname_id, "frequency": freq, "request_time": curr_time},
                )
            else:
                # 2. if a record was found, update it, stage the change 
                freq, _ = result
                session.execute(
                    PACKET_UPDATE_STMT,
                    {"frequency": freq + 1, "request_time": curr_time, "gid": geoname_id},
                )
            # Push the changes
            session.commit()
            print("commited incrementing packet frequency")
            #---DEBUG---#
            # Fetch and print the updated record 
            updated_row = session.execute(PACKET_SEARCH_ID_STMT, {"gid": geoname_id}).fetchone()
            if updated_row:
                gid, freq_after, req_time_after = updated_row
                if freq_after != freq:
                    print(f"   ✅ Updated row: geoname_id={gid}, freq={freq_after} vs old {freq}, request_time={req_time_after}")
                else: 
                    print("Frequency wasnt updated when incrementing a packet")
            else: 
                print("Cant find a packet record after incrementing?")

        except Exception as e:
            # If the changes werent accepted roll back what might have happened
            print("failed update or add a packet record")
            session.rollback()
        finally:
            # Close the session
            print("finished incrementing packet frequency")
            session.close()
