"""!
@file main.py
@brief initalize our databases, start the event loop, and 
start the scapy network sender 
"""

# Standard libraries we need
import random
import sys
import signal # for stop signal
import time # for sleep

# Package libraries we need 
from sqlalchemy import text

# Local libraries we need
from db import initalize_engines, get_geoip_session
from config import countries_list_selected
from scapy_send import send_packet



# Function that ctrl + c will make the program enter 
INTERRUPTED = False
def signal_handler(sig, frame):
    global INTERRUPTED
    print("\nSIGINT received. Shutting down...")
    INTERRUPTED = True

# Register the signal handler for ctrl + c 
signal.signal(signal.SIGINT, signal_handler)


# -----------------------
#  setup and start
# -----------------------
def main():
    # 1. Wait on the user to start the event loop and let them choose  
    # to load the load and cvs files into it if we havent already 
    print("Initialized. Hit enter to start... \n Type `yes` to initalize databases")
    user_ready = False
    user_input = input().strip().lower()
    if user_input == "yes":
        user_ready = True
        initalize_engines()
    

    # 2. Create sessions to access the geoIP database database
    geoip_session = get_geoip_session()
    print("Sessions created")

    # Make a list of all possible countries from countries table    
    stmt = text("SELECT country_name, geoname_id FROM countries")
    country_records = geoip_session.execute(stmt).fetchall()
    country_list = [(row[0], row[1]) for row in country_records]
        
    # 3. Start the loop and print countries and their major IP block address 
    # pulled from the database
    while not INTERRUPTED:
        # OPTION 1: totally random country + IP address
        # Get country_name : geoname_id pairs
        country_name, geoname_id = random.choice(country_list)
        #-------------------------------------------------------
        # OPTION 2: Random ish country from pre-defined list in config.py
        #country_name, geoname_id = random.choice(countries_list_selected)
        #--------------------------------------------------------
        # geoname_id print for debugging
        #print(f"Random country: {country_name} (geoname_id={geoname_id})")

        # Query blocks table for all Major IP blocks for a country
        block_stmt = text("SELECT network FROM blocks WHERE geoname_id = :gid")
        block_rows = geoip_session.execute(block_stmt, {"gid": geoname_id}).fetchall()

        if not block_rows:
            print("No matching block entries found.")
        else:
            # Pick a random Major IP Block for a country
            random_network = random.choice(block_rows)[0]
            #print(f"Sending network for {country_name} : {random_network}")
            #Send the packet over the network
            send_packet(random_network, country_name)
        # Sleep for one second before querying another countries ip block
        time.sleep(1)

    # FINAL STEP: close the session
    geoip_session.close()
    print("session closed, exiting")
    sys.exit(0)

if __name__ == "__main__":
    main()
