"""!
@file main.py
@brief initalize our databases, start the listener event loop 
"""

# Standard libraries we need
import signal # for stop signal
import sys # for exit()

# Package libraries we need 
from sqlalchemy import text

# Local libraries we need
from db import initalize_engines, get_country_session, get_block_session
from scapy_receiver import start_sniffer


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
        
    # 3. Start the loop and wait for packets
    while not INTERRUPTED: 
        start_sniffer(geoip_session)
    
    # 4. close the program
    session_countries.close()
    session_blocks.close()
    print("sessions closed, exiting")
    sys.exit(0)

if __name__ == "__main__":
    main()
