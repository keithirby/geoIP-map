# Standard libraries we need 
import re
import random

# Package libraries we need 
from scapy.all import Ether, IP, TCP, sendp


# Local libraries we need
from config import RECEIVER_IP, SUBNET, DEST_PORT, SCAPY_DELAY, RECEIVER_MAC

# use ctrl + z to kill this 
# Add a SIGINT here later 
def send_packet(src_ip_with_cidr, country):
    # 1. Extract IP and CIDR using regex
    match = re.match(r"(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})", src_ip_with_cidr)
    if not match:
        print(f"Invalid IP/CIDR address: {src_ip_with_cidr}, not sending")
        return 

    # 2. Seperate the IP and CIDR to their own strings
    src_ip, cidr_mask = match.groups()
    # 3. Add the CIDR mask as the payload 
    payload = f"{src_ip}/{cidr_mask}".encode() 
    # 4. Build packet with CIDR mask payload
    pkt = Ether(dst=RECEIVER_MAC) / IP(src=src_ip, dst=RECEIVER_IP) / TCP(
        sport=random.randint(1024, 65535),
        dport=DEST_PORT,
        flags="S"
    ) / payload
    # Send the packet to the host
    try:
        sendp(pkt, verbose=0) 
        # debug print
        #print(f"Sent packet from {src_ip_with_cidr} ({country}) with payload: {payload}")
        # normal print
        print(f"Sent packet from {payload} and country ({country})")
    except Exception as e:
        print(f"Failed to send packet: {e}")
    