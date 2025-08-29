#!/usr/bin/env bash
set -e

# ========================
# Config
# ========================
PROJ_DIR="proj"
NET_NAME="scapy_net"
SUBNET="172.16.0.0/24"
RECEIVER_IP="172.16.0.200"
SENDER_NAME="host"
RECEIVER_NAME="remote"
IMAGE_NAME="scapy_base"

# ========================
# Setup project directories
# ========================
mkdir -p "$PROJ_DIR/$SENDER_NAME"
mkdir -p "$PROJ_DIR/$RECEIVER_NAME"

# ========================
# Functions
# ========================

build_image() {
    echo "[*] Building Docker image: $IMAGE_NAME"

    # Create a base Dockerfile in proj/
cat > "$PROJ_DIR/Dockerfile.scapy" <<'EOF'
FROM python:3.11

# Install pip and required system packages
# The Python base image usually includes pip, but it's good practice to ensure it's up-to-date.
RUN apt-get update && apt-get install -y \
    python3-pip \
    sqlite3 \
    iputils-ping \
    iproute2 \
    libpcap0.8-dev \ 
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Install specific Python packages
RUN pip install \
    scapy \
    pandas \
    sqlalchemy

WORKDIR /app
EOF

    docker build -t $IMAGE_NAME -f "$PROJ_DIR/Dockerfile.scapy" "$PROJ_DIR"
}

start_containers() {
    echo "[*] Starting containers..."

    # Remove network if exists, then recreate
    docker network rm $NET_NAME 2>/dev/null || true
    docker network create --subnet=$SUBNET $NET_NAME || true

    # Run receiver container
    docker run -dit --rm \
        --net $NET_NAME --ip $RECEIVER_IP \
        --name $RECEIVER_NAME \
        -v "$(pwd)/$PROJ_DIR/$RECEIVER_NAME:/app" \
        $IMAGE_NAME tail -f /dev/null

    # Run sender container
    docker run -dit --rm \
        --net $NET_NAME \
        --name $SENDER_NAME \
        -v "$(pwd)/$PROJ_DIR/$SENDER_NAME:/app" \
        $IMAGE_NAME tail -f /dev/null

    # Command for changing the hostnames of the terminals
    SET_PROMPT_CMD='HOSTNAME=$(hostname); export PS1="\\[\\033[01;32m\\]\u@$HOSTNAME:\\[\\033[00m\\]\\w\\$ "'
    # Open GNOME terminal for both
    gnome-terminal --title="$RECEIVER_NAME" -- bash -c "docker exec -it $RECEIVER_NAME /bin/bash -c '$SET_PROMPT_CMD; /bin/bash'" &
    sleep 1
    # Open GNOME terminal for sender with a new prompt
    gnome-terminal --title="$SENDER_NAME" -- bash -c "docker exec -it $SENDER_NAME /bin/bash -c '$SET_PROMPT_CMD; /bin/bash'" &


    echo "Two containers should be running"
    echo "   Left: $RECEIVER_NAME (receiver) | Right: $SENDER_NAME (sender)"
    echo "   Project directories: $PROJ_DIR/$RECEIVER_NAME , $PROJ_DIR/$SENDER_NAME"
}

clean_all() {
    echo "[*] Cleaning up containers, network, and image..."

    docker stop $SENDER_NAME $RECEIVER_NAME 2>/dev/null || true
    docker network rm $NET_NAME 2>/dev/null || true
    docker rmi $IMAGE_NAME 2>/dev/null || true

    echo "Cleanup complete!"
}

# ========================
# Main
# ========================
case "$1" in
    build)
        build_image
        ;;
    start)
        start_containers
        ;;
    clean)
        clean_all
        ;;
    *)
        echo "Usage: $0 {build|start|clean}"
        exit 1
        ;;
esac
