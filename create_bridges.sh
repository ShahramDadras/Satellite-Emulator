#!/bin/bash

# Function to create a bridge
create_bridge() {
    BRIDGE_NAME="$1"
    ip link add name "$BRIDGE_NAME" type bridge
    ip link set dev "$BRIDGE_NAME" up
}

# Create 10 virtual bridges named 'br1' to 'br5'
for i in $(seq 1 5); do
    create_bridge "br$i"
done

# Keep the script running (you can replace this with another process if needed)
tail -f /dev/null



