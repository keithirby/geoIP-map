#!/usr/bin/env bash
set -e

# Config
NET_NAME="scapy_net"
SUBNET="172.16.0.0/24"
RECEIVER_IP="172.16.0.200"
SENDER_NAME="host"
RECEIVER_NAME="remote"

# Step 1: Delete the network if one exists then make a new network 
docker network rm scapy_net 2>/dev/null || true
docker network create --subnet=$SUBNET $NET_NAME || true

# Step 2: Build base image with Scapy, SQLite3, ping, and ip tools
cat > Dockerfile.scapy <<'EOF'
FROM python:3.11

# Install required packages
RUN apt-get update \
    && apt-get install -y python3-scapy sqlite3 iputils-ping iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
EOF


docker build -t scapy_base -f Dockerfile.scapy .

# Step 3: Run receiver container (detached)
docker run -dit --rm \
    --net $NET_NAME --ip $RECEIVER_IP \
    --name $RECEIVER_NAME \
    scapy_base tail -f /dev/null

# Step 4: Run sender container (detached)
docker run -dit --rm \
    --net $NET_NAME \
    --name $SENDER_NAME \   
    scapy_base tail -f /dev/null



# Open receiver container in a new GNOME Terminal window
gnome-terminal --title="$RECEIVER_NAME" -- bash -c "docker exec -it $RECEIVER_NAME /bin/bash; exec bash" &
# Small delay to open the second terminal
sleep 1
# Open sender container in a new GNOME Terminal window
gnome-terminal --title="$SENDER_NAME" -- bash -c "docker exec -it $SENDER_NAME /bin/bash; exec bash" &


echo "Two containers should be running!"
echo "Left pane: receiver | Right pane: sender"
