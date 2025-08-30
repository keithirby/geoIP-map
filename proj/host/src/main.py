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
        
    # 4. Start the loop and wait for packets
    while not INTERRUPTED: 
        start_sniffer(session_countries, session_blocks)
    
    # 5. close the program
    session_countries.close()
    session_blocks.close()
    print("sessions closed, exiting")
    sys.exit(0)

if __name__ == "__main__":
    main()
