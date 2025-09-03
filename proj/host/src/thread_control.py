import threading
import time
from db import get_geoip_session, increment_packet_freq, reset_packet_table, PACKET_DELETE_ALL_STMT
from scapy_receiver import start_sniffer
from config import DECREMENT_INTERVAL

SNIFFER_THREAD = None
SNIFFER_STOP_EVENT = threading.Event()
RESET_THREAD = None
RESET_STOP_EVENT = threading.Event()

reset_config = {"timer": 30, "enabled": False}  # Default: 30s, disabled

def reset_packet_table_thread():
    print(f"[AutoReset] Thread started (interval = {reset_config['timer']}s)")
    while not RESET_STOP_EVENT.is_set():
        if reset_config["enabled"]:
            reset_packet_table()
            print(f"[AutoReset] Packet table reset. Next reset in {reset_config['timer']}s")
        for _ in range(int(reset_config["timer"] * 10)):
            if RESET_STOP_EVENT.is_set() or not reset_config["enabled"]:
                break
            time.sleep(0.1)
    print("[AutoReset] Thread exiting")

def start_reset_thread():
    global RESET_THREAD
    if RESET_THREAD and RESET_THREAD.is_alive():
        return
    RESET_STOP_EVENT.clear()
    RESET_THREAD = threading.Thread(target=reset_packet_table_thread, daemon=True)
    RESET_THREAD.start()

def stop_reset_thread():
    RESET_STOP_EVENT.set()
    if RESET_THREAD:
        RESET_THREAD.join(timeout=2)


def sniffer_loop():
    geoip_session = get_geoip_session()
    print("[Sniffer] Session created")
    try:
        while not SNIFFER_STOP_EVENT.is_set():
            # Use a timeout or non-blocking packet sniff call
            start_sniffer(geoip_session, increment_packet_freq, SNIFFER_STOP_EVENT)
    finally:
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
    global SNIFFER_THREAD
    if SNIFFER_THREAD and SNIFFER_THREAD.is_alive():
        print("[Sniffer] Stopping...")
        SNIFFER_STOP_EVENT.set()
        SNIFFER_THREAD.join(timeout=2)  # Will only finish if thread checks event
        if SNIFFER_THREAD.is_alive():
            print("[Sniffer] Thread did not exit! It is likely blocked in start_sniffer()")
        else:
            print("[Sniffer] Stopped")

def main(): 
        # 2. Create sessions to access the geoIP database database
    geoip_session = get_geoip_session()
    print("Sessions created")


    # 5. Start the loop and wait for packets
    print("Starting packet sniffer thread")
        # Start sniffer by default (can be toggled off in GUI)
    start_sniffer_thread()

    start_reset_thread() 

    try:
        while not INTERRUPTED:
            time.sleep(0.2)
    finally:
        stop_sniffer_thread()
        stop_reset_thread()
        decrement_thread.join()
        geoip_session.close()
        print("Clean exit")
    print("session closed, exiting")
