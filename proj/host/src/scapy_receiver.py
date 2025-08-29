"""!
@file main.py
@brief Listen for packets and print them to the console
"""

from scapy.all import sniff, IP, TCP

def handle_pkt(pkt):
    # Check if the sent packet has a IP and TCP layer
    if IP in pkt and TCP in pkt:
        # If it does then make sure there is a payload attached
        if pkt.haslayer(TCP) and hasattr(pkt[TCP], "payload"):
            # extract the payload and print the sender IP address and payload
            payload = bytes(pkt[TCP].payload).decode()
            print(f"Received packet from {pkt[IP].src} with payload: {payload}")

sniff(filter="tcp", prn=handle_pkt)
