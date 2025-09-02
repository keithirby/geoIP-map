"""!
@file main.py
@brief initalize our databases, start the listener event loop 
"""

# Standard libraries we need
import signal # for stop signal
import sys # for exit()
import threading
import time 

# Package libraries we need 
from sqlalchemy import text

# Local libraries we need
from db import initalize_engines, get_geoip_session, increment_packet_freq, decrement_packet_frequencies
from scapy_receiver import start_sniffer
from config import DECREMENT_INTERVAL

INTERRUPTED = False
SNIFFER_THREAD = None
SNIFFER_STOP_EVENT = threading.Event()

# Function that ctrl + c will make the program enter 
def signal_handler(sig, frame):
    global INTERRUPTED
    print("\nSIGINT received. Shutting down...")
    INTERRUPTED = True

# Register the signal handler for ctrl + c 
signal.signal(signal.SIGINT, signal_handler)

# Function to decrement all packets sent frequency by 1 every interval_sec
def periodic_decrement(interval_sec=5):
    while not INTERRUPTED:
        decrement_packet_frequencies()
        time.sleep(interval_sec)

def sniffer_loop():
    """Loop that runs the sniffer until stop event is set."""
    geoip_session = get_geoip_session()
    print("[Sniffer] Session created")
    while not SNIFFER_STOP_EVENT.is_set():
        start_sniffer(geoip_session, increment_packet_freq)
    geoip_session.close()
    print("[Sniffer] Session closed")


def start_sniffer_thread():
    """Start sniffer in a background thread."""
    global SNIFFER_THREAD
    if SNIFFER_THREAD and SNIFFER_THREAD.is_alive():
        print("[Sniffer] Already running")
        return
    SNIFFER_STOP_EVENT.clear()
    SNIFFER_THREAD = threading.Thread(target=sniffer_loop, daemon=True)
    SNIFFER_THREAD.start()
    print("[Sniffer] Started background thread")


def stop_sniffer_thread():
    """Stop the running sniffer thread."""
    if not SNIFFER_THREAD:
        return
    print("[Sniffer] Stopping...")
    SNIFFER_STOP_EVENT.set()
    SNIFFER_THREAD.join(timeout=2)
    print("[Sniffer] Stopped")

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

    # 4. start the background thread to update the packet table
    decrement_thread = threading.Thread(target=periodic_decrement, daemon=True)
    decrement_thread.start()
    print(f"Started background decrement thread (every {DECREMENT_INTERVAL}s)")

    # 5. Start the loop and wait for packets
    print("Starting packet sniffer thread")
        # Start sniffer by default (can be toggled off in GUI)
    start_sniffer_thread()

    try:
        while not INTERRUPTED:
            time.sleep(0.2)
    finally:
        stop_sniffer_thread()
        decrement_thread.join()
        print("Clean exit")

    
    # FINAL STEP: close the session and thread
    decrement_thread.join()
    geoip_session.close()
    geoip_session.close()
    print("session closed, exiting")

if __name__ == "__main__":
    main()
