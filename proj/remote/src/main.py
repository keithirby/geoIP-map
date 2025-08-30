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
from db import initalize_engines, get_country_session, get_block_session
from config import countries_list
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
    # 1. load the csv files into our two engines 
    # We dont need to start the engines because they initialize on boot 
    # in db.py 
    initalize_engines()

    # 2. Create sessions to access the database
    session_countries = get_country_session()
    session_blocks = get_block_session()
    print("Sessions created")

    # 3. Wait on the user to start the event loop
    print("Databases initialized. Type 'yes' to continue...")
    user_ready = False
    while not user_ready:
        user_input = input().strip().lower()
        if user_input == "yes":
            user_ready = True 
        
    # 4. Start the loop and print countries and their major IP block address 
    # pulled from the database
    while not INTERRUPTED:
        # OPTION 1: totally random country + IP ADDR
        # Get country_name : geoname_id pairs
        stmt = text("SELECT country_name, geoname_id FROM countries")
        country_rows = session_countries.execute(stmt).fetchall()
        # Picks random country from the database
        rnd_country_list = [(row[0], row[1]) for row in country_rows]
        country_name, geoname_id = random.choice(rnd_country_list)
        #-------------------------------------------------------
        # OPTION 2: Random ish country from pre-defined list
        #country_name, geoname_id = random.choice(countries_list)
        # Helper prints for debugging
        # geoname_id print for debugging
        #print(f"Random country: {country_name} (geoname_id={geoname_id})")
        # normal print for not debugging
        #print(f"Random country: {country_name}")

        # Query blocks table using text()
        block_stmt = text("SELECT network FROM blocks WHERE geoname_id = :gid")
        block_rows = session_blocks.execute(block_stmt, {"gid": geoname_id}).fetchall()

        if not block_rows:
            print("No matching block entries found.")
        else:
            # Pick a random block entry
            random_network = random.choice(block_rows)[0]
            #print(f"Sending network for {country_name} : {random_network}")
            #Send the packet over the network
            send_packet(random_network, country_name)
        # Sleep for one second before querying another countries ip block
        time.sleep(1)

    # FINAL STEP: close the sessions 
    session_countries.close()
    session_blocks.close()
    print("sessions closed, exiting")
    sys.exit(0)

if __name__ == "__main__":
    main()
