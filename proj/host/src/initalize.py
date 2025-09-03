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
from db import initalize_engines, get_geoip_session, increment_packet_freq, reset_packet_table
from scapy_receiver import start_sniffer
from config import DECREMENT_INTERVAL
from thread_control import (
    start_sniffer_thread,
    stop_sniffer_thread,
    start_reset_thread,
    stop_reset_thread
)

INTERRUPTED = False

# Function that ctrl + c will make the program enter 
def signal_handler(sig, frame):
    global INTERRUPTED
    print("\nSIGINT received. Shutting down...")
    INTERRUPTED = True

# Register the signal handler for ctrl + c 
signal.signal(signal.SIGINT, signal_handler)