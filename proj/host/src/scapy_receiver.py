"""!
@file main.py
@brief Listen for packets and print them to the console
"""

# Package libraries we need
from scapy.all import sniff, IP, TCP

# Package libraries we need 
from sqlalchemy import text



def match_country_to_address(payload, session_countries, session_blocks):
    if payload == None:
            print("Packet did not have a recognized payload")
            return 

    # 2. Use the payload (src ip + CIDR) to find a matching geoname_id
    block_stmt = text("SELECT network, geoname_id FROM blocks WHERE network = :net")
    result = session_blocks.execute(block_stmt, {"net": payload}).fetchone()
    if not result:
        raise ValueError(f"No matching block found for payload {payload}")
        return
    network, geoname_id = result
    # 3. Use the matched geoname_id to find the country name
    # Query the countries table for country_name
    country_stmt = text("SELECT country_name FROM countries WHERE geoname_id = :gid")
    country_result = session_countries.execute(country_stmt, {"gid": geoname_id}).fetchone()
    if not country_result:
        raise ValueError(f"No country found for geoname_id {geoname_id}")
        return
    country_name = country_result[0]
    print(f"Received packet from from ({country_name}) and `{payload}` ")
    


def handle_pkt(pkt, session_countries, session_blocks):
    # Check if the sent packet has a IP and TCP layer
    if IP in pkt and TCP in pkt:
        # If it does then make sure there is a payload attached
        if pkt.haslayer(TCP) and hasattr(pkt[TCP], "payload"):
            # extract the payload and print the sender IP address and payload
            try: 
                payload = bytes(pkt[TCP].payload).decode(errors="ignore")
            except UnicodeDecodeError:
                # Skip packets that don't decode
                return  
            # debug print
            #print(f"Received packet from SRC IP {pkt[IP].src} | payload {payload}")
            match_country_to_address(payload, session_countries, session_blocks)

def start_sniffer(session_countries, session_blocks):
    """
    Starts sniffing and passes session objects to handle_pkt().
    """
    sniff(
        filter="tcp",
        prn=lambda pkt: handle_pkt(pkt, session_countries, session_blocks)
    )


    